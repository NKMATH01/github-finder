"""brief_parser 단위 테스트."""

import sys
sys.path.insert(0, ".")

from models.schemas import BriefInput
from services.brief_parser import parse_brief


def test_parse_basic_brief():
    brief = BriefInput(
        goal_description="시선 추적 기능",
        project_stack=["Next.js", "FastAPI"],
        execution_environment="server",
    )
    result = parse_brief(brief)
    assert result.goal_description == "시선 추적 기능"
    assert result.primary_language == "JavaScript"
    assert result.priority == "balanced"


def test_parse_python_stack():
    brief = BriefInput(
        goal_description="OCR 기능",
        project_stack=["Python", "Django"],
        execution_environment="server",
    )
    result = parse_brief(brief)
    assert result.primary_language == "Python"


def test_parse_priority():
    brief = BriefInput(
        goal_description="음성 인식",
        project_stack=["React"],
        execution_environment="web_browser",
        priority="accuracy",
    )
    result = parse_brief(brief)
    assert result.priority == "accuracy"


def test_llm_context_contains_stack():
    brief = BriefInput(
        goal_description="PDF 생성",
        project_stack=["FastAPI", "PostgreSQL"],
        execution_environment="server",
        additional_conditions="GPU 없이 실행",
    )
    result = parse_brief(brief)
    ctx = result.to_llm_context()
    assert "FastAPI" in ctx
    assert "PostgreSQL" in ctx
    assert "GPU 없이 실행" in ctx
    assert "서버" in ctx


def test_parse_with_reference_repo():
    brief = BriefInput(
        goal_description="시선 추적",
        project_stack=["Python"],
        execution_environment="server",
        reference_repo="https://github.com/antoinelame/GazeTracking",
    )
    result = parse_brief(brief)
    ctx = result.to_llm_context()
    assert "GazeTracking" in ctx


def test_stack_keywords():
    brief = BriefInput(
        goal_description="테스트",
        project_stack=["Next.js", "FastAPI", "PostgreSQL"],
        execution_environment="any",
    )
    result = parse_brief(brief)
    assert "next.js" in result.stack_keywords
    assert "fastapi" in result.stack_keywords
    assert len(result.stack_keywords) == 3


def test_unknown_stack_no_language():
    brief = BriefInput(
        goal_description="테스트",
        project_stack=["CustomFramework"],
        execution_environment="any",
    )
    result = parse_brief(brief)
    assert result.primary_language == ""
