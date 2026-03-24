"""통합 프롬프트 생성 — GPT-4o Call Point 4.

기본 프롬프트 + 강화 프롬프트(클론+리포트 반영)를 생성합니다.
"""

import logging

from services.llm_client import call_gpt4o_structured
from services.brief_parser import ParsedBrief
from services.deep_reader import DeepReadingResult
from models.llm_schemas import INTEGRATION_PROMPT_SCHEMA

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
당신은 바이브 코더가 Claude Code/Codex에 바로 붙여넣을 수 있는
통합 프롬프트를 생성하는 전문가입니다.

프롬프트 작성 규칙:
1. 한국어로 작성하세요
2. 브리프의 프로젝트 스택과 실행 환경에 맞는 구현 방식을 지시하세요
3. 의존성 설치 명령어를 포함하세요
4. 핵심 파일 경로와 역할을 명시하세요
5. 구현 단계를 3단계 이상으로 나누세요
6. "이게 잘 안 되면 시도할 대안"을 포함하세요
7. 알려진 한계/주의사항을 명시하세요
"""


async def generate_basic_prompt(
    candidate: DeepReadingResult,
    brief: ParsedBrief,
) -> dict:
    """기본 통합 프롬프트를 생성합니다 (클론 전)."""

    key_files_text = "\n".join(
        f"  - {kf.get('path', '')} — {kf.get('role', '')}"
        for kf in candidate.key_files[:5]
    )

    user_prompt = f"""\
다음 오픈소스 레포를 사용자의 프로젝트에 통합하는 프롬프트를 생성해주세요.

=== 브리프 ===
{brief.to_llm_context()}

=== 추천 레포 ===
레포: {candidate.repo_name} ({candidate.repo_url})
성격: 총점 {candidate.total_score}/100
핵심 파일:
{key_files_text}

장점: {'; '.join(candidate.pros[:3])}
단점: {'; '.join(candidate.cons[:3])}
설치: {candidate.install_command}

위 정보를 바탕으로 Claude Code에 바로 붙여넣을 수 있는 통합 프롬프트를 생성해주세요.
"""

    result = await call_gpt4o_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        json_schema=INTEGRATION_PROMPT_SCHEMA,
        schema_name="integration_prompt",
        temperature=0.4,
        max_tokens=4096,
    )

    logger.info("기본 프롬프트 생성 완료: %s", candidate.repo_name)
    return result


def generate_enhanced_prompt(
    basic_prompt: dict,
    clone_path: str,
    structure_report: dict,
) -> str:
    """강화 프롬프트를 생성합니다 (클론+리포트 반영).

    기본 프롬프트에 클론 경로와 구조 분석 결과를 추가합니다.
    """
    base_text = basic_prompt.get("full_prompt_text", "")

    # 구조 분석 요약 추가
    report_lines = [
        "",
        "### 구조 분석 리포트 요약 (참고용 — 실행 전 검증 필수)",
        f"로컬 클론 경로: {clone_path}",
        "",
    ]

    safe = structure_report.get("safe_modules", [])
    risky = structure_report.get("risky_modules", [])
    fail = structure_report.get("fail_modules", [])

    if safe:
        report_lines.append("✅ 바로 통합 가능:")
        for m in safe[:5]:
            report_lines.append(f"  - {m.get('file_path', '')} → {m.get('action', '')}")

    if risky:
        report_lines.append("\n⚠️ 주의 필요:")
        for m in risky[:5]:
            report_lines.append(
                f"  - {m.get('file_path', '')}: {m.get('issue', '')} → {m.get('solution', '')}"
            )

    if fail:
        report_lines.append("\n❌ 수정 필요:")
        for m in fail[:5]:
            report_lines.append(
                f"  - {m.get('file_path', '')}: {m.get('issue', '')} → 대안: {m.get('alternative', '')}"
            )

    report_lines.append("\n⚠️ 이 리포트는 LLM 분석 기반이며, 실제 실행 전에는 보장할 수 없습니다.")

    enhanced = base_text + "\n".join(report_lines)

    logger.info("강화 프롬프트 생성 완료 (len=%d)", len(enhanced))
    return enhanced
