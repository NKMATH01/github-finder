"""클론 사전 정보 조회 — GitHub API로 레포 크기/의존성 충돌을 사전 체크."""

import logging

import httpx

from config import settings
from services.brief_parser import ParsedBrief

logger = logging.getLogger(__name__)


async def get_clone_preview(
    repo_url: str,
    repo_name: str,
    known_install_issues: list[str] | None = None,
    stack_conflicts: list[str] | None = None,
) -> dict:
    """클론 전 사전 정보를 조회합니다.

    Returns:
        {repo_name, estimated_size_mb, estimated_seconds, known_issues, stack_conflicts, recommendation}
    """
    estimated_size_mb = None
    estimated_seconds = None

    # GitHub API로 레포 크기 조회
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Accept": "application/vnd.github.v3+json"}
            if settings.GITHUB_TOKEN:
                headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

            # owner/repo 추출
            parts = repo_name.split("/")
            if len(parts) == 2:
                resp = await client.get(
                    f"{settings.GITHUB_API_BASE}/repos/{repo_name}",
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    size_kb = data.get("size", 0)
                    estimated_size_mb = round(size_kb / 1024, 1)
                    # shallow clone은 약 60-70% 크기
                    shallow_mb = estimated_size_mb * 0.65
                    # 대략 1MB당 0.5초
                    estimated_seconds = max(3, int(shallow_mb * 0.5))
    except Exception as e:
        logger.debug("클론 사전 정보 조회 실패: %s — %s", repo_name, e)

    issues = known_install_issues or []
    conflicts = stack_conflicts or []

    # 추천 문구
    if estimated_size_mb and estimated_size_mb > 200:
        recommendation = "대형 레포입니다. 필요한 모듈만 추출하는 것을 권장합니다."
    elif estimated_size_mb and estimated_size_mb > 50:
        recommendation = "중간 크기 레포입니다. 클론에 시간이 걸릴 수 있습니다."
    else:
        recommendation = "클론 권장 (소규모 레포)"

    if len(issues) > 2:
        recommendation += " 설치 이슈가 여러 개 있으니 확인하세요."

    return {
        "repo_name": repo_name,
        "estimated_size_mb": estimated_size_mb,
        "estimated_seconds": estimated_seconds,
        "known_issues": issues,
        "stack_conflicts": conflicts,
        "recommendation": recommendation,
    }
