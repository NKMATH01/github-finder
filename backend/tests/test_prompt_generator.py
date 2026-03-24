"""prompt_generator 단위 테스트 — 강화 프롬프트 생성 로직."""

import sys
sys.path.insert(0, ".")

from services.prompt_generator import generate_enhanced_prompt


def test_enhanced_prompt_with_safe_modules():
    basic = {"full_prompt_text": "## 통합 요청\n기본 프롬프트 내용"}
    report = {
        "safe_modules": [
            {"file_path": "src/main.py", "action": "복사", "reason": "순수 Python"},
        ],
        "risky_modules": [],
        "fail_modules": [],
    }
    enhanced = generate_enhanced_prompt(basic, "./cloned_repos/test", report)
    assert "통합 요청" in enhanced
    assert "src/main.py" in enhanced
    assert "바로 통합 가능" in enhanced
    assert "cloned_repos/test" in enhanced


def test_enhanced_prompt_with_risky_modules():
    basic = {"full_prompt_text": "기본 프롬프트"}
    report = {
        "safe_modules": [],
        "risky_modules": [
            {"file_path": "req.txt", "issue": "버전 충돌", "solution": "pip install --upgrade"},
        ],
        "fail_modules": [],
    }
    enhanced = generate_enhanced_prompt(basic, "./cloned", report)
    assert "주의 필요" in enhanced
    assert "버전 충돌" in enhanced


def test_enhanced_prompt_with_fail_modules():
    basic = {"full_prompt_text": "기본 프롬프트"}
    report = {
        "safe_modules": [],
        "risky_modules": [],
        "fail_modules": [
            {"file_path": "gpu.py", "issue": "GPU 필요", "alternative": "CPU 버전 사용"},
        ],
    }
    enhanced = generate_enhanced_prompt(basic, "./cloned", report)
    assert "수정 필요" in enhanced
    assert "GPU 필요" in enhanced
    assert "CPU 버전" in enhanced


def test_enhanced_prompt_disclaimer():
    basic = {"full_prompt_text": "프롬프트"}
    report = {"safe_modules": [], "risky_modules": [], "fail_modules": []}
    enhanced = generate_enhanced_prompt(basic, "./cloned", report)
    assert "LLM 분석 기반" in enhanced
    assert "보장할 수 없습니다" in enhanced


def test_enhanced_prompt_empty_basic():
    basic = {"full_prompt_text": ""}
    report = {"safe_modules": [], "risky_modules": [], "fail_modules": []}
    enhanced = generate_enhanced_prompt(basic, "./cloned", report)
    assert isinstance(enhanced, str)


def test_enhanced_prompt_preserves_basic():
    """강화 프롬프트가 기본 프롬프트를 유지하는지 확인."""
    basic_text = "## 원본 프롬프트\n이 내용은 유지되어야 합니다."
    basic = {"full_prompt_text": basic_text}
    report = {"safe_modules": [], "risky_modules": [], "fail_modules": []}
    enhanced = generate_enhanced_prompt(basic, "./cloned", report)
    assert basic_text in enhanced
