"""Pydantic 스키마 검증 테스트."""

import sys
sys.path.insert(0, ".")

import pytest
from pydantic import ValidationError
from models.schemas import BriefInput, FavoriteCreate, ScoreDetail


def test_brief_valid():
    brief = BriefInput(
        goal_description="시선 추적",
        project_stack=["Python"],
        execution_environment="server",
    )
    assert brief.priority == "balanced"
    assert brief.reference_repo is None


def test_brief_missing_required():
    with pytest.raises(ValidationError):
        BriefInput(
            goal_description="test",
            project_stack=[],  # min_length=1 위반
            execution_environment="server",
        )


def test_brief_invalid_environment():
    with pytest.raises(ValidationError):
        BriefInput(
            goal_description="test",
            project_stack=["Python"],
            execution_environment="cloud",  # 유효하지 않은 값
        )


def test_brief_invalid_priority():
    with pytest.raises(ValidationError):
        BriefInput(
            goal_description="test",
            project_stack=["Python"],
            execution_environment="server",
            priority="fast",  # 유효하지 않은 값
        )


def test_brief_valid_reference_repo():
    brief = BriefInput(
        goal_description="test",
        project_stack=["Python"],
        execution_environment="server",
        reference_repo="https://github.com/owner/repo",
    )
    assert brief.reference_repo == "https://github.com/owner/repo"


def test_brief_invalid_reference_repo():
    with pytest.raises(ValidationError):
        BriefInput(
            goal_description="test",
            project_stack=["Python"],
            execution_environment="server",
            reference_repo="not-a-github-url",
        )


def test_favorite_create():
    fav = FavoriteCreate(
        repo_url="https://github.com/owner/repo",
        repo_name="owner/repo",
    )
    assert fav.category is None
    assert fav.note is None


def test_score_detail_defaults():
    score = ScoreDetail()
    assert score.feature_match == 0
    assert score.stack_compatibility == 0
