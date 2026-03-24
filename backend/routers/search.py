"""검색 API 라우터 — SSE 실시간 진행률 + 폴링 fallback."""

import asyncio
import json
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse

from models.schemas import SearchRequest, SearchResponse, SearchStatus
from models.error_models import AppException, ErrorCodes
from services.pipeline import run_pipeline
from services.db import db_insert, db_update, db_select, db_get_by_id

router = APIRouter()
logger = logging.getLogger(__name__)

# 인메모리 진행 상태 (개인용이므로 충분)
_search_progress: dict[str, dict] = {}

# SSE 이벤트 큐 — search_id → asyncio.Queue
_search_events: dict[str, asyncio.Queue] = {}


async def _emit(search_id: str, event: dict) -> None:
    """파이프라인에서 호출 — 진행 상태 업데이트 + SSE 이벤트 발송."""
    _search_progress[search_id] = event
    queue = _search_events.get(search_id)
    if queue:
        await queue.put(event)


async def _run_search(search_id: str, brief_input):
    """백그라운드에서 파이프라인 실행."""
    try:
        await run_pipeline(search_id, brief_input, lambda ev: _emit(search_id, ev))
    except Exception as e:
        logger.exception("파이프라인 예외: %s", search_id)
        await _emit(search_id, {
            "step": 0, "progress": 0,
            "message": "예상치 못한 오류가 발생했습니다.",
            "status": "failed",
            "error": str(e),
        })


def _is_demo_mode() -> bool:
    from config import settings
    return not settings.SUPABASE_URL or not settings.OPENAI_API_KEY


async def _run_demo_pipeline(search_id: str, brief_goal: str):
    """데모 모드: mock 데이터로 UI 테스트."""
    steps = [
        (1, 10, "브리프를 분석하는 중..."),
        (2, 25, "검색 키워드를 확장하는 중..."),
        (3, 40, "GitHub에서 후보를 검색하는 중..."),
        (4, 55, "상세 정보를 조회하는 중..."),
        (5, 70, "AI가 각 레포를 분석하는 중..."),
        (6, 85, "성격별 3종 분류 중..."),
        (7, 95, "결과를 정리하는 중..."),
    ]
    for step, progress, message in steps:
        await _emit(search_id, {
            "step": step,
            "progress": progress,
            "message": message,
            "status": "running",
        })
        await asyncio.sleep(1)

    await _emit(search_id, {
        "step": 7,
        "progress": 100,
        "message": "검색 완료! 3개 후보를 찾았습니다.",
        "status": "completed",
        "result_id": search_id,
    })


# 데모용 mock 검색 결과
_demo_results: dict[str, dict] = {}


# ─── Endpoints ─────────────────────────────────────────


@router.post("/search", response_model=SearchResponse)
async def create_search(request: SearchRequest, background_tasks: BackgroundTasks):
    """브리프 제출 + 검색 시작 → search_id 즉시 반환."""
    search_id = str(uuid.uuid4())

    # SSE 큐 생성
    _search_events[search_id] = asyncio.Queue()

    # 진행 상태 초기화
    _search_progress[search_id] = {
        "step": 0, "progress": 0,
        "message": "검색을 시작합니다...",
        "status": "pending",
    }

    # 데모 모드
    if _is_demo_mode():
        _demo_results[search_id] = {
            "brief": request.brief.model_dump(),
            "goal": request.brief.goal_description,
        }
        background_tasks.add_task(_run_demo_pipeline, search_id, request.brief.goal_description)
        return SearchResponse(
            search_id=search_id,
            keywords_en=["gaze tracking", "eye tracking", "head pose estimation"],
            status="pending",
        )

    # Supabase에 검색 기록 생성
    await db_insert("searches", {
        "id": search_id,
        "query_ko": request.brief.goal_description[:200],
        "brief": request.brief.model_dump(),
        "keywords_en": [],
        "target_platform": request.brief.execution_environment,
        "status": "pending",
        "current_step": 0,
        "error_log": None,
    })

    # 백그라운드에서 파이프라인 실행
    background_tasks.add_task(_run_search, search_id, request.brief)

    return SearchResponse(
        search_id=search_id,
        keywords_en=[],
        status="pending",
    )


