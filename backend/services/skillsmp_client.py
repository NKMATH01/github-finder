"""SkillsMP API 통신 모듈 — 스킬 검색 + 상세 조회 + SKILL.md 원문 조회.

캐시: 검색 1시간, 스킬 상세/SKILL.md 24시간.
재시도: 401/429 시 tenacity 지수 백오프 (3회, 2초→4초→8초).
"""

import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from config import settings
from models.error_models import AppException, ErrorCodes
from models.skill_models import SkillResult, SkillDetail
from services.github_cache import (
    cache_get,
    cache_set,
    TTL_SEARCH,
    TTL_REPO_DETAIL,
)

logger = logging.getLogger(__name__)

SKILLSMP_BASE = "https://skillsmp.com/api/v1"


class SkillsmpRateLimitError(Exception):
    """SkillsMP 429 재시도용 예외."""
    pass


class SkillsmpAuthError(Exception):
    """SkillsMP 401 인증 실패."""
    pass


_retry_policy = retry(
    retry=retry_if_exception_type(SkillsmpRateLimitError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=8),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


def _headers() -> dict[str, str]:
    h = {"Accept": "application/json"}
    api_key = getattr(settings, "SKILLSMP_API_KEY", "")
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    return h


@_retry_policy
async def _skillsmp_get(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict | None = None,
    cache_ttl: int | None = None,
) -> dict | list:
    """SkillsMP API GET — 캐시 확인 → 요청 → 캐시 저장."""
    if cache_ttl is not None:
        cached = await cache_get(url, params)
        if cached is not None:
            return cached

    resp = await client.get(url, params=params, headers=_headers())

    if resp.status_code == 401:
        raise SkillsmpAuthError("SKILLSMP_API_KEY가 유효하지 않습니다.")
    if resp.status_code == 429:
        raise SkillsmpRateLimitError("SkillsMP 일일 API 한도를 초과했습니다.")
    if resp.status_code != 200:
        logger.warning("SkillsMP API error: status=%d, url=%s", resp.status_code, url)
        return []

    data = resp.json()

    if cache_ttl is not None:
        await cache_set(url, params, data, ttl_seconds=cache_ttl)

    return data


async def search_skills(
    query: str,
    method: str = "keyword",
) -> list[SkillResult]:
    """SkillsMP에서 스킬을 검색합니다.

    method="keyword" → /skills/search
    method="ai" → /skills/ai-search
    """
    endpoint = "skills/ai-search" if method == "ai" else "skills/search"
    url = f"{SKILLSMP_BASE}/{endpoint}"
    params = {"q": query}

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            data = await _skillsmp_get(client, url, params=params, cache_ttl=TTL_SEARCH)
        except SkillsmpAuthError:
            raise AppException(
                code=ErrorCodes.VALIDATION_ERROR,
                message="SKILLSMP_API_KEY가 설정되지 않았거나 만료되었습니다.",
                status_code=401,
            )
        except SkillsmpRateLimitError:
            raise AppException(
                code="SKILLSMP_RATE_LIMIT",
                message="SkillsMP 일일 API 한도(500회)를 초과했습니다.",
                status_code=429,
                retry_after=3600,
            )

    results = []
    skill_items: list[dict] = []

    if isinstance(data, dict):
        inner = data.get("data", data)
        if isinstance(inner, dict):
            if method == "ai":
                # AI search: data.data.data[].skill
                raw_results = inner.get("data", [])
                if isinstance(raw_results, list):
                    for r in raw_results:
                        if isinstance(r, dict) and "skill" in r:
                            skill_items.append(r["skill"])
            else:
                # Keyword search: data.data.skills[]
                skills_list = inner.get("skills", inner.get("results", inner.get("data", [])))
                if isinstance(skills_list, list):
                    skill_items = skills_list
        elif isinstance(inner, list):
            skill_items = inner
    elif isinstance(data, list):
        skill_items = data

    for item in skill_items:
        if not isinstance(item, dict):
            continue
        results.append(SkillResult(
            skill_id=str(item.get("id", item.get("skill_id", ""))),
            name=item.get("name", item.get("title", "")),
            description=item.get("description", item.get("summary", "")),
            github_url=item.get("githubUrl", item.get("github_url", item.get("repo_url", ""))),
            skill_path=item.get("skill_path", item.get("path", "")),
            category=item.get("category", item.get("type", "")),
            stars=int(item.get("stars", item.get("star_count", 0))),
            last_updated=item.get("updatedAt", item.get("last_updated", item.get("updated_at"))),
            author=item.get("author", item.get("owner", "")),
        ))

    logger.info("SkillsMP %s 검색 완료: query=%s → %d개 스킬", method, query, len(results))
    return results


async def fetch_skill_detail(skill: SkillResult) -> SkillDetail:
    """스킬 상세 정보 + SKILL.md 원문을 조회합니다."""
    detail = SkillDetail(**skill.model_dump())

    # SKILL.md 원문 조회
    if skill.github_url:
        md_content = await fetch_skill_md(skill.github_url, skill.skill_path)
        detail.skill_md_content = md_content

    return detail


async def fetch_skill_md(github_url: str, skill_path: str) -> str:
    """GitHub raw URL에서 SKILL.md 원문을 가져옵니다.

    githubUrl 형태 대응:
    - https://github.com/owner/repo/tree/main/.claude/skills/xxx → branch=main, path=.claude/skills/xxx
    - https://github.com/owner/repo → skill_path 파라미터 사용
    """
    raw_url = ""
    if "github.com" in github_url:
        parts = github_url.rstrip("/").replace("https://github.com/", "").split("/")
        if len(parts) >= 4 and parts[2] == "tree":
            # tree URL: owner/repo/tree/branch/path/to/skill
            owner, repo, _, branch = parts[0], parts[1], parts[2], parts[3]
            dir_path = "/".join(parts[4:]) if len(parts) > 4 else ""
            suffix = f"{dir_path}/SKILL.md" if dir_path else "SKILL.md"
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{suffix}"
        elif len(parts) >= 2:
            owner, repo = parts[0], parts[1]
            path_prefix = f"{skill_path}/" if skill_path else ""
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{path_prefix}SKILL.md"

    if not raw_url:
        return ""

    cached = await cache_get(raw_url, None)
    if cached is not None:
        return cached.get("_raw_text", "") if isinstance(cached, dict) else ""

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(raw_url)
            if resp.status_code == 200:
                content = resp.text
                if len(content) > 10000:
                    content = content[:9000] + "\n...(이하 생략)..."
                await cache_set(raw_url, None, {"_raw_text": content}, ttl_seconds=TTL_REPO_DETAIL)
                return content
            # main 브랜치 실패 → master 시도
            alt_url = raw_url.replace("/main/", "/master/")
            resp = await client.get(alt_url)
            if resp.status_code == 200:
                content = resp.text
                if len(content) > 10000:
                    content = content[:9000] + "\n...(이하 생략)..."
                await cache_set(raw_url, None, {"_raw_text": content}, ttl_seconds=TTL_REPO_DETAIL)
                return content
        except Exception as e:
            logger.debug("SKILL.md 조회 실패: %s — %s", raw_url, e)

    return ""
