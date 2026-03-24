"""error_models 단위 테스트."""

import sys
sys.path.insert(0, ".")

from models.error_models import AppException, ErrorCodes, ErrorResponse, ErrorDetail


def test_app_exception_creation():
    exc = AppException(
        code=ErrorCodes.GITHUB_RATE_LIMIT,
        message="API 한도 초과",
        status_code=429,
        retry_after=60,
    )
    assert exc.code == "GITHUB_RATE_LIMIT"
    assert exc.status_code == 429
    assert exc.retry_after == 60
    assert str(exc) == "API 한도 초과"


def test_error_response_model():
    resp = ErrorResponse(
        error=ErrorDetail(
            code="LLM_TIMEOUT",
            message="타임아웃",
            detail="60초 초과",
            retry_after=10,
        )
    )
    data = resp.model_dump()
    assert data["error"]["code"] == "LLM_TIMEOUT"
    assert data["error"]["retry_after"] == 10


def test_all_error_codes_exist():
    codes = [attr for attr in dir(ErrorCodes) if not attr.startswith("_")]
    assert len(codes) == 13
    assert "VALIDATION_ERROR" in codes
    assert "GITHUB_RATE_LIMIT" in codes
    assert "LLM_TIMEOUT" in codes
    assert "CLONE_FAILED" in codes
    assert "NO_CANDIDATES" in codes


def test_app_exception_default_status():
    exc = AppException(code="TEST", message="test")
    assert exc.status_code == 500
    assert exc.detail is None
    assert exc.retry_after is None
