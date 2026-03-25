"""4-Step 스킬 검색 파이프라인 — SSE 이벤트 발송 + 에러 전파 정책.

에러 정책:
- Step 1~2 (Critical): 실패 → 즉시 종료
- Step 3~4 (Graceful): 부분 실패 허용

SSE 이벤트 형식:
  running:    {"step": N, "progress": P, "message": "...", "status": "running"}
  completed:  {"step": 4, "progress": 100, "status": "completed", "result_id": "xxx"}
  failed:     {"step": N, "progress": P, "status": "failed", "error": "..."}
  no_results: {"step": 2, "progress": 100, "status": "no_results", "message": "..."}
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Awaitable

from models.error_models import AppException
from models.skill_models import SkillSearchInput, ClassifiedSkill
from services.llm_client import call_gpt4o_structured
from services.skillsmp_client import search_skills, fetch_skill_detail
from services.skill_analyzer import analyze_skill, classify_top3_skills
from services.db import db_insert, db_update

logger = logging.getLogger(__name__)

EventEmitter = Callable[[dict[str, Any]], Awaitable[None]]

# 키워드 생성용 JSON Schema
KEYWORD_EXPANSION_SCHEMA = {
    "type": "object",
    "properties": {
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 8,
        },
    },
    "required": ["keywords"],
    "additionalProperties": False,
}


async def run_skill_pipeline(
    search_id: str,
    brief: SkillSearchInput,
    emit: EventEmitter,
) -> None:
    """4단계 스킬 검색 파이프라인."""
    error_log: list[dict] = []

    try:
        # ═══════════════════════════════════════════
        # Step 1: 브리프 파싱 + 검색 키워드 생성 (Critical)
        # ═══════════════════════════════════════════
        await emit({"step": 1, "progress": 5, "message": "브리프를 분석하고 검색 키워드를 생성하는 중...", "status": "running"})

        try:
            keywords = await _generate_keywords(brief.query_ko, brief.project_stack)
        except Exception as e:
            await _fail(search_id, emit, error_log, step=1, progress=5,
                        message=f"키워드 생성 실패: {e}")
            return

        if not keywords:
            await _fail(search_id, emit, error_log, step=1, progress=10,
                        message="검색 키워드를 생성할 수 없습니다.")
            return

        await db_update("skill_searches", search_id, {
            "keywords_en": keywords,
            "current_step": 1,
            "status": "running",
        })

        # ═══════════════════════════════════════════
        # Step 2: SkillsMP API 검색 (Critical)
        # ═══════════════════════════════════════════
        kw_count = len(keywords)
        await emit({"step": 2, "progress": 20, "message": f"{kw_count}개 키워드로 SkillsMP 검색 중...", "status": "running"})

        try:
            all_skills = await _search_all_keywords(keywords)
        except AppException as e:
            await _fail(search_id, emit, error_log, step=2, progress=20, message=e.message)
            return
        except Exception as e:
            await _fail(search_id, emit, error_log, step=2, progress=20,
                        message=f"SkillsMP 검색 실패: {e}")
            return

        if not all_skills:
            error_log.append({"step": 2, "type": "no_results"})
            await db_update("skill_searches", search_id, {
                "status": "no_results", "current_step": 2, "error_log": error_log,
            })
            await emit({
                "step": 2, "progress": 100,
                "message": "조건에 맞는 스킬을 찾지 못했습니다. 다른 키워드로 시도해보세요.",
                "status": "no_results",
            })
            return

        # SKILL.md 원문 조회
        await emit({"step": 2, "progress": 30, "message": f"{len(all_skills)}개 스킬의 SKILL.md를 조회하는 중...", "status": "running"})

        detailed_skills = []
        for skill in all_skills[:10]:
            try:
                detail = await fetch_skill_detail(skill)
                detailed_skills.append(detail)
            except Exception as e:
                error_log.append({"step": 2, "skill": skill.name, "error": str(e)})

        if not detailed_skills:
            await _fail(search_id, emit, error_log, step=2, progress=35,
                        message="스킬 상세 정보를 조회할 수 없습니다.")
            return

        await db_update("skill_searches", search_id, {"current_step": 2})

        # ═══════════════════════════════════════════
        # Step 3: GPT-4o 스킬 분석 + 5축 스코어링 (Graceful)
        # ═══════════════════════════════════════════
        await emit({"step": 3, "progress": 45, "message": "AI가 각 스킬을 분석하는 중...", "status": "running"})

        results = await asyncio.gather(
            *[analyze_skill(s, brief.query_ko, brief.project_stack) for s in detailed_skills],
            return_exceptions=True,
        )

        scored_skills = []
        analysis_failed = 0
        for r in results:
            if isinstance(r, Exception):
                analysis_failed += 1
                error_log.append({"step": 3, "error": str(r)})
            else:
                scored_skills.append(r)

        if analysis_failed > 0:
            await emit({
                "step": 3, "progress": 60,
                "message": f"{analysis_failed}개 스킬 분석 실패, 나머지로 진행",
                "status": "running",
                "warnings": [f"{analysis_failed}개 스킬 분석 실패"],
            })

        if not scored_skills:
            await _fail(search_id, emit, error_log, step=3, progress=60,
                        message="모든 스킬 분석에 실패했습니다.")
            return

        scored_skills.sort(key=lambda s: s.total_score, reverse=True)
        await db_update("skill_searches", search_id, {"current_step": 3})

        # ═══════════════════════════════════════════
        # Step 4: 3종 분류 + 결과 저장 (Graceful)
        # ═══════════════════════════════════════════
        await emit({"step": 4, "progress": 80, "message": "성격별 3종 분류 중...", "status": "running"})

        try:
            classified = await classify_top3_skills(scored_skills, brief.query_ko)
        except Exception as e:
            error_log.append({"step": 4, "error": str(e), "fallback": "score_based"})
            logger.warning("스킬 분류 실패, fallback: %s", e)
            fallback_categories = ["완성도최고", "바로적용", "가장강력"]
            top3 = scored_skills[:3]
            classified = [
                ClassifiedSkill(
                    **s.model_dump(),
                    category=fallback_categories[i],
                    category_reason=f"점수 {i+1}위 기반 자동 배정",
                    rank=i + 1,
                )
                for i, s in enumerate(top3)
            ]

        # DB 저장
        await emit({"step": 4, "progress": 90, "message": "결과를 저장하는 중...", "status": "running"})

        for skill in classified:
            await db_insert("skill_candidates", {
                "search_id": search_id,
                "skill_id": skill.skill_id,
                "skill_name": skill.name,
                "github_url": skill.github_url,
                "skill_path": skill.skill_path,
                "author": skill.author,
                "stars": skill.stars,
                "category": skill.category,
                "category_reason": skill.category_reason,
                "total_score": skill.total_score,
                "score_detail": skill.score_detail.model_dump(),
                "skill_md_preview": skill.skill_md_content[:2000] if skill.skill_md_content else "",
                "confidence_label": skill.confidence_label,
                "pros": skill.pros,
                "cons": skill.cons,
                "warnings": skill.warnings,
            })

        # 완료
        await db_update("skill_searches", search_id, {
            "status": "completed",
            "current_step": 4,
            "candidate_count": len(classified),
            "error_log": error_log if error_log else None,
            "updated_at": datetime.utcnow().isoformat(),
        })

        await emit({
            "step": 4,
            "progress": 100,
            "message": f"검색 완료! {len(classified)}개 스킬을 찾았습니다.",
            "status": "completed",
            "result_id": search_id,
        })

        logger.info("스킬 파이프라인 완료: search_id=%s", search_id)

    except Exception as e:
        await _fail(search_id, emit, error_log, step=0, progress=0,
                    message=f"예상치 못한 오류: {e}")
        logger.exception("스킬 파이프라인 예외: %s", search_id)


async def _generate_keywords(query_ko: str, project_stack: str | None) -> list[str]:
    """GPT-4o로 한국어 → 영어 검색 키워드 변환."""
    user_prompt = (
        f"다음 한국어 기능 설명을 SkillsMP(Claude Code 스킬 마켓플레이스) 검색에 적합한 "
        f"영어 키워드 3~8개로 변환하세요.\n\n"
        f"기능: {query_ko}\n"
        f"스택: {project_stack or '미지정'}\n\n"
        f"키워드는 간결하게, 2~3 단어 이내로 작성하세요."
    )
    raw = await call_gpt4o_structured(
        system_prompt="검색 키워드 생성 전문가입니다. 영어 키워드만 반환하세요.",
        user_prompt=user_prompt,
        json_schema=KEYWORD_EXPANSION_SCHEMA,
        schema_name="skill_keyword_expansion",
        temperature=0.3,
    )
    return raw.get("keywords", [])


async def _search_all_keywords(keywords: list[str]):
    """키워드별 keyword + ai 검색을 병렬 실행하고 중복 제거."""
    from models.skill_models import SkillResult

    seen_ids: set[str] = set()
    all_skills: list[SkillResult] = []

    tasks = []
    for kw in keywords[:5]:
        tasks.append(search_skills(kw, method="keyword"))
        tasks.append(search_skills(kw, method="ai"))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            logger.warning("스킬 검색 실패: %s", result)
            continue
        for skill in result:
            if skill.skill_id not in seen_ids:
                seen_ids.add(skill.skill_id)
                all_skills.append(skill)

    return all_skills[:20]


async def _fail(
    search_id: str,
    emit: EventEmitter,
    error_log: list[dict],
    *,
    step: int,
    progress: int,
    message: str,
) -> None:
    """파이프라인 실패 처리."""
    error_log.append({"step": step, "fatal": True, "error": message})
    await db_update("skill_searches", search_id, {
        "status": "failed",
        "current_step": step,
        "error_log": error_log,
    })
    await emit({
        "step": step,
        "progress": progress,
        "message": message,
        "status": "failed",
        "error": message,
    })
