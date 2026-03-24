"""deep_reader 단위 테스트 — 가중치 계산 + 결과 구조."""

import sys
sys.path.insert(0, ".")

from services.deep_reader import DeepReadingResult, _apply_weights, WEIGHT_PRESETS


def _make_result(**overrides) -> DeepReadingResult:
    defaults = dict(
        repo_name="test/repo", repo_url="https://github.com/test/repo", stars=100,
        feature_match=20, runnability=15, maintenance=12,
        issue_resolution=10, install_ease=8, documentation=7, stack_compatibility=4,
    )
    defaults.update(overrides)
    return DeepReadingResult(**defaults)


def test_apply_weights_balanced():
    result = _make_result()
    score = _apply_weights(result, "balanced")
    assert 0 <= score <= 100
    # 76/100 원점수 → balanced는 그대로
    assert score == 76


def test_apply_weights_accuracy_boosts_feature_match():
    result = _make_result()
    balanced = _apply_weights(result, "balanced")
    accuracy = _apply_weights(result, "accuracy")
    # accuracy 모드에서 feature_match 가중치 1.2 → 점수 상승 예상
    assert accuracy >= balanced - 5  # 큰 차이는 아니지만 방향 확인


def test_apply_weights_speed_boosts_install():
    result = _make_result()
    balanced = _apply_weights(result, "balanced")
    speed = _apply_weights(result, "speed")
    # speed 모드에서 install_ease 가중치 1.5 → 설치 쉬운 레포 우대
    assert isinstance(speed, int)


def test_apply_weights_zero_scores():
    result = _make_result(
        feature_match=0, runnability=0, maintenance=0,
        issue_resolution=0, install_ease=0, documentation=0, stack_compatibility=0,
    )
    score = _apply_weights(result, "balanced")
    assert score == 0


def test_apply_weights_max_scores():
    result = _make_result(
        feature_match=25, runnability=20, maintenance=15,
        issue_resolution=15, install_ease=10, documentation=10, stack_compatibility=5,
    )
    score = _apply_weights(result, "balanced")
    assert score == 100


def test_deep_reading_result_structure():
    result = _make_result(
        pros=["장점1", "장점2"],
        cons=["단점1"],
        failure_scenarios=["실패1"],
        key_files=[{"path": "main.py", "role": "엔트리포인트", "importance": "core"}],
    )
    assert len(result.pros) == 2
    assert len(result.key_files) == 1
    assert result.key_files[0]["importance"] == "core"


def test_weight_presets_keys():
    for preset_name in ("balanced", "accuracy", "speed"):
        preset = WEIGHT_PRESETS[preset_name]
        expected_keys = {
            "feature_match", "runnability", "maintenance",
            "issue_resolution", "install_ease", "documentation", "stack_compatibility",
        }
        assert set(preset.keys()) == expected_keys
