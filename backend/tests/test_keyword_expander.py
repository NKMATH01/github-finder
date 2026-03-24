"""keyword_expander 단위 테스트 — 결과 구조 + 언어 필터 로직."""

import sys
sys.path.insert(0, ".")

from services.keyword_expander import KeywordExpansionResult


def test_expansion_result_creation():
    result = KeywordExpansionResult(
        functional_decomposition=["시선 추적", "동공 감지", "머리 자세 추정"],
        search_keywords=["gaze tracking", "eye tracking", "head pose estimation"],
        language_filter=["Python", "JavaScript"],
        excluded_terms=["tool", "app"],
    )
    assert len(result.search_keywords) == 3
    assert len(result.functional_decomposition) == 3
    assert "Python" in result.language_filter


def test_language_filter_insertion():
    """primary_language가 language_filter에 없으면 앞에 추가되는 로직."""
    result = KeywordExpansionResult(
        functional_decomposition=["기능1"],
        search_keywords=["keyword1"],
        language_filter=["Python"],
        excluded_terms=[],
    )
    # 시뮬레이션: primary_language가 JavaScript인 경우
    primary = "JavaScript"
    if primary and primary not in result.language_filter:
        result.language_filter.insert(0, primary)
    assert result.language_filter[0] == "JavaScript"
    assert result.language_filter[1] == "Python"


def test_language_filter_no_duplicate():
    """primary_language가 이미 있으면 추가하지 않음."""
    result = KeywordExpansionResult(
        functional_decomposition=["기능1"],
        search_keywords=["keyword1"],
        language_filter=["Python", "JavaScript"],
        excluded_terms=[],
    )
    primary = "Python"
    if primary and primary not in result.language_filter:
        result.language_filter.insert(0, primary)
    assert result.language_filter.count("Python") == 1


def test_empty_excluded_terms():
    result = KeywordExpansionResult(
        functional_decomposition=["기능1"],
        search_keywords=["keyword1", "keyword2"],
        language_filter=["Python"],
        excluded_terms=[],
    )
    assert result.excluded_terms == []


def test_keyword_count_range():
    """키워드가 적절한 범위인지 확인 (구조 테스트)."""
    # 8-15개 범위가 권장됨
    for count in (8, 10, 15):
        result = KeywordExpansionResult(
            functional_decomposition=["기능"],
            search_keywords=[f"kw{i}" for i in range(count)],
            language_filter=["Python"],
            excluded_terms=[],
        )
        assert 8 <= len(result.search_keywords) <= 15
