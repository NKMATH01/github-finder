"""구조 분석 리포트 — GPT-4o Call Point 5.

클론된 레포의 핵심 파일을 읽고, 브리프 기반으로
✅ 바로 통합 가능 / ⚠️ 위험 / ❌ 실패 가능 으로 3분류합니다.
"""

import logging
import os
from pathlib import Path

from services.llm_client import call_gpt4o_structured
from services.brief_parser import ParsedBrief
from services.repo_cloner import read_file_head, CODE_EXTENSIONS
from models.llm_schemas import STRUCTURE_ANALYSIS_SCHEMA

logger = logging.getLogger(__name__)

# 분석 대상 우선 파일
PRIORITY_FILES = [
    "README.md", "readme.md",
    "package.json", "requirements.txt", "pyproject.toml",
    "Pipfile", "go.mod", "Cargo.toml",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example", "setup.py", "setup.cfg",
]

SYSTEM_PROMPT = """\
당신은 오픈소스 레포의 코드 구조를 분석하여 통합 가능성을 평가하는 전문가입니다.

분석 규칙:
1. 실제 파일 경로와 코드 내용을 기반으로 분석하세요. 추측이 아닌 사실만 보고하세요.
2. 브리프의 프로젝트 스택과 비교하여 의존성 충돌을 구체적으로 분석하세요.
3. 각 모듈을 3가지로 분류하세요:
   - safe_modules: 별도 수정 없이 복사하면 되는 파일 (순수 코드, 외부 의존 없음)
   - risky_modules: 의존성 충돌 위험이 있지만 해결 가능한 파일 (해결 방법 제시)
   - fail_modules: 환경 제약으로 실패 가능한 부분 (대안 제시)
4. 의존성 충돌은 dependency_conflicts에 패키지별로 정리하세요.
5. 이 리포트는 LLM 분석 기반이므로, 실행 전 보장 불가임을 인지하세요.

중요: summary, action, reason, issue, solution, alternative, project_impact, resolution 등
모든 텍스트 필드는 반드시 한국어로 작성하세요.
"""


async def analyze_structure(
    clone_path: str,
    repo_name: str,
    brief: ParsedBrief,
    key_files: list[dict] | None = None,
) -> dict:
    """클론된 레포의 구조를 분석하고 3분류 리포트를 생성합니다.

    Returns:
        {summary, safe_modules, risky_modules, fail_modules, dependency_conflicts}
    """
    # 1. 핵심 파일 내용 수집
    file_contents = _collect_file_contents(clone_path, key_files)

    # 2. 파일 트리 요약
    tree_summary = _summarize_tree(clone_path)

    # 3. GPT-4o 구조 분석 (Call Point 5)
    brief_context = brief.to_llm_context()

    file_sections = []
    for fpath, content in file_contents.items():
        file_sections.append(f"### {fpath}\n```\n{content[:1500]}\n```")

    user_prompt = f"""\
다음 클론된 레포를 아래 브리프 기준으로 구조 분석해주세요.

=== 브리프 ===
{brief_context}

=== 레포: {repo_name} ===
=== 파일 트리 ===
{tree_summary}

=== 핵심 파일 내용 ===
{chr(10).join(file_sections)}

위 코드를 분석하여:
1. 바로 통합 가능한 모듈 (safe_modules)
2. 의존성 충돌 위험 모듈 (risky_modules)
3. 환경 제약으로 실패 가능한 부분 (fail_modules)
4. 구체적 의존성 충돌 목록 (dependency_conflicts)
을 분류해주세요.
"""

    result = await call_gpt4o_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        json_schema=STRUCTURE_ANALYSIS_SCHEMA,
        schema_name="structure_analysis_report",
        temperature=0.3,
        max_tokens=4096,
    )

    logger.info(
        "구조 분석 완료: %s (safe=%d, risky=%d, fail=%d)",
        repo_name,
        len(result.get("safe_modules", [])),
        len(result.get("risky_modules", [])),
        len(result.get("fail_modules", [])),
    )

    return result


def _collect_file_contents(
    clone_path: str, key_files: list[dict] | None = None
) -> dict[str, str]:
    """핵심 파일의 내용을 수집합니다 (상위 200줄)."""
    contents: dict[str, str] = {}

    # 우선 파일 (의존성, 설정)
    for pf in PRIORITY_FILES:
        fpath = os.path.join(clone_path, pf)
        if os.path.isfile(fpath):
            contents[pf] = read_file_head(fpath, max_lines=100)

    # 딥 리딩에서 특정한 핵심 파일
    if key_files:
        for kf in key_files:
            path = kf.get("path", "")
            if path and kf.get("importance") in ("core", "supporting"):
                fpath = os.path.join(clone_path, path)
                if os.path.isfile(fpath) and path not in contents:
                    contents[path] = read_file_head(fpath, max_lines=200)

    # 코드 파일 추가 (아직 5개 미만이면)
    if len(contents) < 5:
        for dirpath, _, filenames in os.walk(clone_path):
            rel_dir = os.path.relpath(dirpath, clone_path)
            if any(ex in rel_dir for ex in (".git", "node_modules", "__pycache__")):
                continue
            for fname in filenames:
                if len(contents) >= 8:
                    break
                if Path(fname).suffix in CODE_EXTENSIONS:
                    rel_path = os.path.join(rel_dir, fname).replace("\\", "/")
                    if rel_path.startswith("./"):
                        rel_path = rel_path[2:]
                    if rel_path not in contents:
                        fpath = os.path.join(dirpath, fname)
                        contents[rel_path] = read_file_head(fpath, max_lines=150)

    return contents


def _summarize_tree(clone_path: str, max_entries: int = 60) -> str:
    """파일 트리를 텍스트로 요약합니다."""
    lines = []
    root = Path(clone_path)

    for dirpath, dirnames, filenames in os.walk(clone_path):
        # 제외 디렉토리
        dirnames[:] = [
            d for d in dirnames
            if d not in (".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build")
            and not d.startswith(".")
        ]

        rel_dir = os.path.relpath(dirpath, clone_path)
        depth = rel_dir.count(os.sep) if rel_dir != "." else 0

        if depth > 2:
            continue

        indent = "  " * depth
        dir_name = os.path.basename(dirpath) if rel_dir != "." else ""
        if dir_name:
            lines.append(f"{indent}{dir_name}/")

        for fname in sorted(filenames):
            if len(lines) >= max_entries:
                lines.append(f"{indent}  ... (truncated)")
                return "\n".join(lines)
            lines.append(f"{indent}  {fname}")

    return "\n".join(lines)
