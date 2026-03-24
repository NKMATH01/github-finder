"""클론 + 구조 분석 API 라우터 — 실제 구현."""

import logging
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks

from config import settings
from models.schemas import CloneRequest, ClonePreviewResponse, CloneStatusResponse, StorageInfo
from models.error_models import AppException, ErrorCodes
from services.clone_previewer import get_clone_preview
from services.repo_cloner import clone_repo, delete_clone
from services.structure_analyzer import analyze_structure
from services.prompt_generator import generate_enhanced_prompt
from services.brief_parser import parse_brief, ParsedBrief
from services.db import db_insert, db_update, db_select, db_get_by_id

router = APIRouter()
logger = logging.getLogger(__name__)

# 인메모리 클론 진행 상태
_clone_progress: dict[str, dict] = {}


async def _run_clone_pipeline(
    clone_id: str,
    candidate_id: str,
    repo_url: str,
    repo_name: str,
    brief_data: dict | None,
    key_files: list[dict] | None,
    basic_prompt: dict | None,
):
    """백그라운드 클론 + 구조 분석 파이프라인."""
    try:
        owner, name = repo_name.split("/", 1) if "/" in repo_name else ("", repo_name)

        # Step 1: git clone
        _clone_progress[clone_id] = {
            "status": "cloning", "progress": 10,
            "clone_path": None, "file_count": None,
            "code_file_count": None, "total_size_mb": None,
            "file_tree": None, "structure_report": None,
            "integration_safe": [], "integration_risky": [],
            "integration_fail": [], "enhanced_prompt": None,
            "error_message": None,
        }

        clone_result = await clone_repo(repo_url, owner, name)

        await db_update("cloned_repos", clone_id, {
            "clone_path": clone_result["clone_path"],
            "file_count": clone_result["file_count"],
            "code_file_count": clone_result["code_file_count"],
            "total_size_mb": clone_result["total_size_mb"],
            "file_tree": clone_result["file_tree"],
            "status": "scanning",
        })

        _clone_progress[clone_id].update(
            status="scanning", progress=40,
            clone_path=clone_result["clone_path"],
            file_count=clone_result["file_count"],
            code_file_count=clone_result["code_file_count"],
            total_size_mb=clone_result["total_size_mb"],
            file_tree=clone_result["file_tree"],
        )

        # Step 2: 구조 분석 (GPT-4o Call Point 5)
        _clone_progress[clone_id].update(status="analyzing", progress=60)
        await db_update("cloned_repos", clone_id, {"status": "analyzing"})

        # 브리프 복원
        brief = None
        if brief_data:
            from models.schemas import BriefInput
            brief = parse_brief(BriefInput(**brief_data))

        if brief:
            report = await analyze_structure(
                clone_path=clone_result["clone_path"],
                repo_name=repo_name,
                brief=brief,
                key_files=key_files,
            )

            # 리포트를 마크다운으로 변환
            report_md = _report_to_markdown(report, repo_name)

            await db_update("cloned_repos", clone_id, {
                "structure_report": report_md,
                "integration_safe": report.get("safe_modules", []),
                "integration_risky": report.get("risky_modules", []),
                "integration_fail": report.get("fail_modules", []),
                "dependency_conflicts": report.get("dependency_conflicts", []),
            })

            _clone_progress[clone_id].update(
                progress=85,
                structure_report=report_md,
                integration_safe=report.get("safe_modules", []),
                integration_risky=report.get("risky_modules", []),
                integration_fail=report.get("fail_modules", []),
            )

            # Step 3: 강화 프롬프트 생성
            if basic_prompt:
                enhanced = generate_enhanced_prompt(
                    basic_prompt=basic_prompt,
                    clone_path=clone_result["clone_path"],
                    structure_report=report,
                )
                _clone_progress[clone_id]["enhanced_prompt"] = enhanced

                # prompts 테이블에 강화 프롬프트 저장
                existing_prompts = await db_select(
                    "prompts",
                    filters={"candidate_id": candidate_id},
                    limit=1,
                )
                if existing_prompts:
                    await db_update("prompts", existing_prompts[0]["id"], {
                        "enhanced_content": enhanced,
                        "clone_id": clone_id,
                    })

        # 완료
        await db_update("cloned_repos", clone_id, {"status": "completed"})

        # candidates 테이블에 clone_id 연결
        await db_update("candidates", candidate_id, {"clone_id": clone_id})

        _clone_progress[clone_id].update(status="completed", progress=100)
        logger.info("클론 파이프라인 완료: %s", clone_id)

    except AppException as e:
        _clone_progress[clone_id] = {
            **_clone_progress.get(clone_id, {}),
            "status": "failed", "progress": 100,
            "error_message": e.message,
        }
        await db_update("cloned_repos", clone_id, {
            "status": "failed", "error_message": e.message,
        })
        logger.error("클론 파이프라인 실패: %s — %s", clone_id, e.message)

    except Exception as e:
        _clone_progress[clone_id] = {
            **_clone_progress.get(clone_id, {}),
            "status": "failed", "progress": 100,
            "error_message": str(e),
        }
        await db_update("cloned_repos", clone_id, {
            "status": "failed", "error_message": str(e)[:500],
        })
        logger.exception("클론 파이프라인 예외: %s", clone_id)


