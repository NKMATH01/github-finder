"""스킬 분석 + 5축 스코어링 + 3종 분류 — GPT-4o 기반.

5축 스코어링:
  ① 기능 매칭 (30점)  ② 품질/완성도 (25점)  ③ 호환성 (20점)
  ④ 커뮤니티 신뢰도 (15점)  ⑤ 설치 용이성 (10점)
"""

import logging
from dataclasses import dataclass

from services.llm_client import call_gpt4o_structured
from models.skill_models import SkillDetail, ScoredSkill, SkillScoreDetail, ClassifiedSkill

logger = logging.getLogger(__name__)

# ─── 스코어링 JSON Schema ───

SKILL_SCORING_SCHEMA = {
    "type": "object",
    "properties": {
        "feature_match": {"type": "integer", "minimum": 0, "maximum": 30},
        "quality": {"type": "integer", "minimum": 0, "maximum": 25},
        "compatibility": {"type": "integer", "minimum": 0, "maximum": 20},
        "community_trust": {"type": "integer", "minimum": 0, "maximum": 15},
        "install_ease": {"type": "integer", "minimum": 0, "maximum": 10},
        "pros": {"type": "array", "items": {"type": "string"}},
        "cons": {"type": "array", "items": {"type": "string"}},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["feature_match", "quality", "compatibility", "community_trust",
                  "install_ease", "pros", "cons", "warnings"],
    "additionalProperties": False,
}

SKILL_CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string"},
                    "assigned_category": {
                        "type": "string",
                        "enum": ["완성도최고", "바로적용", "가장강력"],
                    },
                    "category_reason": {"type": "string"},
                    "rank": {"type": "integer"},
                },
                "required": ["skill_name", "assigned_category", "category_reason", "rank"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["candidates"],
    "additionalProperties": False,
}

SCORING_SYSTEM_PROMPT = """\
당신은 Claude Code/Codex용 스킬(SKILL.md)을 분석하는 전문가입니다.

사용자의 브리프와 스킬의 SKILL.md 내용을 비교하여 5축 스코어를 매기세요:
1. feature_match (0~30): 사용자가 원하는 기능과 스킬이 제공하는 기능의 일치도
2. quality (0~25): SKILL.md의 구조, 문서화 수준, 예제 포함 여부, 완성도
3. compatibility (0~20): 사용자의 프로젝트 스택과 스킬의 호환 여부
4. community_trust (0~15): GitHub star 수, 최근 업데이트, 커뮤니티 활성도
5. install_ease (0~10): 설치 간편도 (의존성 최소, 추가 설정 불필요일수록 높음)

장점(pros), 단점(cons), 주의사항(warnings)을 각각 1~3개씩 작성하세요.
한국어로 작성하세요.
"""

CLASSIFICATION_SYSTEM_PROMPT = """\
당신은 Claude Code용 스킬을 성격별로 분류하는 전문가입니다.

분류 규칙:
1. 완성도최고: 문서화, 예제, 안정성이 가장 뛰어남 — "믿고 쓸 수 있는 스킬"
2. 바로적용: 설치 후 즉시 사용 가능, 의존성 최소 — "지금 바로 쓸 수 있는 스킬"
3. 가장강력: 기능이 가장 풍부하고 정밀함 — "제대로 쓰면 가장 강력한 스킬"

서로 다른 성격의 스킬을 골라야 합니다.
"""


async def analyze_skill(
    skill: SkillDetail,
    query_ko: str,
    project_stack: str | None = None,
) -> ScoredSkill:
    """개별 스킬을 GPT-4o로 분석하여 5축 스코어링합니다."""
    skill_summary = (
        f"스킬명: {skill.name}\n"
        f"설명: {skill.description}\n"
        f"GitHub: {skill.github_url}\n"
        f"Stars: {skill.stars}\n"
        f"작성자: {skill.author}\n"
        f"최근 업데이트: {skill.last_updated or '불명'}\n"
    )
    if skill.skill_md_content:
        md_preview = skill.skill_md_content[:3000]
        skill_summary += f"\n--- SKILL.md 내용 ---\n{md_preview}\n"

    user_prompt = (
        f"=== 사용자 브리프 ===\n"
        f"원하는 기능: {query_ko}\n"
        f"프로젝트 스택: {project_stack or '미지정'}\n\n"
        f"=== 분석할 스킬 ===\n{skill_summary}\n\n"
        f"위 스킬을 브리프 기준으로 5축 스코어링하세요."
    )

    raw = await call_gpt4o_structured(
        system_prompt=SCORING_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        json_schema=SKILL_SCORING_SCHEMA,
        schema_name="skill_scoring",
        temperature=0.2,
    )

    score_detail = SkillScoreDetail(
        feature_match=raw["feature_match"],
        quality=raw["quality"],
        compatibility=raw["compatibility"],
        community_trust=raw["community_trust"],
        install_ease=raw["install_ease"],
    )
    total = sum([
        score_detail.feature_match,
        score_detail.quality,
        score_detail.compatibility,
        score_detail.community_trust,
        score_detail.install_ease,
    ])

    return ScoredSkill(
        skill_id=skill.skill_id,
        name=skill.name,
        description=skill.description,
        github_url=skill.github_url,
        skill_path=skill.skill_path,
        author=skill.author,
        stars=skill.stars,
        last_updated=skill.last_updated,
        skill_md_content=skill.skill_md_content,
        total_score=total,
        score_detail=score_detail,
        pros=raw.get("pros", []),
        cons=raw.get("cons", []),
        warnings=raw.get("warnings", []),
    )


async def classify_top3_skills(
    scored_skills: list[ScoredSkill],
    query_ko: str,
) -> list[ClassifiedSkill]:
    """상위 스킬을 성격별 3종으로 분류합니다."""
    summaries = []
    for i, s in enumerate(scored_skills[:8]):
        summaries.append(
            f"{i+1}. {s.name} (점수: {s.total_score}/100, Stars: {s.stars})\n"
            f"   장점: {'; '.join(s.pros[:2])}\n"
            f"   단점: {'; '.join(s.cons[:2])}"
        )

    user_prompt = (
        f"=== 사용자 요청 ===\n{query_ko}\n\n"
        f"=== 후보 스킬 (점수 내림차순) ===\n"
        f"{chr(10).join(summaries)}\n\n"
        f"위 스킬 중 성격이 다른 Top 3를 선정하고 분류해주세요."
    )

    try:
        raw = await call_gpt4o_structured(
            system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            json_schema=SKILL_CLASSIFICATION_SCHEMA,
            schema_name="skill_classification",
            temperature=0.3,
        )

        classified = []
        for c in raw["candidates"]:
            matched = next((s for s in scored_skills if s.name == c["skill_name"]), None)
            if not matched:
                continue
            classified.append(ClassifiedSkill(
                **matched.model_dump(),
                category=c["assigned_category"],
                category_reason=c["category_reason"],
                rank=c["rank"],
            ))

        if classified:
            return classified

    except Exception as e:
        logger.warning("GPT-4o 스킬 분류 실패, 점수 기반 fallback: %s", e)

    # Fallback: 점수 순 Top 3
    fallback_categories = ["완성도최고", "바로적용", "가장강력"]
    top3 = sorted(scored_skills, key=lambda s: s.total_score, reverse=True)[:3]
    return [
        ClassifiedSkill(
            **s.model_dump(),
            category=fallback_categories[i],
            category_reason=f"GPT-4o 분류 실패, 점수 {i+1}위 기반 자동 배정",
            rank=i + 1,
        )
        for i, s in enumerate(top3)
    ]
