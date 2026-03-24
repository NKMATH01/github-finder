"""딥 리딩 + 7축 스코어링 — GPT-4o Call Point 2.

각 후보 레포에 대해 README·코드 구조·이슈를 LLM이 읽고 분석합니다.
"""

import asyncio
import logging
from dataclasses import dataclass, field

from services.llm_client import call_gpt4o_structured
from services.brief_parser import ParsedBrief
from services.github_searcher import RepoDetailedInfo
from models.llm_schemas import DEEP_READING_SCHEMA

logger = logging.getLogger(__name__)


@dataclass
class DeepReadingResult:
    """딥 리딩 분석 결과 — 7축 점수 + 장단점 + 핵심 파일."""

    repo_name: str
    repo_url: str
    stars: int

    # 7축 점수
    feature_match: int = 0
    runnability: int = 0
    maintenance: int = 0
    issue_resolution: int = 0
    install_ease: int = 0
    documentation: int = 0
    stack_compatibility: int = 0

    total_score: int = 0

    # 분석 결과
    feature_match_reason: str = ""
    runnability_evidence: str = ""
    stack_compatibility_detail: str = ""
    key_files: list[dict] = field(default_factory=list)
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)
    failure_scenarios: list[str] = field(default_factory=list)
    install_command: str = ""
    estimated_size_mb: float = 0


# 가중치 프리셋
WEIGHT_PRESETS = {
    "balanced": {
        "feature_match": 1.0,
        "runnability": 1.0,
        "maintenance": 1.0,
        "issue_resolution": 1.0,
        "install_ease": 1.0,
        "documentation": 1.0,
        "stack_compatibility": 1.0,
    },
    "accuracy": {
        "feature_match": 1.2,
        "runnability": 1.0,
        "maintenance": 1.0,
        "issue_resolution": 1.0,
        "install_ease": 0.5,
        "documentation": 1.0,
        "stack_compatibility": 1.0,
    },
    "speed": {
        "feature_match": 0.8,
        "runnability": 1.0,
        "maintenance": 1.0,
        "issue_resolution": 1.0,
        "install_ease": 1.5,
        "documentation": 1.0,
        "stack_compatibility": 1.5,
    },
}


SYSTEM_PROMPT = """\
당신은 GitHub 오픈소스 레포를 분석하는 전문가입니다.
사용자의 브리프(프로젝트 요구사항)와 레포의 상세 정보를 비교하여 7가지 축으로 평가합니다.

평가 원칙:
- 근거 없이 높은 점수를 주지 마세요
- 각 점수에는 반드시 구체적 근거를 제시하세요
- 단점에는 구체적인 실패 시나리오를 포함하세요
- 브리프의 프로젝트 스택과의 호환성을 반드시 분석하세요
- 핵심 파일은 실제 파일 트리에 존재하는 파일만 지목하세요

7가지 평가축:
1. 기능 일치도 (0-25): README·코드와 브리프의 매칭도
2. 실행 가능성 (0-20): 데모, Docker, CI, 설치 문서 여부
3. 유지보수 활성도 (0-15): 최근 커밋 빈도
4. 이슈 해결률 (0-15): 닫힌 이슈 / 전체 이슈 비율
5. 설치 난이도 (0-10): npm/pip 한 줄이면 10점, 복잡하면 낮음
6. 문서/예제 품질 (0-10): README+예제+튜토리얼 충실도
7. 스택 호환성 (0-5): 브리프 스택과 동일 언어/프레임워크이면 5점

중요: 모든 텍스트 필드(pros, cons, failure_scenarios, reason, evidence 등)는 반드시 한국어로 작성하세요.
role 필드도 한국어로 작성하세요 (예: "메인 로직", "설정 파일" 등).
"""


def _build_repo_context(repo: RepoDetailedInfo) -> str:
    """레포 상세 정보를 LLM에 전달할 텍스트로 변환."""
    parts = [
        f"## 레포: {repo.full_name}",
        f"Stars: {repo.stars} | Forks: {repo.forks} | 언어: {repo.language}",
        f"최근 업데이트: {repo.updated_at}",
        f"크기: {repo.size_kb}KB",
        f"라이선스: {repo.license_name or '없음'}",
        f"토픽: {', '.join(repo.topics) if repo.topics else '없음'}",
        "",
        "### README (일부)",
        repo.readme_content[:3000] if repo.readme_content else "(README 없음)",
        "",
        "### 파일 트리",
        "\n".join(repo.file_tree[:50]) if repo.file_tree else "(조회 실패)",
    ]

    if repo.dependency_files:
        parts.append("\n### 의존성 파일")
        for fname, content in repo.dependency_files.items():
            parts.append(f"\n#### {fname}")
            parts.append(content[:1000])

    if repo.recent_issues:
        parts.append("\n### 최근 이슈")
        for issue in repo.recent_issues[:5]:
            parts.append(
                f"- [{issue['state']}] {issue['title']} "
                f"(labels: {', '.join(issue.get('labels', []))})"
            )
        if repo.total_issues_count:
            ratio = (
                repo.closed_issues_count / max(repo.total_issues_count, 1) * 100
            )
            parts.append(f"이슈 해결률: {ratio:.0f}% ({repo.closed_issues_count}/{repo.total_issues_count})")

    return "\n".join(parts)