def _report_to_markdown(report: dict, repo_name: str) -> str:
    """구조 분석 리포트를 마크다운으로 변환."""
    lines = [
        f"## 구조 분석 리포트: {repo_name}",
        f"⚠️ 이 리포트는 LLM 분석 기반이며, 실행 전에는 보장할 수 없습니다.",
        "",
        report.get("summary", ""),
        "",
    ]

    safe = report.get("safe_modules", [])
    if safe:
        lines.append("### ✅ 바로 통합 가능")
        for m in safe:
            lines.append(f"- `{m.get('file_path', '')}` → {m.get('action', '')} ({m.get('reason', '')})")
        lines.append("")

    risky = report.get("risky_modules", [])
    if risky:
        lines.append("### ⚠️ 의존성 충돌 위험")
        for m in risky:
            lines.append(f"- `{m.get('file_path', '')}`: {m.get('issue', '')} → 해결: {m.get('solution', '')}")
        lines.append("")

    fail = report.get("fail_modules", [])
    if fail:
        lines.append("### ❌ 환경 제약으로 실패 가능")
        for m in fail:
            lines.append(f"- `{m.get('file_path', '')}`: {m.get('issue', '')} → 대안: {m.get('alternative', '')}")

    return "\n".join(lines)


@router.get("/clone/preview/{candidate_id}", response_model=ClonePreviewResponse)
async def clone_preview(candidate_id: str):
    """클론 사전 정보 조회."""
    candidate = await db_get_by_id("candidates", candidate_id)
    if not candidate:
        raise AppException(
            code=ErrorCodes.SEARCH_NOT_FOUND,
            message="후보를 찾을 수 없습니다.",
            status_code=404,
        )

    preview = await get_clone_preview(
        repo_url=candidate["repo_url"],
        repo_name=candidate["repo_name"],
        known_install_issues=candidate.get("known_install_issues", []),
        stack_conflicts=candidate.get("stack_conflicts", []),
    )

    return ClonePreviewResponse(**preview)


