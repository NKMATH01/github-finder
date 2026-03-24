"""7-Step 검색 파이프라인 — SSE 이벤트 발송 + 단계별 에러 정책.

에러 정책:
- Step 1~3 (Critical Path): 실패 → 즉시 종료
- Step 4~7 (Graceful Degradation): 부분 실패 허용, 가능한 범위까지 진행

SSE 이벤트 형식:
  running:    {"step": N, "progress": P, "message": "...", "status": "running"}
  completed:  {"step": 7, "progress": 100, "status": "completed", "result_id": "xxx"}
  failed:     {"step": N, "progress": P, "status": "failed", "error": "..."}
  no_results: {"step": 3, "progress": 100, "status": "no_results", "message": "..."}
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Awaitable

from models.schemas import BriefInput
from models.error_models import AppException, ErrorCodes
from services.brief_parser import parse_brief
from services.keyword_expander import expand_keywords
from services.github_searcher import search_github, fetch_repo_details
from services.deep_reader import analyze_repos_parallel
from services.classifier import classify_top3, ClassifiedCandidate, ClassificationResult
from services.file_identifier import identify_key_files
from services.prompt_generator import generate_basic_prompt
from services.db import db_insert, db_update

logger = logging.getLogger(__name__)

# emit(event_dict) → 코루틴
EventEmitter = Callable[[dict[str, Any]], Awaitable[None]]


async def run_pipeline(
    search_id: str,
    brief_input: BriefInput,
    emit: EventEmitter,
) -> None:
    """7단계 검색 파이프라인.

    각 단계 완료 시 emit()으로 SSE 이벤트를 발송합니다.
    """
    error_log: list[dict] = []

    try:
        # ═══════════════════════════════════════════
        # Step 1: 브리프 파싱 (Critical — 실패 시 즉시 종료)
        # ═══════════════════════════════════════════
        await emit({"step": 1, "progress": 5, "message": "브리프를 분석하는 중...", "status": "running"})
        try:
            parsed = parse_brief(brief_input)
        except Exception as e:
            await _fail(search_id, emit, error_log, step=1, progress=5,
                        message=f"브리프 필수값을 확인해주세요: {e}")
            return

        await db_update("searches", search_id, {"current_step": 1, "status": "running"})

        # ═══════════════════════════════════════════
        # Step 2: 키워드 확장 (Critical — 2회 재시도 → 실패 시 종료)
        # ═══════════════════════════════════════════
        await emit({"step": 2, "progress": 15, "message": "검색 키워드를 확장하는 중...", "status": "running"})

        expansion = None
        for attempt in range(3):
            try:
                expansion = await expand_keywords(parsed)
                break
            except Exception as e:
                error_log.append({"step": 2, "attempt": attempt + 1, "error": str(e)})
                if attempt < 2:
                    await emit({
                        "step": 2, "progress": 15,
                        "message": f"키워드 생성 재시도 중... ({attempt + 2}/3)",
                        "status": "running",
                    })
                    await asyncio.sleep(2 ** attempt)

        if not expansion:
            await _fail(search_id, emit, error_log, step=2, progress=15,
                        message="키워드 생성에 실패했습니다. GPT-4o 응답 오류.")
            return

        await db_update("searches", search_id, {
            "keywords_en": expansion.search_keywords,
            "current_step": 2,
            "updated_at": datetime.utcnow().isoformat(),
        })

        # ═══════════════════════════════════════════
        # Step 3: GitHub 1차 필터링 (Critical — 0건이면 종료)
        # ═══════════════════════════════════════════
        kw_count = len(expansion.search_keywords)
        await emit({"step": 3, "progress": 30, "message": f"GitHub에서 {kw_count}개 키워드로 검색 중...", "status": "running"})

        try:
            basic_repos = await search_github(
                keywords=expansion.search_keywords,
                language_filter=expansion.language_filter,
            )
        except AppException as e:
            if e.code == ErrorCodes.GITHUB_RATE_LIMIT:
                await emit({
                    "step": 3, "progress": 30,
                    "message": "API 한도 접근, 대기 중...",
                    "status": "running",
                    "warnings": ["GitHub API 요청 한도에 근접합니다."],
                })
            await _fail(search_id, emit, error_log, step=3, progress=30, message=e.message)
            return
        except Exception as e:
            await _fail(search_id, emit, error_log, step=3, progress=30,
                        message=f"GitHub 검색 실패: {e}")
            return

        if not basic_repos:
            error_log.append({"step": 3, "type": "no_results"})
            await db_update("searches", search_id, {
                "status": "no_results", "current_step": 3, "error_log": error_log,
            })
            await emit({
                "step": 3, "progress": 100,
                "message": "조건에 맞는 레포를 찾지 못했습니다. 키워드를 수정해보세요.",
                "status": "no_results",
            })
            return

        await db_update("searches", search_id, {"current_step": 3})

        # ═══════════════════════════════════════════
        # Step 4: 상세 정보 조회 (Graceful — 일부 실패 시 스킵)
        # ═══════════════════════════════════════════
        repo_count = min(len(basic_repos), 8)
        await emit({
            "step": 4, "progress": 40,
            "message": f"{len(basic_repos)}개 후보 중 상위 {repo_count}개 상세 조회 중...",
            "status": "running",
        })

        top_repos = basic_repos[:8]
        results = await asyncio.gather(
            *[fetch_repo_details(repo) for repo in top_repos],
            return_exceptions=True,
        )

        detailed_repos = []
        fetch_failed = 0
        for r in results:
            if isinstance(r, Exception):
                fetch_failed += 1
                error_log.append({"step": 4, "error": str(r)})
            else:
                detailed_repos.append(r)

        if fetch_failed > 0:
            await emit({
                "step": 4, "progress": 45,
                "message": f"{fetch_failed}개 레포 조회 실패, 나머지로 계속 진행",
                "status": "running",
                "warnings": [f"{fetch_failed}개 레포 상세 조회 실패"],
            })

        if not detailed_repos:
            await _fail(search_id, emit, error_log, step=4, progress=45,
                        message="모든 레포 상세 조회에 실패했습니다.")
            return

        await db_update("searches", search_id, {"current_step": 4})

        # ═══════════════════════════════════════════
        # Step 5: 딥 리딩 + 7축 스코어링 (Graceful — 전체 실패 시 종료)
        # ═══════════════════════════════════════════
        await emit({
            "step": 5, "progress": 50,
            "message": "AI가 각 레포의 README, 코드, 이슈를 읽고 있습니다...",
            "status": "running",
        })

        try:
            scored_results = await analyze_repos_parallel(detailed_repos, parsed)
        except Exception as e:
            await _fail(search_id, emit, error_log, step=5, progress=50,
                        message=f"AI 분석 전체 실패: {e}")
            return

        if not scored_results:
            await _fail(search_id, emit, error_log, step=5, progress=60,
                        message="AI 분석에 실패했습니다. 잠시 후 다시 시도해주세요.")
            return

        analysis_failed = len(detailed_repos) - len(scored_results)
        if analysis_failed > 0:
            error_log.append({"step": 5, "partial_failure": analysis_failed})
            await emit({
                "step": 5, "progress": 65,
                "message": f"{analysis_failed}개 레포 분석 실패, 나머지로 진행",
                "status": "running",
                "warnings": [f"{analysis_failed}개 레포 분석 실패"],
            })

        await db_update("searches", search_id, {"current_step": 5})

        # ═══════════════════════════════════════════
        # Step 6: 3종 분류 (Graceful — 실패 시 점수 순 fallback)
        # ═══════════════════════════════════════════
        await emit({
            "step": 6, "progress": 80,
            "message": "성격별 3종 분류 중 (완성도/통합용이/고정밀)...",
            "status": "running",
        })

        try:
            classification = await classify_top3(scored_results, parsed)
        except Exception as e:
            # Fallback: 점수 순 상위 3개를 기본 카테고리로 분류
            error_log.append({"step": 6, "error": str(e), "fallback": "score_based"})
            logger.warning("3종 분류 실패, 점수 기반 fallback: %s", e)

            categories = ["완성도최고", "통합용이", "고정밀"]
            top3 = sorted(scored_results, key=lambda r: r.total_score, reverse=True)[:3]
            fallback_candidates = [
                ClassifiedCandidate(
                    repo_name=r.repo_name,
                    category=categories[i] if i < len(categories) else "기타",
                    category_reason="점수 기반 자동 분류 (AI 분류 실패로 인한 fallback)",
                    rank=i + 1,
                )
                for i, r in enumerate(top3)
            ]
            classification = ClassificationResult(
                classification_type="personality",
                classification_reason="점수 기반 fallback",
                candidates=fallback_candidates,
            )

            await emit({
                "step": 6, "progress": 82,
                "message": "분류 실패, 점수 기반 fallback 적용",
                "status": "running",
                "warnings": ["AI 분류 실패, 점수 기반 fallback 적용"],
            })

        await db_update("searches", search_id, {"current_step": 6})

        # ═══════════════════════════════════════════
        # Step 7: 결과 저장 + 프롬프트 생성 (Graceful — 프롬프트 실패 시 스킵)
        # ═══════════════════════════════════════════
        await emit({
            "step": 7, "progress": 90,
            "message": "결과를 정리하고 프롬프트를 생성하는 중...",
            "status": "running",
        })

        prompt_failures = 0
        for classified in classification.candidates:
            matched = next(
                (r for r in scored_results if r.repo_name == classified.repo_name),
                None,
            )
            if not matched:
                continue

            key_files = identify_key_files(matched)

            candidate_data = {
                "search_id": search_id,
                "repo_url": matched.repo_url,
                "repo_name": matched.repo_name,
                "stars": matched.stars,
                "category": classified.category,
                "category_reason": classified.category_reason,
                "total_score": matched.total_score,
                "score_detail": {
                    "feature_match": matched.feature_match,
                    "runnability": matched.runnability,
                    "maintenance": matched.maintenance,
                    "issue_resolution": matched.issue_resolution,
                    "install_ease": matched.install_ease,
                    "documentation": matched.documentation,
                    "stack_compatibility": matched.stack_compatibility,
                },
                "key_files": key_files,
                "pros": matched.pros,
                "cons": matched.cons,
                "failure_scenarios": matched.failure_scenarios,
                "estimated_size_mb": matched.estimated_size_mb,
                "known_install_issues": [],
                "stack_conflicts": [],
                "rank": classified.rank,
            }

            saved_candidate = await db_insert("candidates", candidate_data)

            # 프롬프트 생성 (실패 시 스킵)
            try:
                prompt_result = await generate_basic_prompt(matched, parsed)
                await db_insert("prompts", {
                    "candidate_id": saved_candidate["id"],
                    "target": "claude",
                    "content": prompt_result.get("full_prompt_text", ""),
                    "alternative_prompts": (
                        [prompt_result.get("alternative_plan", {})]
                        if prompt_result.get("alternative_plan")
                        else []
                    ),
                })
                logger.info("프롬프트 생성 완료: %s", matched.repo_name)
            except Exception as e:
                prompt_failures += 1
                error_log.append({"step": 7, "repo": matched.repo_name, "error": str(e)})
                logger.warning("프롬프트 생성 실패 (스킵): %s — %s", matched.repo_name, e)

        if prompt_failures > 0:
            await emit({
                "step": 7, "progress": 95,
                "message": f"{prompt_failures}개 프롬프트 생성 실패",
                "status": "running",
                "warnings": [f"{prompt_failures}개 프롬프트 생성 실패"],
            })

        # ═══════════════════════════════════════════
        # 완료
        # ═══════════════════════════════════════════
        await db_update("searches", search_id, {
            "status": "completed",
            "current_step": 7,
            "candidate_count": len(classification.candidates),
            "error_log": error_log if error_log else None,
            "updated_at": datetime.utcnow().isoformat(),
        })

        await emit({
            "step": 7,
            "progress": 100,
            "message": f"검색 완료! {len(classification.candidates)}개 후보를 찾았습니다.",
            "status": "completed",
            "result_id": search_id,
        })

        logger.info("검색 파이프라인 완료: search_id=%s", search_id)

    except Exception as e:
        await _fail(search_id, emit, error_log, step=0, progress=0,
                    message=f"예상치 못한 오류가 발생했습니다: {e}")
        logger.exception("검색 파이프라인 예외: %s", search_id)


async def _fail(
    search_id: str,
    emit: EventEmitter,
    error_log: list[dict],
    *,
    step: int,
    progress: int,
    message: str,
) -> None:
    """파이프라인 실패 처리 — DB 업데이트 + SSE 이벤트 발송."""
    error_log.append({"step": step, "fatal": True, "error": message})
    await db_update("searches", search_id, {
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