@router.get("/search/{search_id}/stream")
async def stream_search(search_id: str):
    """SSE 실시간 진행률 스트림.

    클라이언트는 EventSource로 연결하여 실시간 이벤트를 수신합니다.
    completed/failed/no_results 이벤트 수신 후 연결이 종료됩니다.
    """
    # 큐가 없으면 새로 생성 (SSE 재연결 대응)
    if search_id not in _search_events:
        _search_events[search_id] = asyncio.Queue()

    queue = _search_events[search_id]

    async def event_generator():
        # 이미 진행 중이거나 완료된 경우, 현재 상태를 즉시 전송
        current = _search_progress.get(search_id)
        if current:
            yield f"data: {json.dumps(current, ensure_ascii=False)}\n\n"
            if current.get("status") in ("completed", "failed", "no_results"):
                return

        # 스트림 이벤트 대기
        terminal_statuses = {"completed", "failed", "no_results"}
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event.get("status") in terminal_statuses:
                    break
            except asyncio.TimeoutError:
                # 하트비트 (연결 유지)
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


@router.get("/search/{search_id}/status", response_model=SearchStatus)
async def get_search_status(search_id: str):
    """검색 진행 상태 폴링 (SSE fallback)."""
    progress = _search_progress.get(search_id)
    if progress:
        return SearchStatus(
            status=progress.get("status", "pending"),
            progress=progress.get("progress", 0),
            message=progress.get("message", ""),
            step=progress.get("step", 0),
            warnings=progress.get("warnings"),
        )

    if _is_demo_mode():
        raise AppException(
            code=ErrorCodes.SEARCH_NOT_FOUND,
            message="검색을 찾을 수 없습니다.",
            status_code=404,
        )

    search = await db_get_by_id("searches", search_id)
    if not search:
        raise AppException(
            code=ErrorCodes.SEARCH_NOT_FOUND,
            message="검색 결과를 찾을 수 없습니다.",
            status_code=404,
        )

    return SearchStatus(
        status=search.get("status", "pending"),
        progress=100 if search.get("status") == "completed" else 0,
        message="",
        step=search.get("current_step", 0),
    )


@router.get("/search/{search_id}/results")
async def get_search_results(search_id: str):
    """검색 결과 (Top 3 후보)."""
    # 데모 모드
    if _is_demo_mode() and search_id in _demo_results:
        return _generate_demo_results(search_id)

    search = await db_get_by_id("searches", search_id)
    if not search:
        raise AppException(
            code=ErrorCodes.SEARCH_NOT_FOUND,
            message="검색 결과를 찾을 수 없습니다.",
            status_code=404,
        )

    if search.get("status") != "completed":
        raise AppException(
            code=ErrorCodes.SEARCH_NOT_FOUND,
            message="검색이 아직 완료되지 않았습니다.",
            status_code=404,
        )

    candidates = await db_select(
        "candidates",
        filters={"search_id": search_id},
        order_by="rank",
    )

    return {
        "search_id": search_id,
        "brief_summary": search.get("brief", {}),
        "candidates": [
            {
                "id": c["id"],
                "rank": c["rank"],
                "category": c["category"],
                "repo_url": c["repo_url"],
                "repo_name": c["repo_name"],
                "total_score": c["total_score"],
                "score_detail": c.get("score_detail", {}),
                "confidence_label": c.get("confidence_label", "LLM 분석 기반 (실행 미검증)"),
                "stars": c.get("stars", 0),
                "key_files": c.get("key_files", []),
                "pros": c.get("pros", []),
                "cons": c.get("cons", []),
                "failure_scenarios": c.get("failure_scenarios", []),
                "estimated_size_mb": c.get("estimated_size_mb"),
                "estimated_clone_seconds": c.get("estimated_clone_seconds"),
                "known_install_issues": c.get("known_install_issues", []),
                "stack_conflicts": c.get("stack_conflicts", []),
                "clone_id": c.get("clone_id"),
            }
            for c in candidates
        ],
    }


@router.get("/searches/recent")
async def get_recent_searches(limit: int = 10):
    """최근 검색 이력."""
    if _is_demo_mode():
        return []
    searches = await db_select(
        "searches",
        columns="id, query_ko, brief, keywords_en, status, candidate_count, created_at",
        order_by="-created_at",
        limit=limit,
    )
    return searches


