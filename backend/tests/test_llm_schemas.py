"""LLM JSON Schema 구조 검증 테스트."""

import sys
sys.path.insert(0, ".")

import json
from models.llm_schemas import (
    KEYWORD_EXPANSION_SCHEMA,
    DEEP_READING_SCHEMA,
    THREE_TYPE_CLASSIFICATION_SCHEMA,
    INTEGRATION_PROMPT_SCHEMA,
    STRUCTURE_ANALYSIS_SCHEMA,
)


def _validate_schema_structure(schema: dict):
    """기본 JSON Schema 구조 검증."""
    assert schema["type"] == "object"
    assert "properties" in schema
    assert "required" in schema
    assert schema.get("additionalProperties") is False
    # required 필드가 properties에 존재하는지 확인
    for field in schema["required"]:
        assert field in schema["properties"], f"required field '{field}' not in properties"


def test_keyword_expansion_schema():
    _validate_schema_structure(KEYWORD_EXPANSION_SCHEMA)
    props = KEYWORD_EXPANSION_SCHEMA["properties"]
    assert "search_keywords" in props
    assert "language_filter" in props
    assert props["search_keywords"]["type"] == "array"


def test_deep_reading_schema():
    _validate_schema_structure(DEEP_READING_SCHEMA)
    props = DEEP_READING_SCHEMA["properties"]
    # 7축 점수 필드 존재 확인
    score_fields = [
        "feature_match_score", "runnability_score", "maintenance_score",
        "issue_resolution_score", "install_ease_score",
        "documentation_score", "stack_compatibility_score",
    ]
    for field in score_fields:
        assert field in props, f"Missing score field: {field}"
        assert props[field]["type"] == "integer"
    # 장단점 필드
    assert "pros" in props
    assert "cons" in props
    assert "failure_scenarios" in props


def test_classification_schema():
    _validate_schema_structure(THREE_TYPE_CLASSIFICATION_SCHEMA)
    props = THREE_TYPE_CLASSIFICATION_SCHEMA["properties"]
    assert "classification_type" in props
    assert props["classification_type"]["enum"] == ["personality", "difficulty"]
    assert "candidates" in props


def test_integration_prompt_schema():
    _validate_schema_structure(INTEGRATION_PROMPT_SCHEMA)
    props = INTEGRATION_PROMPT_SCHEMA["properties"]
    assert "full_prompt_text" in props
    assert "implementation_steps" in props


def test_structure_analysis_schema():
    _validate_schema_structure(STRUCTURE_ANALYSIS_SCHEMA)
    props = STRUCTURE_ANALYSIS_SCHEMA["properties"]
    assert "safe_modules" in props
    assert "risky_modules" in props
    assert "fail_modules" in props
    # risky severity enum 확인
    risky_item = props["risky_modules"]["items"]["properties"]
    assert "severity" in risky_item
    assert risky_item["severity"]["enum"] == ["low", "medium", "high"]


def test_all_schemas_serializable():
    """모든 스키마가 JSON 직렬화 가능한지 확인."""
    schemas = [
        KEYWORD_EXPANSION_SCHEMA,
        DEEP_READING_SCHEMA,
        THREE_TYPE_CLASSIFICATION_SCHEMA,
        INTEGRATION_PROMPT_SCHEMA,
        STRUCTURE_ANALYSIS_SCHEMA,
    ]
    for schema in schemas:
        serialized = json.dumps(schema)
        deserialized = json.loads(serialized)
        assert deserialized == schema
