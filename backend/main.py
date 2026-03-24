"""GitHub 기능 조달 워크벤치 — FastAPI 백엔드."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from models.error_models import AppException
from routers import search, clone, prompts, favorites, skills

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("GitHub 기능 조달 워크벤치 백엔드 시작")
    yield
    logger.info("백엔드 종료")


app = FastAPI(
    title="GitHub 기능 조달 워크벤치 API",
    description="바이브 코더를 위한 GitHub 오픈소스 검색·분석·통합 프롬프트 생성 API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://localhost:3030", "http://localhost:4000", "http://localhost:4002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 전역 에러 핸들러
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "detail": exc.detail,
                "retry_after": exc.retry_after,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("처리되지 않은 예외 발생")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "서버 내부 오류가 발생했습니다.",
                "detail": str(exc) if settings.GITHUB_TOKEN else None,
            }
        },
    )


# 라우터 등록
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(clone.router, prefix="/api", tags=["clone"])
app.include_router(prompts.router, prefix="/api", tags=["prompts"])
app.include_router(favorites.router, prefix="/api", tags=["favorites"])
app.include_router(skills.router, prefix="/api", tags=["skills"])


# 시스템 엔드포인트
@app.get("/api/system/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "llm_model": settings.LLM_MODEL,
        "github_configured": bool(settings.GITHUB_TOKEN),
        "supabase_configured": bool(settings.SUPABASE_URL),
    }


@app.get("/api/system/rate-limit")
async def rate_limit_info():
    """GitHub API rate limit 잔여 횟수 조회."""
    import httpx

    if not settings.GITHUB_TOKEN:
        return {"error": "GitHub 토큰이 설정되지 않았습니다."}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/rate_limit",
            headers={"Authorization": f"token {settings.GITHUB_TOKEN}"},
        )
        data = resp.json()
        core = data.get("resources", {}).get("core", {})
        search_limit = data.get("resources", {}).get("search", {})
        return {
            "core": {
                "limit": core.get("limit"),
                "remaining": core.get("remaining"),
                "reset_at": core.get("reset"),
            },
            "search": {
                "limit": search_limit.get("limit"),
                "remaining": search_limit.get("remaining"),
                "reset_at": search_limit.get("reset"),
            },
        }