# ─── Demo Results ──────────────────────────────────────


def _generate_demo_results(search_id: str) -> dict:
    """데모용 mock 검색 결과 생성."""
    demo = _demo_results.get(search_id, {})

    return {
        "search_id": search_id,
        "brief_summary": demo.get("brief", {}),
        "candidates": [
            {
                "id": f"demo-1-{search_id[:8]}",
                "rank": 1,
                "category": "완성도최고",
                "repo_url": "https://github.com/antoinelame/GazeTracking",
                "repo_name": "antoinelame/GazeTracking",
                "total_score": 87,
                "score_detail": {
                    "feature_match": 22, "runnability": 18, "maintenance": 12,
                    "issue_resolution": 13, "install_ease": 9, "documentation": 8, "stack_compatibility": 4,
                },
                "confidence_label": "LLM 분석 기반 (실행 미검증)",
                "stars": 3400,
                "key_files": [
                    {"path": "gaze_tracking/gaze_tracking.py", "role": "메인 추적 로직", "importance": "core"},
                    {"path": "gaze_tracking/pupil.py", "role": "동공 감지", "importance": "core"},
                ],
                "pros": ["pip install 한 줄로 설치 가능", "직관적 API 제공"],
                "cons": ["안경 착용 시 동공 인식률 저하", "dlib C++ 빌드 필요"],
                "failure_scenarios": ["안경 착용 학생 과반 시 인식률 50% 이하"],
                "estimated_size_mb": 2.1,
                "estimated_clone_seconds": 5,
                "known_install_issues": ["dlib C++ 빌드 필요"],
                "stack_conflicts": [],
                "clone_id": None,
            },
            {
                "id": f"demo-2-{search_id[:8]}",
                "rank": 2,
                "category": "통합용이",
                "repo_url": "https://github.com/google/mediapipe",
                "repo_name": "google/mediapipe",
                "total_score": 82,
                "score_detail": {
                    "feature_match": 18, "runnability": 19, "maintenance": 14,
                    "issue_resolution": 11, "install_ease": 10, "documentation": 7, "stack_compatibility": 3,
                },
                "confidence_label": "LLM 분석 기반 (실행 미검증)",
                "stars": 27000,
                "key_files": [
                    {"path": "mediapipe/python/solutions/face_mesh.py", "role": "Face Mesh Python API", "importance": "core"},
                ],
                "pros": ["Google 공식, pip 설치 간단", "CPU 최적화 모델"],
                "cons": ["시선 추적 전용 아님", "대형 레포 ~180MB"],
                "failure_scenarios": ["시선 방향 추정 직접 구현 필요"],
                "estimated_size_mb": 180,
                "estimated_clone_seconds": 30,
                "known_install_issues": [],
                "stack_conflicts": ["대형 레포, 필요 모듈만 추출 권장"],
                "clone_id": None,
            },
            {
                "id": f"demo-3-{search_id[:8]}",
                "rank": 3,
                "category": "고정밀",
                "repo_url": "https://github.com/deepgaze/deepgaze",
                "repo_name": "deepgaze/deepgaze",
                "total_score": 68,
                "score_detail": {
                    "feature_match": 24, "runnability": 12, "maintenance": 8,
                    "issue_resolution": 9, "install_ease": 3, "documentation": 7, "stack_compatibility": 4,
                },
                "confidence_label": "LLM 분석 기반 (실행 미검증)",
                "stars": 850,
                "key_files": [
                    {"path": "deepgaze/head_pose_estimation.py", "role": "머리 자세 추정", "importance": "core"},
                ],
                "pros": ["딥러닝 기반 정확도 최고", "논문 기반"],
                "cons": ["GPU 권장", "업데이트 1년+ 전"],
                "failure_scenarios": ["GPU 없이 30fps 미달"],
                "estimated_size_mb": 450,
                "estimated_clone_seconds": 60,
                "known_install_issues": ["GPU 권장", "TF 버전 충돌"],
                "stack_conflicts": ["TensorFlow 버전 확인 필요"],
                "clone_id": None,
            },
        ],
    }
