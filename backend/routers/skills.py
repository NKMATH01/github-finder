"""스킬 검색/분석/설치 API 라우터 — SSE 실시간 진행률."""

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse

from models.skill_models import (
    SkillSearchRequest,
    SkillSearchResponse,
    SkillSearchStatus,
    SkillSearchResults,
    ClassifiedSkill,
    SkillPackage,
)
from models.error_models import AppException, ErrorCodes
from services.skill_pipeline import run_skill_pipeline
from services.skill_installer import download_skill, prepare_install_command
from services.skillsmp_client import fetch_skill_md
from services.db import db_insert, db_update, db_select, db_get_by_id

router = APIRouter()
logger = logging.getLogger(__name__)

# 인메모리 진행 상태
_skill_progress: dict[str, dict] = {}
_skill_events: dict[str, asyncio.Queue] = {}


async def _emit(search_id: str, event: dict) -> None:
    """파이프라인에서 호출 — 진행 상태 업데이트 + SSE 이벤트 발송."""
    _skill_progress[search_id] = event
    queue = _skill_events.get(search_id)
    if queue:
        await queue.put(event)


async def _run_skill_search(search_id: str, brief):
    """백그라운드에서 스킬 파이프라인 실행."""
    try:
        await run_skill_pipeline(search_id, brief, lambda ev: _emit(search_id, ev))
    except Exception as e:
        logger.exception("스킬 파이프라인 예외: %s", search_id)
        await _emit(search_id, {
            "step": 0, "progress": 0,
            "message": "예상치 못한 오류가 발생했습니다.",
            "status": "failed",
            "error": str(e),
        })


def _is_demo_mode() -> bool:
    from config import settings
    api_key = getattr(settings, "SKILLSMP_API_KEY", "")
    return not api_key or not settings.OPENAI_API_KEY


async def _run_demo_skill_pipeline(search_id: str, query_ko: str):
    """데모 모드: mock 스킬 데이터."""
    steps = [
        (1, 10, "브리프를 분석하고 키워드를 생성하는 중..."),
        (2, 35, "SkillsMP에서 스킬을 검색하는 중..."),
        (3, 65, "AI가 각 스킬을 분석하는 중..."),
        (4, 90, "성격별 3종 분류 중..."),
    ]
    for step, progress, message in steps:
        await _emit(search_id, {
            "step": step, "progress": progress,
            "message": message, "status": "running",
        })
        await asyncio.sleep(1)

    await _emit(search_id, {
        "step": 4, "progress": 100,
        "message": "검색 완료! 3개 스킬을 찾았습니다.",
        "status": "completed",
        "result_id": search_id,
    })


# 데모 결과 저장소
_demo_skill_results: dict[str, dict] = {}


# ─── Endpoints ─────────────────────────────────────────


@router.post("/skills/search", response_model=SkillSearchResponse)
async def create_skill_search(request: SkillSearchRequest, background_tasks: BackgroundTasks):
    """스킬 브리프 제출 + 검색 시작 → search_id 즉시 반환."""
    search_id = str(uuid.uuid4())

    _skill_events[search_id] = asyncio.Queue()
    _skill_progress[search_id] = {
        "step": 0, "progress": 0,
        "message": "스킬 검색을 시작합니다...",
        "status": "pending",
    }

    if _is_demo_mode():
        _demo_skill_results[search_id] = {
            "query_ko": request.brief.query_ko,
        }
        background_tasks.add_task(_run_demo_skill_pipeline, search_id, request.brief.query_ko)
        return SkillSearchResponse(search_id=search_id, status="pending")

    await db_insert("skill_searches", {
        "id": search_id,
        "query_ko": request.brief.query_ko[:200],
        "brief": request.brief.model_dump(),
        "keywords_en": [],
        "status": "pending",
        "current_step": 0,
        "error_log": None,
    })

    background_tasks.add_task(_run_skill_search, search_id, request.brief)
    return SkillSearchResponse(search_id=search_id, status="pending")


@router.get("/skills/search/{search_id}/status")
async def get_skill_search_status(search_id: str):
    """스킬 검색 진행 상태 폴링 (SSE fallback)."""
    progress = _skill_progress.get(search_id)
    if progress:
        return SkillSearchStatus(
            status=progress.get("status", "pending"),
            progress=progress.get("progress", 0),
            message=progress.get("message", ""),
            step=progress.get("step", 0),
            warnings=progress.get("warnings"),
        )
    raise AppException(
        code=ErrorCodes.SEARCH_NOT_FOUND,
        message="스킬 검색을 찾을 수 없습니다.",
        status_code=404,
    )


