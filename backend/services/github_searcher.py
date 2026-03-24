"""GitHub API 1차 필터링 — Search + Contents + Issues API 연동.

Rate limit 대응:
- Supabase 캐시 (검색: 1시간 TTL, 레포 상세: 24시간 TTL)
- tenacity 지수 백오프 (403/429 시 최대 3회 재시도, 2초→4초→8초)
- X-RateLimit-Remaining 헤더 모니터링 (10 미만이면 자발적 대기)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

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
from services.github_cache import (
    cache_get,
    cache_set,
    TTL_SEARCH,
    TTL_REPO_DETAIL,
)

logger = logging.getLogger(__name__)


@dataclass
class RepoBasicInfo:
    """1차 필터링된 레포 기본 정보."""

    owner: str
    name: str
    full_name: str
    url: str
    description: str
    stars: int
    forks: int
    language: str
    updated_at: str
    open_issues: int
    has_wiki: bool
    license_name: str | None
    size_kb: int
    topics: list[str] = field(default_factory=list)


@dataclass
class RepoDetailedInfo(RepoBasicInfo):
    """딥 리딩용 상세 정보 (README, 파일 트리, 의존성, 이슈)."""

    readme_content: str = ""
    file_tree: list[str] = field(default_factory=list)
    dependency_files: dict[str, str] = field(default_factory=dict)  # filename -> content
    recent_issues: list[dict] = field(default_factory=list)
    closed_issues_count: int = 0
    total_issues_count: int = 0


class GitHubRateLimitError(Exception):
    """Rate limit 재시도를 위한 내부 예외."""
    pass


def _headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github.v3+json"}
    if settings.GITHUB_TOKEN:
        h["Authorization"] = f"token {settings.GITHUB_TOKEN}"
    return h


async def _check_rate_limit(resp: httpx.Response) -> None:
    """응답 헤더에서 rate limit 잔여량을 확인하고, 10 미만이면 자발적 대기."""
    remaining = resp.headers.get("X-RateLimit-Remaining")
    if remaining is not None:
        remaining_int = int(remaining)
        if remaining_int < 10:
            reset_ts = resp.headers.get("X-RateLimit-Reset")
            if reset_ts:
                wait_sec = max(int(reset_ts) - int(datetime.now().timestamp()), 1)
                wait_sec = min(wait_sec, 60)  # 최대 60초 대기
            else:
                wait_sec = 30
            logger.warning(
                "Rate limit 잔여 %d — %d초 자발적 대기", remaining_int, wait_sec
            )
            await asyncio.sleep(wait_sec)


def _raise_on_rate_limit(resp: httpx.Response) -> None:
    """403/429 응답이면 GitHubRateLimitError를 발생시켜 tenacity 재시도를 유발."""
    if resp.status_code in (403, 429):
        remaining = resp.headers.get("X-RateLimit-Remaining", "?")
        logger.warning("GitHub rate limit hit: status=%d, remaining=%s", resp.status_code, remaining)
        raise GitHubRateLimitError(
            f"Rate limited: status={resp.status_code}, remaining={remaining}"
        )


# -- 재시도 데코레이터 --------------------------------------------------------

_retry_policy = retry(
    retry=retry_if_exception_type(GitHubRateLimitError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=8),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


@_retry_policy
async def _github_get(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    cache_ttl: int | None = None,
) -> httpx.Response | dict:
    """GitHub API GET 요청 — 캐시 확인 → 요청 → 캐시 저장 → rate limit 체크.

    cache_ttl이 지정되면 캐시 레이어를 사용합니다.
    캐시 히트 시 dict를 반환하고, 캐시 미스 시 httpx.Response를 반환합니다.
    """
    # 캐시 확인
    if cache_ttl is not None:
        cached = await cache_get(url, params)
        if cached is not None:
            return cached  # dict 반환

    # 실제 API 호출
    resp = await client.get(url, params=params, headers=headers or _headers())

    # 403/429 → 재시도
    _raise_on_rate_limit(resp)

    # rate limit 잔여량 체크 → 자발적 대기
    await _check_rate_limit(resp)

    # 성공 시 캐시 저장
    if resp.status_code == 200 and cache_ttl is not None:
        await cache_set(url, params, resp.json(), ttl_seconds=cache_ttl)

    return resp


async def search_github(
    keywords: list[str],
    language_filter: list[str] | None = None,
    min_stars: int = 50,
    max_results_per_keyword: int = 10,
) -> list[RepoBasicInfo]:
    """GitHub Search API로 1차 필터링된 후보 레포를 반환합니다.

    - 키워드별 검색 → 중복 제거 → Stars 기준 정렬
    - 필터: Stars >= min_stars, 12개월 내 커밋, archived가 아닌 활성 레포
    - 캐시: 검색 결과 1시간 TTL
    - 재시도: 403/429 시 지수 백오프 (2초→4초→8초, 최대 3회)
    """
    cutoff_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    seen_repos: set[str] = set()
    all_repos: list[RepoBasicInfo] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for keyword in keywords[:8]:  # 키워드 8개까지만 검색
            query_parts = [keyword, f"pushed:>{cutoff_date}", f"stars:>={min_stars}"]
            if language_filter:
                query_parts.append(f"language:{language_filter[0]}")
            query = " ".join(query_parts)

            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": max_results_per_keyword,
            }
            url = f"{settings.GITHUB_API_BASE}/search/repositories"

            try:
                result = await _github_get(
                    client, url, params=params, cache_ttl=TTL_SEARCH,
                )

                # 캐시 히트: dict 반환됨
                if isinstance(result, dict):
                    data = result
                else:
                    # httpx.Response
                    if result.status_code != 200:
                        logger.warning(
                            "GitHub search failed: status=%d, keyword=%s",
                            result.status_code,
                            keyword,
                        )
                        continue
                    data = result.json()

                for item in data.get("items", []):
                    full_name = item["full_name"]
                    if full_name in seen_repos or item.get("archived"):
                        continue
                    seen_repos.add(full_name)

                    all_repos.append(
                        RepoBasicInfo(
                            owner=item["owner"]["login"],
                            name=item["name"],
                            full_name=full_name,
                            url=item["html_url"],
                            description=item.get("description") or "",
                            stars=item["stargazers_count"],
                            forks=item["forks_count"],
                            language=item.get("language") or "",
                            updated_at=item["updated_at"],
                            open_issues=item["open_issues_count"],
                            has_wiki=item.get("has_wiki", False),
                            license_name=(
                                item.get("license", {}).get("spdx_id")
                                if item.get("license")
                                else None
                            ),
                            size_kb=item.get("size", 0),
                            topics=item.get("topics", []),
                        )
                    )

            except GitHubRateLimitError:
                # 3회 재시도 후에도 실패 → AppException으로 변환
                raise AppException(
                    code=ErrorCodes.GITHUB_RATE_LIMIT,
                    message="GitHub API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
                    status_code=429,
                    retry_after=60,
                )
            except AppException:
                raise
            except Exception as e:
                logger.warning("GitHub search error: keyword=%s, err=%s", keyword, e)
                continue

    # Stars 기준 내림차순 정렬
    all_repos.sort(key=lambda r: r.stars, reverse=True)

    logger.info(
        "GitHub 검색 완료: %d개 키워드 → %d개 후보",
        min(len(keywords), 8),
        len(all_repos),
    )

    return all_repos[:20]  # 상위 20개


async def fetch_repo_details(repo: RepoBasicInfo) -> RepoDetailedInfo:
    """레포의 상세 정보를 조회합니다 (README, 파일 트리, 의존성, 이슈).

    딥 리딩 분석에 필요한 데이터를 수집합니다.
    캐시: 24시간 TTL. 재시도: 403/429 시 지수 백오프.
    """
    detailed = RepoDetailedInfo(**vars(repo))

    async with httpx.AsyncClient(timeout=20.0) as client:
        headers = _headers()
        base = f"{settings.GITHUB_API_BASE}/repos/{repo.full_name}"

        # README
        try:
            resp = await _github_get(
                client,
                f"{base}/readme",
                headers={**headers, "Accept": "application/vnd.github.v3.raw"},
                cache_ttl=TTL_REPO_DETAIL,
            )
            if isinstance(resp, dict):
                # 캐시된 README는 dict로 저장됨
                content = resp.get("_raw_text", "")
            elif resp.status_code == 200:
                content = resp.text
                # raw text를 캐시에 저장 (JSON 직렬화를 위해 dict 래핑)
                await cache_set(
                    f"{base}/readme", None,
                    {"_raw_text": content},
                    ttl_seconds=TTL_REPO_DETAIL,
                )
            else:
                content = ""

            if content:
                if len(content) > 4000:
                    detailed.readme_content = content[:3000] + "\n...(중략)...\n" + content[-1000:]
                else:
                    detailed.readme_content = content
        except GitHubRateLimitError:
            logger.warning("README 조회 rate limit: %s", repo.full_name)
        except Exception as e:
            logger.debug("README 조회 실패: %s — %s", repo.full_name, e)

        # 파일 트리 (depth 2)
        try:
            result = await _github_get(
                client,
                f"{base}/git/trees/HEAD",
                params={"recursive": "1"},
                headers=headers,
                cache_ttl=TTL_REPO_DETAIL,
            )
            if isinstance(result, dict):
                tree = result.get("tree", [])
            elif result.status_code == 200:
                tree = result.json().get("tree", [])
            else:
                tree = []

            detailed.file_tree = [
                item["path"]
                for item in tree
                if item["type"] == "blob" and item["path"].count("/") <= 2
            ][:100]  # 최대 100개
        except GitHubRateLimitError:
            logger.warning("파일 트리 조회 rate limit: %s", repo.full_name)
        except Exception as e:
            logger.debug("파일 트리 조회 실패: %s — %s", repo.full_name, e)

        # 의존성 파일 (package.json, requirements.txt 등)
        dep_files = ["package.json", "requirements.txt", "Pipfile", "pyproject.toml", "go.mod", "Cargo.toml"]
        for dep_file in dep_files:
            try:
                result = await _github_get(
                    client,
                    f"{base}/contents/{dep_file}",
                    headers={**headers, "Accept": "application/vnd.github.v3.raw"},
                    cache_ttl=TTL_REPO_DETAIL,
                )
                if isinstance(result, dict):
                    content = result.get("_raw_text", "")[:2000]
                elif result.status_code == 200:
                    content = result.text[:2000]
                    await cache_set(
                        f"{base}/contents/{dep_file}", None,
                        {"_raw_text": content},
                        ttl_seconds=TTL_REPO_DETAIL,
                    )
                else:
                    continue

                if content:
                    detailed.dependency_files[dep_file] = content
            except GitHubRateLimitError:
                logger.warning("의존성 파일 조회 rate limit: %s/%s", repo.full_name, dep_file)
            except Exception:
                pass

        # 최근 이슈 10개
        try:
            issues_url = f"{base}/issues"
            issues_params = {"state": "all", "per_page": "10", "sort": "updated"}

            # 이슈 API는 list를 반환하므로 캐시에서 직접 조회
            cached_issues = await cache_get(issues_url, issues_params)
            if cached_issues is not None:
                issues = cached_issues.get("_issues", [])
            else:
                resp = await _github_get(
                    client, issues_url, params=issues_params, headers=headers,
                )
                if isinstance(resp, dict):
                    issues = []
                elif resp.status_code == 200:
                    issues = resp.json()
                    await cache_set(
                        issues_url, issues_params,
                        {"_issues": issues},
                        ttl_seconds=TTL_REPO_DETAIL,
                    )
                else:
                    issues = []

            if isinstance(issues, list):
                detailed.recent_issues = [
                    {
                        "title": issue["title"],
                        "state": issue["state"],
                        "labels": [l["name"] for l in issue.get("labels", [])],
                        "created_at": issue["created_at"],
                    }
                    for issue in issues
                    if "pull_request" not in issue  # PR 제외
                ]
                detailed.total_issues_count = repo.open_issues
                detailed.closed_issues_count = sum(
                    1 for i in issues if i["state"] == "closed"
                )
        except GitHubRateLimitError:
            logger.warning("이슈 조회 rate limit: %s", repo.full_name)
        except Exception as e:
            logger.debug("이슈 조회 실패: %s — %s", repo.full_name, e)

    return detailed
