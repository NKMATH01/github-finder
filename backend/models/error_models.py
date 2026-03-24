"""표준 에러 응답 스키마 — 13종 에러 코드."""

from typing import Optional
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    detail: Optional[str] = None
    retry_after: Optional[int] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class AppException(Exception):
    """애플리케이션 전역 예외. FastAPI 에러 핸들러에서 ErrorResponse로 변환."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        detail: Optional[str] = None,
        retry_after: Optional[int] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail
        self.retry_after = retry_after
        super().__init__(message)


# 에러 코드 상수
class ErrorCodes:
    VALIDATION_ERROR = "VALIDATION_ERROR"          # 422
    GITHUB_RATE_LIMIT = "GITHUB_RATE_LIMIT"        # 429
    GITHUB_API_ERROR = "GITHUB_API_ERROR"          # 502
    LLM_TIMEOUT = "LLM_TIMEOUT"                    # 504
    LLM_API_ERROR = "LLM_API_ERROR"                # 502
    CLONE_FAILED = "CLONE_FAILED"                  # 500
    CLONE_TIMEOUT = "CLONE_TIMEOUT"                # 504
    CLONE_SIZE_EXCEEDED = "CLONE_SIZE_EXCEEDED"    # 413
    ANALYSIS_FAILED = "ANALYSIS_FAILED"            # 500
    SUPABASE_ERROR = "SUPABASE_ERROR"              # 503
    SEARCH_NOT_FOUND = "SEARCH_NOT_FOUND"          # 404
    NO_CANDIDATES = "NO_CANDIDATES"                # 404
    GIT_NOT_INSTALLED = "GIT_NOT_INSTALLED"         # 500
