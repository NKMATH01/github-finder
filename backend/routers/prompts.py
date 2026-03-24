"""프롬프트 API 라우터 — 실제 구현."""

from fastapi import APIRouter

from models.error_models import AppException, ErrorCodes
from services.db import db_get_by_id, db_update

router = APIRouter()


@router.get("/prompts/{prompt_id}")
async def get_prompt(prompt_id: str):
    """기본 프롬프트 조회."""
    prompt = await db_get_by_id("prompts", prompt_id)
    if not prompt:
        raise AppException(
            code=ErrorCodes.SEARCH_NOT_FOUND,
            message="프롬프트를 찾을 수 없습니다.",
            status_code=404,
        )
    return prompt


@router.get("/prompts/{prompt_id}/enhanced")
async def get_enhanced_prompt(prompt_id: str):
    """강화 프롬프트 조회 (클론+리포트 반영)."""
    prompt = await db_get_by_id("prompts", prompt_id)
    if not prompt:
        raise AppException(
            code=ErrorCodes.SEARCH_NOT_FOUND,
            message="프롬프트를 찾을 수 없습니다.",
            status_code=404,
        )

    enhanced = prompt.get("enhanced_content")
    if not enhanced:
        return {
            "id": prompt_id,
            "content": prompt.get("content", ""),
            "message": "강화 프롬프트가 아직 생성되지 않았습니다. 레포를 클론한 후 생성됩니다.",
        }

    return {
        "id": prompt_id,
        "content": enhanced,
        "is_enhanced": True,
    }


@router.post("/prompts/{prompt_id}/copy")
async def increment_copy_count(prompt_id: str):
    """복사 카운트 증가."""
    prompt = await db_get_by_id("prompts", prompt_id)
    if not prompt:
        raise AppException(
            code=ErrorCodes.SEARCH_NOT_FOUND,
            message="프롬프트를 찾을 수 없습니다.",
            status_code=404,
        )

    new_count = (prompt.get("copy_count", 0) or 0) + 1
    await db_update("prompts", prompt_id, {"copy_count": new_count})

    return {"copy_count": new_count}
