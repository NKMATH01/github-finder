"""GPT-4o Structured Output 통합 클라이언트.

모든 LLM 호출은 이 모듈을 통해 수행됩니다.
response_format=json_schema로 출력 형식을 보장합니다.
"""

import logging
import time
from typing import Any

from openai import AsyncOpenAI, APITimeoutError, RateLimitError, APIError

from config import settings
from models.error_models import AppException, ErrorCodes

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.LLM_TIMEOUT_SEC,
        )
    return _client


async def call_gpt4o_structured(
    system_prompt: str,
    user_prompt: str,
    json_schema: dict[str, Any],
    schema_name: str,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """GPT-4o Structured Output 호출.

    Args:
        system_prompt: 시스템 프롬프트
        user_prompt: 사용자 프롬프트
        json_schema: JSON Schema 정의
        schema_name: 스키마 이름 (API에 전달)
        temperature: 생성 온도 (기본 0.3)
        max_tokens: 최대 출력 토큰

    Returns:
        파싱된 dict (스키마 준수 보장)

    Raises:
        AppException: LLM 타임아웃 또는 API 오류
    """
    client = get_client()
    start_time = time.time()

    for attempt in range(settings.LLM_MAX_RETRIES):
        try:
            response = await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "strict": True,
                        "schema": json_schema,
                    },
                },
                temperature=temperature,
                max_tokens=max_tokens,
            )

            elapsed = time.time() - start_time
            content = response.choices[0].message.content

            # usage 로깅 (비용 추적용)
            usage = response.usage
            logger.info(
                "LLM 호출 완료: schema=%s, 소요=%.1fs, "
                "input_tokens=%d, output_tokens=%d",
                schema_name,
                elapsed,
                usage.prompt_tokens if usage else 0,
                usage.completion_tokens if usage else 0,
            )

            import json
            return json.loads(content)

        except APITimeoutError:
            logger.warning(
                "LLM 타임아웃 (시도 %d/%d): schema=%s",
                attempt + 1,
                settings.LLM_MAX_RETRIES,
                schema_name,
            )
            if attempt == settings.LLM_MAX_RETRIES - 1:
                raise AppException(
                    code=ErrorCodes.LLM_TIMEOUT,
                    message="AI 분석 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.",
                    status_code=504,
                    detail=f"GPT-4o timeout after {settings.LLM_TIMEOUT_SEC}s",
                    retry_after=10,
                )

        except RateLimitError as e:
            wait_time = 2 ** (attempt + 1)
            logger.warning(
                "LLM rate limit (시도 %d/%d): %ds 대기",
                attempt + 1,
                settings.LLM_MAX_RETRIES,
                wait_time,
            )
            if attempt == settings.LLM_MAX_RETRIES - 1:
                raise AppException(
                    code=ErrorCodes.LLM_API_ERROR,
                    message="AI 서비스 요청 한도를 초과했습니다.",
                    status_code=429,
                    detail=str(e),
                    retry_after=wait_time,
                )
            import asyncio
            await asyncio.sleep(wait_time)

        except APIError as e:
            logger.error("LLM API 오류: %s", e)
            raise AppException(
                code=ErrorCodes.LLM_API_ERROR,
                message="AI 서비스에 문제가 발생했습니다.",
                status_code=502,
                detail=str(e),
            )

    # 여기에 도달하면 안 됨
    raise AppException(
        code=ErrorCodes.LLM_API_ERROR,
        message="AI 분석에 실패했습니다.",
        status_code=500,
    )
