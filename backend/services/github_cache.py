"""GitHub API 응답 캐시 레이어 — Supabase github_cache 테이블 + 인메모리 폴백.

검색 API 응답은 1시간, 레포 상세 조회는 24시간 TTL로 캐시합니다.
Supabase 미연결 시 인메모리 dict로 동작합니다.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from config import settings

logger = logging.getLogger(__name__)

# TTL 설정 (초)
TTL_SEARCH = 3600       # 검색: 1시간
TTL_REPO_DETAIL = 86400  # 레포 상세: 24시간

# 인메모리 폴백 캐시
_memory_cache: dict[str, dict[str, Any]] = {}

# Supabase 클라이언트 (lazy init)
_client = None
_supabase_available = False


def _init_supabase():
    global _client, _supabase_available
    if _client is not None:
        return
    try:
        if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
            from supabase import create_client
            _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
            _supabase_available = True
            logger.info("github_cache: Supabase connected")
        else:
            logger.info("github_cache: Supabase not configured — using memory cache")
    except Exception as e:
        logger.warning("github_cache: Supabase connection failed — using memory cache: %s", e)
        _supabase_available = False


def _make_cache_key(url: str, params: dict | None = None) -> str:
    """URL + 파라미터를 SHA-256 해시로 캐시 키 생성."""
    raw = url
    if params:
        raw += "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return hashlib.sha256(raw.encode()).hexdigest()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def cache_get(url: str, params: dict | None = None) -> dict | None:
    """캐시에서 응답 조회. 만료되었으면 None 반환."""
    _init_supabase()
    key = _make_cache_key(url, params)

    # Supabase 조회
    if _supabase_available and _client:
        try:
            result = (
                _client.table("github_cache")
                .select("response_data, expires_at")
                .eq("cache_key", key)
                .execute()
            )
            if result.data:
                row = result.data[0]
                expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
                if expires_at > _now_utc():
                    logger.debug("cache HIT (supabase): %s", key[:12])
                    return row["response_data"]
                else:
                    # 만료된 캐시 삭제
                    _client.table("github_cache").delete().eq("cache_key", key).execute()
        except Exception as e:
            logger.debug("cache_get supabase error: %s", e)

    # 인메모리 폴백
    if key in _memory_cache:
        entry = _memory_cache[key]
        if entry["expires_at"] > _now_utc():
            logger.debug("cache HIT (memory): %s", key[:12])
            return entry["response_data"]
        else:
            del _memory_cache[key]

    return None


async def cache_set(
    url: str,
    params: dict | None,
    response_data: Any,
    ttl_seconds: int = TTL_SEARCH,
) -> None:
    """응답을 캐시에 저장."""
    _init_supabase()
    key = _make_cache_key(url, params)
    expires_at = _now_utc() + timedelta(seconds=ttl_seconds)

    # 인메모리에 항상 저장
    _memory_cache[key] = {
        "response_data": response_data,
        "expires_at": expires_at,
    }

    # Supabase upsert
    if _supabase_available and _client:
        try:
            _client.table("github_cache").upsert({
                "cache_key": key,
                "response_data": json.loads(json.dumps(response_data, default=str)),
                "expires_at": expires_at.isoformat(),
            }).execute()
        except Exception as e:
            logger.debug("cache_set supabase error: %s", e)


async def cache_cleanup() -> int:
    """만료된 캐시 항목 정리. 삭제된 건수 반환."""
    now = _now_utc()
    removed = 0

    # 인메모리 정리
    expired_keys = [k for k, v in _memory_cache.items() if v["expires_at"] <= now]
    for k in expired_keys:
        del _memory_cache[k]
        removed += 1

    # Supabase 정리
    if _supabase_available and _client:
        try:
            _client.table("github_cache").delete().lt("expires_at", now.isoformat()).execute()
        except Exception as e:
            logger.debug("cache_cleanup supabase error: %s", e)

    if removed:
        logger.info("github_cache: cleaned up %d expired entries", removed)
    return removed
