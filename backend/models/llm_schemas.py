"""GPT-4o Structured Output용 JSON Schema 정의 — 5개 Call Point.

주의: strict: true 모드에서는 모든 properties가 required에 포함되어야 합니다.
optional 필드가 필요하면 "type": ["string", "null"] 로 nullable 처리합니다.
모든 출력은 한국어로 생성됩니다.
"""


# Call Point 1: 키워드 확장
KEYWORD_EXPANSION_SCHEMA = {
    "type": "object",
    "properties": {
        "functional_decomposition": {
            "type": "array",
            "items": {"type": "string"},
            "description": "브리프에서 분해한 기능 단위 목록 (한국어)",
        },
        "search_keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "GitHub 검색용 영어 키워드 (8-15개)",
        },
        "language_filter": {
            "type": "array",
            "items": {"type": "string"},
            "description": "우선 검색할 프로그래밍 언어",
        },
        "excluded_terms": {
            "type": "array",
            "items": {"type": "string"},
            "description": "제외할 키워드 (너무 범용적인 것)",
        },
    },
    "required": [
        "functional_decomposition",
        "search_keywords",
        "language_filter",
        "excluded_terms",
    ],
    "additionalProperties": False,
}


# Call Point 2: 딥 리딩 + 7축 스코어링
DEEP_READING_SCHEMA = {
    "type": "object",
    "properties": {
        "feature_match_score": {"type": "integer", "description": "기능 일치도 (0-25)"},
        "feature_match_reason": {"type": "string"},
        "runnability_score": {"type": "integer", "description": "실행 가능성 (0-20)"},
        "runnability_evidence": {"type": "string"},
        "maintenance_score": {"type": "integer", "description": "유지보수 활성도 (0-15)"},
        "issue_resolution_score": {"type": "integer", "description": "이슈 해결률 (0-15)"},
        "install_ease_score": {"type": "integer", "description": "설치 난이도 (0-10)"},
        "documentation_score": {"type": "integer", "description": "문서/예제 품질 (0-10)"},
        "stack_compatibility_score": {"type": "integer", "description": "스택 호환성 (0-5)"},
        "stack_compatibility_detail": {"type": "string"},
        "key_files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "role": {"type": "string", "description": "한국어로 역할 설명"},
                    "importance": {"type": "string", "enum": ["core", "supporting", "example"]},
                },
                "required": ["path", "role", "importance"],
                "additionalProperties": False,
            },
        },
        "pros": {"type": "array", "items": {"type": "string"}, "description": "장점 3-5개 (한국어)"},
        "cons": {"type": "array", "items": {"type": "string"}, "description": "단점 3-5개 (한국어, 실패 시나리오 포함)"},
        "failure_scenarios": {"type": "array", "items": {"type": "string"}, "description": "구체적 실패 시나리오 2-3개 (한국어)"},
        "install_command": {"type": "string", "description": "설치 명령어"},
        "estimated_size_mb": {"type": "number", "description": "예상 레포 크기 (MB)"},
    },
    "required": [
        "feature_match_score", "feature_match_reason",
        "runnability_score", "runnability_evidence",
        "maintenance_score", "issue_resolution_score",
        "install_ease_score", "documentation_score",
        "stack_compatibility_score", "stack_compatibility_detail",
        "key_files", "pros", "cons", "failure_scenarios",
        "install_command", "estimated_size_mb",
    ],
    "additionalProperties": False,
}


# Call Point 3: 3종 분류
THREE_TYPE_CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "classification_type": {
            "type": "string",
            "enum": ["personality", "difficulty"],
            "description": "'personality'=완성도/통합용이/고정밀, 'difficulty'=난이도하/중/상",
        },
        "classification_reason": {"type": "string", "description": "한국어로 분류 이유"},
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "repo_name": {"type": "string"},
                    "assigned_category": {"type": "string"},
                    "category_reason": {"type": "string", "description": "한국어로 카테고리 이유"},
                    "rank": {"type": "integer"},
                },
                "required": ["repo_name", "assigned_category", "category_reason", "rank"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["classification_type", "classification_reason", "candidates"],
    "additionalProperties": False,
}


# Call Point 4: 통합 프롬프트 생성
INTEGRATION_PROMPT_SCHEMA = {
    "type": "object",
    "properties": {
        "prompt_title": {"type": "string"},
        "project_info_section": {"type": "string"},
        "goal_section": {"type": "string"},
        "reference_section": {"type": "string"},
        "implementation_steps": {
            "type": "array",
            "items": {"type": "string"},
            "description": "구현 단계 (한국어, 3개 이상)",
        },
        "install_commands": {"type": "array", "items": {"type": "string"}},
        "known_limitations": {"type": "array", "items": {"type": "string"}, "description": "한국어로 알려진 한계"},
        "alternative_plan": {
            "type": "object",
            "properties": {
                "condition": {"type": "string", "description": "한국어로 대안 조건"},
                "alternative_repo": {"type": "string"},
                "instruction": {"type": "string", "description": "한국어로 대안 지시"},
            },
            "required": ["condition", "alternative_repo", "instruction"],
            "additionalProperties": False,
        },
        "full_prompt_text": {"type": "string", "description": "최종 한국어 마크다운 프롬프트 전문"},
    },
    "required": [
        "prompt_title", "project_info_section", "goal_section",
        "reference_section", "implementation_steps", "install_commands",
        "known_limitations", "alternative_plan", "full_prompt_text",
    ],
    "additionalProperties": False,
}


# Call Point 5: 구조 분석 리포트
STRUCTURE_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "전체 요약 (한국어, 2-3문장)"},
        "safe_modules": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "target_path": {"type": "string", "description": "복사 대상 경로 (없으면 빈 문자열)"},
                    "action": {"type": "string", "description": "한국어로 조치 설명"},
                    "reason": {"type": "string", "description": "한국어로 이유"},
                },
                "required": ["file_path", "target_path", "action", "reason"],
                "additionalProperties": False,
            },
        },
        "risky_modules": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "package_name": {"type": "string", "description": "충돌 패키지명 (없으면 빈 문자열)"},
                    "issue": {"type": "string", "description": "한국어로 문제 설명"},
                    "solution": {"type": "string", "description": "한국어로 해결 방법"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                },
                "required": ["file_path", "package_name", "issue", "solution", "severity"],
                "additionalProperties": False,
            },
        },
        "fail_modules": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "issue": {"type": "string", "description": "한국어로 문제 설명"},
                    "environment_constraint": {"type": "string", "description": "환경 제약 (없으면 빈 문자열)"},
                    "alternative": {"type": "string", "description": "한국어로 대안"},
                },
                "required": ["file_path", "issue", "environment_constraint", "alternative"],
                "additionalProperties": False,
            },
        },
        "dependency_conflicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "package": {"type": "string"},
                    "repo_version": {"type": "string"},
                    "project_impact": {"type": "string", "description": "한국어로 영향 설명"},
                    "resolution": {"type": "string", "description": "한국어로 해결 방법"},
                },
                "required": ["package", "repo_version", "project_impact", "resolution"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "safe_modules", "risky_modules", "fail_modules", "dependency_conflicts"],
    "additionalProperties": False,
}
