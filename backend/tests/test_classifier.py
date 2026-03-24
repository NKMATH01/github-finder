"""classifier 단위 테스트 — 카테고리 매핑 + 분류 로직."""

import sys
sys.path.insert(0, ".")

from services.classifier import CATEGORY_MAP, ClassifiedCandidate, ClassificationResult


def test_category_map_normalization():
    assert CATEGORY_MAP["완성도 최고"] == "완성도최고"
    assert CATEGORY_MAP["통합 용이"] == "통합용이"
    assert CATEGORY_MAP["고정밀"] == "고정밀"
    assert CATEGORY_MAP["난이도 하"] == "난이도하"
    assert CATEGORY_MAP["난이도 중"] == "난이도중"
    assert CATEGORY_MAP["난이도 상"] == "난이도상"


def test_category_map_already_normalized():
    assert CATEGORY_MAP["완성도최고"] == "완성도최고"
    assert CATEGORY_MAP["통합용이"] == "통합용이"


def test_classified_candidate_creation():
    c = ClassifiedCandidate(
        repo_name="owner/repo",
        category="완성도최고",
        category_reason="종합 점수 최고",
        rank=1,
    )
    assert c.rank == 1
    assert c.category == "완성도최고"


def test_classification_result_personality():
    result = ClassificationResult(
        classification_type="personality",
        classification_reason="서로 다른 가치 제공",
        candidates=[
            ClassifiedCandidate("a/repo1", "완성도최고", "이유1", 1),
            ClassifiedCandidate("b/repo2", "통합용이", "이유2", 2),
            ClassifiedCandidate("c/repo3", "고정밀", "이유3", 3),
        ],
    )
    assert len(result.candidates) == 3
    assert result.classification_type == "personality"
    categories = {c.category for c in result.candidates}
    assert categories == {"완성도최고", "통합용이", "고정밀"}


def test_classification_result_difficulty():
    result = ClassificationResult(
        classification_type="difficulty",
        classification_reason="비슷한 성격이라 난이도 분기",
        candidates=[
            ClassifiedCandidate("a/repo1", "난이도하", "이유1", 1),
            ClassifiedCandidate("b/repo2", "난이도중", "이유2", 2),
            ClassifiedCandidate("c/repo3", "난이도상", "이유3", 3),
        ],
    )
    assert result.classification_type == "difficulty"
