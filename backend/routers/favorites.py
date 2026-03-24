"""즐겨찾기 API 라우터 — 실제 구현."""

from fastapi import APIRouter

from models.schemas import FavoriteCreate
from models.error_models import AppException, ErrorCodes
from services.db import db_insert, db_select, db_delete

router = APIRouter()


@router.get("/favorites")
async def list_favorites():
    """즐겨찾기 목록."""
    favorites = await db_select(
        "favorites",
        order_by="-created_at",
        limit=100,
    )
    return favorites


@router.post("/favorites")
async def add_favorite(favorite: FavoriteCreate):
    """즐겨찾기 추가."""
    result = await db_insert("favorites", favorite.model_dump())
    return result


@router.delete("/favorites/{favorite_id}")
async def delete_favorite(favorite_id: str):
    """즐겨찾기 삭제."""
    await db_delete("favorites", favorite_id)
    return {"message": "즐겨찾기가 삭제되었습니다."}
