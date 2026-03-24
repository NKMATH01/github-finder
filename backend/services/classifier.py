"""성격별 3종 분류 — GPT-4o Call Point 3.

딥 리딩 결과에서 Top 3를 성격이 다른 후보로 분류합니다.
- 완성도 최고 / 통합 용이 / 고정밀
- 모두 비슷하면 난이도 하/중/상으로 분기
"""

import logging
from dataclasses import dataclass

from services.llm_client import call_gpt4o_structured
from services.brief_parser import ParsedBrief
from services.deep_reader import DeepReadingResult
from models.llm_schemas import THREE_TYPE_CLASSIFICATION_SCHEMA

logger = logging.getLogger(__name__)

# 카테고리 매핑
CATEGORY_MAP = {
    "완성도 최고": "완성도최고",
    "완성도최고": "완성도최고",
    "통합 용이": "통합용이",
    "통합용이": "통합용이",
    "고정밀": "고정밀",
    "난이도 하": "난이도하",
    "난이도하": "난이도하",
    "난이도 중": "난이도중",
    "난이도중": "난이도중",
    "난이도 상": "난이도상",
    "난이도상": "난이도상",
}


@dataclass
class ClassifiedCandidate:
    """분류된 후보."""

    repo_name: str
    category: str
    category_reason: str
    rank: int


@dataclass
class ClassificationResult:
    """3종 분류 결과."""

    classification_type: str  # personality | difficulty
    classification_reason: str
    candidates: list[ClassifiedCandidate]


SYSTEM_PROMPT = """\
당신은 오픈소스 레포를 성격별로 분류하는 전문가입니다.

분류 규칙:
1. 후보들이 서로 다른 가치를 제공하면 "personality" 분류:
   - 완성도 최고: 종합 신뢰도 최고, "안정적으로 쓰고 싶다면 이것"
   - 통합 용이: 설치 간단 + 의존성 최소, "빨리 붙이고 싶다면 이것"
   - 고정밀: 기능 일치도/정확도 최고, "정확도가 중요하다면 이것"

2. 후보들이 비슷한 성격이면 "difficulty" 분류:
   - 난이도 하: 가장 쉬운 것
   - 난이도 중: 중간
   - 난이도 상: 가장 어렵지만 강력한 것

3. 단순히 점수 순서가 아니라 실제로 성격이 달라야 합니다.
4. 각 후보에 대해 왜 그 카테고리인지 구체적 이유를 제시하세요.
"""


async def classify_top3(
    candidates: list[DeepReadingResult],
    brief: ParsedBrief,
) -> ClassificationResult:
    """상위 후보를 성격별 3종으로 분류합니다."""

    # 상위 7~8개의 요약을 GPT-4o에 전달
    candidate_summaries = []
    for i, c in enumerate(candidates[:8]):
        summary = (
            f"{i+1}. {c.repo_name}\n"
            f"   총점: {c.total_score}/100 | Stars: {c.stars}\n"
            f"   기능일치: {c.feature_match}/25 | 실행가능: {c.runnability}/20 | "
            f"설치난이도: {c.install_ease}/10 | 스택호환: {c.stack_compatibility}/5\n"
            f"   장점: {'; '.join(c.pros[:2])}\n"
            f"   단점: {'; '.join(c.cons[:2])}"
        )
        candidate_summaries.append(summary)

    user_prompt = f"""\
다음 후보 레포들 중에서 성격이 다른 Top 3를 선정하고 분류해주세요.

=== 브리프 ===
{brief.to_llm_context()}

=== 후보 목록 (점수 내림차순) ===
{chr(10).join(candidate_summaries)}

위 후보들 중 Top 3를 선정하되, 서로 다른 가치를 제공하는 후보를 골라주세요.
"""

    raw = await call_gpt4o_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        json_schema=THREE_TYPE_CLASSIFICATION_SCHEMA,
        schema_name="three_type_classification",
        temperature=0.3,
    )

    classified = []
    for c in raw["candidates"]:
        # 카테고리명 정규화
        category = CATEGORY_MAP.get(c["assigned_category"], c["assigned_category"])
        classified.append(
            ClassifiedCandidate(
                repo_name=c["repo_name"],
                category=category,
                category_reason=c["category_reason"],
                rank=c["rank"],
            )
        )

    result = ClassificationResult(
        classification_type=raw["classification_type"],
        classification_reason=raw["classification_reason"],
        candidates=classified,
    )

    logger.info(
        "3종 분류 완료: type=%s, top3=%s",
        result.classification_type,
        [(c.repo_name, c.category) for c in result.candidates],
    )

    return result
