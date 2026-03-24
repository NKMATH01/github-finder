"""Supabase 클라이언트 — 실패해도 핵심 기능은 동작하도록 설계.

Supabase 연결 실패 시 인메모리 폴백으로 동작합니다.
"""

import logging
from typing import Any

from config import settings

logger = logging.getLogger(__name__)

_client = None
_supabase_available = False

# 인메모리 폴백 저장소
_memory_store: dict[str, dict[str, Any]] = {
    "searches": {},
    "candidates": {},
    "cloned_repos": {},
    "prompts": {},
    "favorites": {},
}


def _init_supabase():
    global _client, _supabase_available
    if _client is not None:
        return
    try:
        if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
            from supabase import create_client
            _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
            _supabase_available = True
            logger.info("Supabase connected")
        else:
            logger.warning("Supabase not configured — using memory store")
    except Exception as e:
        logger.warning("Supabase connection failed — using memory store: %s", e)
        _supabase_available = False


_init_supabase()


async def db_insert(table: str, data: dict[str, Any]) -> dict[str, Any]:
    """테이블에 데이터 삽입. Supabase 실패 시 인메모리에 저장."""
    # ID 보장
    if "id" not in data:
        import uuid
        data["id"] = str(uuid.uuid4())

    # 인메모리에 항상 저장
    _memory_store.setdefault(table, {})[data["id"]] = data

    # Supabase에도 시도 (실패해도 무시)
    if _supabase_available and _client:
        try:
            result = _client.table(table).insert(data).execute()
            if result.data:
                return result.data[0]
        except Exception as e:
            logger.warning("Supabase insert failed (using memory): %s — %s", table, str(e)[:100])

    return data


async def db_select(
    table: str,
    columns: str = "*",
    filters: dict[str, Any] | None = None,
    order_by: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """테이블에서 데이터 조회."""
    # Supabase 시도
    if _supabase_available and _client:
        try:
            query = _client.table(table).select(columns)
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            if order_by:
                desc = order_by.startswith("-")
                col = order_by.lstrip("-")
                query = query.order(col, desc=desc)
            if limit:
                query = query.limit(limit)
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.warning("Supabase select failed (using memory): %s — %s", table, str(e)[:100])

    # 인메모리 폴백
    rows = list(_memory_store.get(table, {}).values())
    if filters:
        rows = [r for r in rows if all(r.get(k) == v for k, v in filters.items())]
    if order_by:
        desc = order_by.startswith("-")
        col = order_by.lstrip("-")
        rows.sort(key=lambda r: r.get(col, ""), reverse=desc)
    if limit:
        rows = rows[:limit]
    return rows


async def db_update(table: str, row_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """ID 기반 데이터 업데이트."""
    # 인메모리 업데이트
    if table in _memory_store and row_id in _memory_store[table]:
        _memory_store[table][row_id].update(data)

    # Supabase 시도
    if _supabase_available and _client:
        try:
            result = _client.table(table).update(data).eq("id", row_id).execute()
            if result.data:
                return result.data[0]
        except Exception as e:
            logger.warning("Supabase update failed (using memory): %s — %s", table, str(e)[:100])

    return _memory_store.get(table, {}).get(row_id, data)


async def db_delete(table: str, row_id: str) -> None:
    """ID 기반 데이터 삭제."""
    # 인메모리 삭제
    if table in _memory_store and row_id in _memory_store[table]:
        del _memory_store[table][row_id]

    # Supabase 시도
    if _supabase_available and _client:
        try:
            _client.table(table).delete().eq("id", row_id).execute()
        except Exception as e:
            logger.warning("Supabase delete failed: %s — %s", table, str(e)[:100])


async def db_get_by_id(table: str, row_id: str) -> dict[str, Any] | None:
    """ID로 단일 레코드 조회."""
    # 인메모리 먼저
    mem = _memory_store.get(table, {}).get(row_id)
    if mem:
        return mem

    # Supabase 시도
    if _supabase_available and _client:
        try:
            result = _client.table(table).select("*").eq("id", row_id).execute()
            if result.data:
                # 인메모리에도 캐시
                _memory_store.setdefault(table, {})[row_id] = result.data[0]
                return result.data[0]
        except Exception as e:
            logger.warning("Supabase get_by_id failed: %s — %s", table, str(e)[:100])

    return None
