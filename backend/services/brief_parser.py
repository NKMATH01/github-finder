"""브리프 파싱 + 필수/선택 검증."""

import logging
from dataclasses import dataclass, field

from models.schemas import BriefInput

logger = logging.getLogger(__name__)


@dataclass
class ParsedBrief:
    """파싱된 브리프 — 파이프라인 전체에서 사용되는 내부 객체."""

    goal_description: str
    project_stack: list[str]
    execution_environment: str
    priority: str = "balanced"
    reference_repo: str | None = None
    additional_conditions: str | None = None

    # 파싱 결과
    primary_language: str = ""
    stack_keywords: list[str] = field(default_factory=list)

    def to_llm_context(self) -> str:
        """LLM에 전달할 브리프 컨텍스트 문자열 생성."""
        stack_text = ', '.join(self.project_stack) if self.stack_keywords else "미정 (AI 추천 요청)"
        lines = [
            f"[목표 기능] {self.goal_description}",
            f"[프로젝트 스택] {stack_text}",
            f"[실행 환경] {self._env_label()}",
            f"[우선순위] {self._priority_label()}",
        ]
        if self.reference_repo:
            lines.append(f"[참고 레포] {self.reference_repo}")
        if self.additional_conditions:
            lines.append(f"[추가 조건] {self.additional_conditions}")
        return "\n".join(lines)

    def _env_label(self) -> str:
        labels = {
            "web_browser": "웹 브라우저 (프론트엔드 직접 실행)",
            "server": "서버 (백엔드에서 처리)",
            "local_app": "로컬 앱 (Electron 등)",
            "any": "상관없음",
        }
        return labels.get(self.execution_environment, self.execution_environment)

    def _priority_label(self) -> str:
        labels = {
            "accuracy": "정확도 우선",
            "speed": "속도 우선",
            "balanced": "균형",
        }
        return labels.get(self.priority, self.priority)


# 스택→언어 매핑
STACK_LANGUAGE_MAP: dict[str, str] = {
    "next.js": "JavaScript",
    "react": "JavaScript",
    "vue": "JavaScript",
    "angular": "JavaScript",
    "svelte": "JavaScript",
    "express": "JavaScript",
    "node": "JavaScript",
    "typescript": "TypeScript",
    "python": "Python",
    "fastapi": "Python",
    "django": "Python",
    "flask": "Python",
    "java": "Java",
    "spring": "Java",
    "go": "Go",
    "golang": "Go",
    "rust": "Rust",
    "c++": "C++",
    "c#": "C#",
    ".net": "C#",
    "ruby": "Ruby",
    "rails": "Ruby",
    "php": "PHP",
    "laravel": "PHP",
    "swift": "Swift",
    "kotlin": "Kotlin",
}


def parse_brief(input: BriefInput) -> ParsedBrief:
    """BriefInput을 ParsedBrief로 변환.

    - 프로젝트 스택에서 주 언어 추출
    - 스택 키워드 정리
    """
    # 주 언어 추출
    primary_language = ""
    stack_keywords: list[str] = []

    # "any" 또는 빈 스택이면 AI가 추천
    is_any_stack = (
        not input.project_stack
        or input.project_stack == ["any"]
        or (len(input.project_stack) == 1 and input.project_stack[0].lower() == "any")
    )

    if not is_any_stack:
        for stack_item in input.project_stack:
            normalized = stack_item.lower().strip()
            stack_keywords.append(normalized)

            if not primary_language and normalized in STACK_LANGUAGE_MAP:
                primary_language = STACK_LANGUAGE_MAP[normalized]

    logger.info(
        "브리프 파싱 완료: goal=%s, stack=%s, lang=%s, env=%s, priority=%s",
        input.goal_description[:50],
        input.project_stack,
        primary_language,
        input.execution_environment,
        input.priority,
    )

    return ParsedBrief(
        goal_description=input.goal_description,
        project_stack=input.project_stack,
        execution_environment=input.execution_environment,
        priority=input.priority or "balanced",
        reference_repo=input.reference_repo,
        additional_conditions=input.additional_conditions,
        primary_language=primary_language,
        stack_keywords=stack_keywords,
    )