@router.get("/skills/search/{search_id}/stream")
async def stream_skill_search(search_id: str):
    """SSE 실시간 진행률 스트림."""
    if search_id not in _skill_events:
        _skill_events[search_id] = asyncio.Queue()

    queue = _skill_events[search_id]

    async def event_generator():
        current = _skill_progress.get(search_id)
        if current:
            yield f"data: {json.dumps(current, ensure_ascii=False)}\n\n"
            if current.get("status") in ("completed", "failed", "no_results"):
                return

        terminal = {"completed", "failed", "no_results"}
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event.get("status") in terminal:
                    break
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'status': 'heartbeat'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/skills/search/{search_id}/results")
async def get_skill_results(search_id: str):
    """스킬 검색 결과 (Top 3 스킬)."""
    if _is_demo_mode() and search_id in _demo_skill_results:
        return _generate_demo_skill_results(search_id)

    search = await db_get_by_id("skill_searches", search_id)
    if not search:
        raise AppException(
            code=ErrorCodes.SEARCH_NOT_FOUND,
            message="스킬 검색을 찾을 수 없습니다.",
            status_code=404,
        )

    if search.get("status") != "completed":
        raise AppException(
            code=ErrorCodes.SEARCH_NOT_FOUND,
            message="스킬 검색이 아직 완료되지 않았습니다.",
            status_code=404,
        )

    candidates = await db_select(
        "skill_candidates",
        filters={"search_id": search_id},
    )

    return {
        "search_id": search_id,
        "query_ko": search.get("query_ko", ""),
        "candidates": candidates,
    }


@router.post("/skills/download")
async def download_skill_endpoint(body: dict):
    """스킬 파일 다운로드 + 설치 정보 반환."""
    github_url = body.get("github_url", "")
    skill_path = body.get("skill_path", "")

    if not github_url:
        raise AppException(
            code=ErrorCodes.VALIDATION_ERROR,
            message="github_url은 필수입니다.",
            status_code=400,
        )

    package = await download_skill(github_url, skill_path)
    return package.model_dump()


@router.get("/skills/preview/{skill_id}")
async def preview_skill(skill_id: str, github_url: str = "", skill_path: str = ""):
    """SKILL.md 원문 미리보기."""
    if not github_url:
        raise AppException(
            code=ErrorCodes.VALIDATION_ERROR,
            message="github_url 쿼리 파라미터가 필요합니다.",
            status_code=400,
        )

    content = await fetch_skill_md(github_url, skill_path)
    if not content:
        raise AppException(
            code=ErrorCodes.SEARCH_NOT_FOUND,
            message="SKILL.md를 찾을 수 없습니다.",
            status_code=404,
        )

    return {"skill_id": skill_id, "skill_md": content}


# ─── Demo Results ──────────────────────────────────────

def _generate_demo_skill_results(search_id: str) -> dict:
    """데모용 mock 스킬 검색 결과."""
    demo = _demo_skill_results.get(search_id, {})

    return {
        "search_id": search_id,
        "query_ko": demo.get("query_ko", ""),
        "candidates": [
            {
                "skill_id": f"demo-skill-1-{search_id[:8]}",
                "skill_name": "code-reviewer",
                "github_url": "https://github.com/anthropics/claude-code-skills",
                "skill_path": "skills/code-reviewer",
                "author": "anthropics",
                "stars": 2400,
                "category": "완성도최고",
                "category_reason": "문서화 완벽, 예제 풍부, 안정적 동작 확인",
                "total_score": 88,
                "score_detail": {
                    "feature_match": 26, "quality": 23, "compatibility": 18,
                    "community_trust": 13, "install_ease": 8,
                },
                "skill_md_preview": "# Code Reviewer\n\nAutomatically reviews code changes...",
                "pros": ["PR 자동 리뷰 기능 내장", "커스텀 규칙 설정 가능", "한국어 피드백 지원"],
                "cons": ["대규모 PR에서 토큰 비용 증가"],
                "warnings": ["Claude Pro 구독 필요"],
                "install_command": "mkdir -p .claude/skills/code-reviewer && curl -sL ... -o .claude/skills/code-reviewer/SKILL.md",
            },
            {
                "skill_id": f"demo-skill-2-{search_id[:8]}",
                "skill_name": "git-automation",
                "github_url": "https://github.com/example/git-automation-skill",
                "skill_path": "",
                "author": "example",
                "stars": 890,
                "category": "바로적용",
                "category_reason": "SKILL.md 하나만 복사하면 즉시 사용 가능",
                "total_score": 79,
                "score_detail": {
                    "feature_match": 20, "quality": 19, "compatibility": 17,
                    "community_trust": 14, "install_ease": 9,
                },
                "skill_md_preview": "# Git Automation\n\nAutomates common git workflows...",
                "pros": ["설치 즉시 사용 가능", "의존성 없음"],
                "cons": ["고급 워크플로우 미지원", "커스텀 제한적"],
                "warnings": [],
                "install_command": "mkdir -p .claude/skills/git-automation && curl -sL ... -o .claude/skills/git-automation/SKILL.md",
            },
            {
                "skill_id": f"demo-skill-3-{search_id[:8]}",
                "skill_name": "mcp-builder",
                "github_url": "https://github.com/example/mcp-builder-skill",
                "skill_path": "skills/mcp-builder",
                "author": "example",
                "stars": 1200,
                "category": "가장강력",
                "category_reason": "MCP 서버 자동 생성, 가장 풍부한 기능",
                "total_score": 74,
                "score_detail": {
                    "feature_match": 28, "quality": 16, "compatibility": 12,
                    "community_trust": 10, "install_ease": 8,
                },
                "skill_md_preview": "# MCP Builder\n\nBuild MCP servers with ease...",
                "pros": ["MCP 서버 자동 생성", "다양한 프레임워크 지원"],
                "cons": ["학습 곡선 있음", "Node.js 필수"],
                "warnings": ["Node.js 18+ 필요"],
                "install_command": "mkdir -p .claude/skills/mcp-builder && curl -sL ... -o .claude/skills/mcp-builder/SKILL.md",
            },
        ],
    }