def _apply_weights(result: DeepReadingResult, priority: str) -> int:
    """우선순위에 따라 가중치를 적용하고 총점을 계산합니다."""
    weights = WEIGHT_PRESETS.get(priority, WEIGHT_PRESETS["balanced"])

    raw_scores = {
        "feature_match": result.feature_match,
        "runnability": result.runnability,
        "maintenance": result.maintenance,
        "issue_resolution": result.issue_resolution,
        "install_ease": result.install_ease,
        "documentation": result.documentation,
        "stack_compatibility": result.stack_compatibility,
    }

    weighted_sum = sum(
        score * weights.get(axis, 1.0) for axis, score in raw_scores.items()
    )

    # 100점 만점 정규화
    max_possible = sum(
        max_score * weights.get(axis, 1.0)
        for axis, max_score in {
            "feature_match": 25,
            "runnability": 20,
            "maintenance": 15,
            "issue_resolution": 15,
            "install_ease": 10,
            "documentation": 10,
            "stack_compatibility": 5,
        }.items()
    )

    return round(weighted_sum / max_possible * 100) if max_possible > 0 else 0


async def analyze_repo(
    repo: RepoDetailedInfo, brief: ParsedBrief
) -> DeepReadingResult:
    """단일 레포에 대해 GPT-4o 딥 리딩 분석을 수행합니다."""

    repo_context = _build_repo_context(repo)
    brief_context = brief.to_llm_context()

    user_prompt = f"""\
다음 레포를 아래 브리프 기준으로 분석해주세요.

=== 브리프 ===
{brief_context}

=== 레포 정보 ===
{repo_context}
"""

    raw = await call_gpt4o_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        json_schema=DEEP_READING_SCHEMA,
        schema_name="deep_reading_analysis",
        temperature=0.3,
        max_tokens=4096,
    )

    result = DeepReadingResult(
        repo_name=repo.full_name,
        repo_url=repo.url,
        stars=repo.stars,
        feature_match=raw["feature_match_score"],
        runnability=raw["runnability_score"],
        maintenance=raw["maintenance_score"],
        issue_resolution=raw["issue_resolution_score"],
        install_ease=raw["install_ease_score"],
        documentation=raw["documentation_score"],
        stack_compatibility=raw["stack_compatibility_score"],
        feature_match_reason=raw["feature_match_reason"],
        runnability_evidence=raw["runnability_evidence"],
        stack_compatibility_detail=raw["stack_compatibility_detail"],
        key_files=raw["key_files"],
        pros=raw["pros"],
        cons=raw["cons"],
        failure_scenarios=raw["failure_scenarios"],
        install_command=raw["install_command"],
        estimated_size_mb=raw["estimated_size_mb"],
    )

    result.total_score = _apply_weights(result, brief.priority)

    logger.info(
        "딥 리딩 완료: %s → score=%d (priority=%s)",
        repo.full_name,
        result.total_score,
        brief.priority,
    )

    return result


async def analyze_repos_parallel(
    repos: list[RepoDetailedInfo],
    brief: ParsedBrief,
    max_concurrent: int = 4,
) -> list[DeepReadingResult]:
    """여러 레포를 병렬로 분석합니다.

    OpenAI rate limit을 고려하여 동시 요청 수를 제한합니다.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _analyze_with_limit(repo: RepoDetailedInfo) -> DeepReadingResult | None:
        async with semaphore:
            try:
                return await analyze_repo(repo, brief)
            except Exception as e:
                logger.warning("딥 리딩 실패 (스킵): %s — %s", repo.full_name, e)
                return None

    tasks = [_analyze_with_limit(repo) for repo in repos]
    results = await asyncio.gather(*tasks)

    # None 제거 + 점수 내림차순 정렬
    valid_results = [r for r in results if r is not None]
    valid_results.sort(key=lambda r: r.total_score, reverse=True)

    logger.info(
        "병렬 딥 리딩 완료: %d/%d 성공",
        len(valid_results),
        len(repos),
    )

    return valid_results
