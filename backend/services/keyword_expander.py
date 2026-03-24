"""검색어 확장 — GPT-4o Call Point 1.

한국어 브리프를 분석하여 기능 분해 + 영어 GitHub 검색 키워드를 생성합니다.
"""

import logging
from dataclasses import dataclass

from services.llm_client import call_gpt4o_structured
from services.brief_parser import ParsedBrief
from models.llm_schemas import KEYWORD_EXPANSION_SCHEMA

logger = logging.getLogger(__name__)


@dataclass
class KeywordExpansionResult:
    """키워드 확장 결과."""

    functional_decomposition: list[str]  # 기능 분해 (한국어)
    search_keywords: list[str]           # GitHub 검색 키워드 (영어)
    language_filter: list[str]           # 우선 검색 언어
    excluded_terms: list[str]            # 제외 키워드


SYSTEM_PROMPT = """\
당신은 GitHub 오픈소스 검색 전문가입니다.
사용자가 한국어로 작성한 브리프(기능 설명)를 분석하여:

1. 기능 분해: 브리프의 핵심 기능을 2-5개 하위 기능으로 분해 (한국어)
2. 검색 키워드: GitHub Search API에서 실제로 결과가 나오는 구체적 영어 기술 키워드 8-15개 생성
3. 언어 필터: 브리프의 프로젝트 스택에 맞는 프로그래밍 언어 우선순위
4. 제외 키워드: 너무 범용적이어서 노이즈가 되는 키워드 (tool, app, library 등)

키워드 작성 규칙:
- GitHub에서 실제로 검색되는 기술 용어만 사용
- 복합 키워드도 포함 (예: "gaze tracking", "face landmark detection")
- 유사/대체 기술도 포함 (예: 시선 추적 → gaze estimation, eye tracking, head pose)
- 너무 넓은 단어(tool, app, framework)는 excluded_terms에 넣기

반드시 functional_decomposition은 한국어로 작성하세요.
search_keywords는 영어로 작성하세요.
"""


async def expand_keywords(brief: ParsedBrief) -> KeywordExpansionResult:
    """브리프를 GPT-4o로 분석하여 검색 키워드를 확장합니다."""

    user_prompt = f"""\
다음 브리프를 분석하여 GitHub 검색 키워드를 생성해주세요.

{brief.to_llm_context()}
"""

    result = await call_gpt4o_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        json_schema=KEYWORD_EXPANSION_SCHEMA,
        schema_name="keyword_expansion",
        temperature=0.3,
    )

    expansion = KeywordExpansionResult(
        functional_decomposition=result["functional_decomposition"],
        search_keywords=result["search_keywords"],
        language_filter=result["language_filter"],
        excluded_terms=result["excluded_terms"],
    )

    # 브리프의 primary_language를 language_filter 앞에 추가
    if brief.primary_language and brief.primary_language not in expansion.language_filter:
        expansion.language_filter.insert(0, brief.primary_language)

    logger.info(
        "키워드 확장 완료: 기능분해=%d개, 키워드=%d개, 언어=%s",
        len(expansion.functional_decomposition),
        len(expansion.search_keywords),
        expansion.language_filter,
    )

    return expansion
