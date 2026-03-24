"""핵심 파일 특정 — 딥 리딩 결과의 key_files를 정제합니다."""

import logging

from services.deep_reader import DeepReadingResult

logger = logging.getLogger(__name__)


def identify_key_files(result: DeepReadingResult) -> list[dict]:
    """딥 리딩 결과에서 핵심 파일 목록을 정제합니다.

    - core 파일을 먼저, supporting, example 순으로 정렬
    - 최대 10개까지만 반환
    """
    importance_order = {"core": 0, "supporting": 1, "example": 2}

    sorted_files = sorted(
        result.key_files,
        key=lambda f: importance_order.get(f.get("importance", "example"), 3),
    )

    return sorted_files[:10]