@router.post("/clone")
async def start_clone(request: CloneRequest, background_tasks: BackgroundTasks):
    """클론 시작."""
    candidate = await db_get_by_id("candidates", request.candidate_id)
    if not candidate:
        raise AppException(
            code=ErrorCodes.SEARCH_NOT_FOUND,
            message="후보를 찾을 수 없습니다.",
            status_code=404,
        )

    clone_id = str(uuid.uuid4())

    # cloned_repos 레코드 생성
    await db_insert("cloned_repos", {
        "id": clone_id,
        "repo_url": candidate["repo_url"],
        "repo_name": candidate["repo_name"],
        "clone_path": "",
        "status": "cloning",
    })

    # 브리프 데이터 조회
    search = await db_get_by_id("searches", candidate["search_id"])
    brief_data = search.get("brief") if search else None

    # 기본 프롬프트 조회 (search 파이프라인에서 생성됨)
    prompts = await db_select(
        "prompts",
        filters={"candidate_id": request.candidate_id},
        limit=1,
    )
    basic_prompt = None
    if prompts:
        basic_prompt = {
            "full_prompt_text": prompts[0].get("content", ""),
            "alternative_plan": (prompts[0].get("alternative_prompts", []) or [{}])[0] if prompts[0].get("alternative_prompts") else {},
        }

    background_tasks.add_task(
        _run_clone_pipeline,
        clone_id=clone_id,
        candidate_id=request.candidate_id,
        repo_url=candidate["repo_url"],
        repo_name=candidate["repo_name"],
        brief_data=brief_data,
        key_files=candidate.get("key_files", []),
        basic_prompt=basic_prompt,
    )

    return {"clone_id": clone_id, "status": "cloning"}


@router.get("/clone/{clone_id}/status")
async def get_clone_status(clone_id: str):
    """클론 + 분석 진행 상태."""
    progress = _clone_progress.get(clone_id)
    if progress:
        return {"clone_id": clone_id, **progress}

    record = await db_get_by_id("cloned_repos", clone_id)
    if not record:
        raise AppException(
            code=ErrorCodes.SEARCH_NOT_FOUND,
            message="클론 정보를 찾을 수 없습니다.",
            status_code=404,
        )

    return {
        "clone_id": clone_id,
        "status": record.get("status", "unknown"),
        "progress": 100 if record.get("status") in ("completed", "failed") else 0,
        "clone_path": record.get("clone_path"),
        "file_count": record.get("file_count"),
        "code_file_count": record.get("code_file_count"),
        "total_size_mb": record.get("total_size_mb"),
        "file_tree": record.get("file_tree"),
        "structure_report": record.get("structure_report"),
        "integration_safe": record.get("integration_safe", []),
        "integration_risky": record.get("integration_risky", []),
        "integration_fail": record.get("integration_fail", []),
        "error_message": record.get("error_message"),
    }


@router.get("/clone/list")
async def list_clones():
    """클론된 레포 목록."""
    clones = await db_select(
        "cloned_repos",
        columns="id, repo_url, repo_name, clone_path, total_size_mb, status, created_at",
        order_by="-created_at",
        limit=50,
    )
    return clones


@router.get("/clone/storage-info")
async def storage_info():
    """클론 저장소 용량 정보."""
    clones = await db_select(
        "cloned_repos",
        columns="repo_name, total_size_mb, created_at",
        filters={"status": "completed"},
    )

    total = sum(c.get("total_size_mb", 0) or 0 for c in clones)
    return StorageInfo(
        total_size_mb=round(total, 1),
        repo_count=len(clones),
        repos=[
            {
                "name": c.get("repo_name", ""),
                "size_mb": c.get("total_size_mb", 0),
                "created_at": c.get("created_at", ""),
            }
            for c in clones
        ],
    )


@router.delete("/clone/{clone_id}")
async def delete_clone_endpoint(clone_id: str):
    """클론 삭제."""
    record = await db_get_by_id("cloned_repos", clone_id)
    if not record:
        raise AppException(
            code=ErrorCodes.SEARCH_NOT_FOUND,
            message="클론 정보를 찾을 수 없습니다.",
            status_code=404,
        )

    clone_path = record.get("clone_path", "")
    if clone_path:
        delete_clone(clone_path)

    await db_update("cloned_repos", clone_id, {
        "status": "deleted",
        "deleted_at": datetime.utcnow().isoformat(),
    })

    return {"message": "클론이 삭제되었습니다."}
