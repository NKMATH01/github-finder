"""스킬 다운로드 + 설치 준비 — 실제 파일 복사는 하지 않음.

보안:
- 허용 확장자 화이트리스트
- 단일 파일 1MB / 전체 10MB 제한
- path traversal 방지
- 심볼릭 링크 차단
"""

import logging
import os
import re
from pathlib import Path

import httpx

from config import settings
from models.error_models import AppException, ErrorCodes
from models.skill_models import SkillPackage

logger = logging.getLogger(__name__)

# 스킬 파일 허용 확장자
ALLOWED_EXTENSIONS = {
    ".md", ".py", ".js", ".ts", ".sh", ".json", ".yml", ".yaml", ".toml",
    ".txt", ".cfg", ".ini", ".bash", ".zsh",
}

ALLOWED_FILENAMES = {"SKILL.md", "Makefile", "LICENSE"}

MAX_SINGLE_FILE_KB = 1024   # 1MB
MAX_TOTAL_KB = 10240         # 10MB


def _is_allowed_skill_file(filename: str) -> bool:
    """화이트리스트 기반 스킬 파일 허용 판단."""
    if filename in ALLOWED_FILENAMES:
        return True
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def _is_safe_path(path: str) -> bool:
    """path traversal 방지."""
    normalized = os.path.normpath(path)
    return not normalized.startswith("..") and not os.path.isabs(normalized)


async def download_skill(
    github_url: str,
    skill_path: str,
) -> SkillPackage:
    """GitHub API로 스킬 디렉토리의 파일 목록을 조회하고 다운로드합니다.

    실제 파일 시스템에 쓰지 않고, 메모리에서 파일 목록과 미리보기를 구성합니다.
    """
    # GitHub URL 파싱
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)", github_url)
    if not match:
        raise AppException(
            code=ErrorCodes.VALIDATION_ERROR,
            message="유효하지 않은 GitHub URL입니다.",
            status_code=400,
        )
    owner, repo = match.group(1), match.group(2)

    api_base = settings.GITHUB_API_BASE
    headers = {"Accept": "application/vnd.github.v3+json"}
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

    # 스킬 디렉토리 파일 목록 조회
    contents_path = skill_path if skill_path else ""
    url = f"{api_base}/repos/{owner}/{repo}/contents/{contents_path}"

    files_info: list[dict] = []
    total_size_kb = 0
    skill_md_preview = ""

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            raise AppException(
                code=ErrorCodes.CLONE_FAILED,
                message=f"스킬 디렉토리를 조회할 수 없습니다 (HTTP {resp.status_code})",
                status_code=502,
            )

        items = resp.json()
        if not isinstance(items, list):
            items = [items]

        for item in items:
            name = item.get("name", "")
            item_type = item.get("type", "")
            size_bytes = item.get("size", 0)
            size_kb = size_bytes / 1024

            # 파일만 처리 (디렉토리 재귀 탐색 안 함)
            if item_type != "file":
                continue

            # 보안 검증
            if not _is_safe_path(name):
                logger.warning("path traversal 차단: %s", name)
                continue
            if not _is_allowed_skill_file(name):
                continue
            if size_kb > MAX_SINGLE_FILE_KB:
                logger.warning("파일 크기 초과 (스킵): %s (%.0fKB)", name, size_kb)
                continue
            if total_size_kb + size_kb > MAX_TOTAL_KB:
                logger.warning("전체 크기 한도 초과, 나머지 파일 스킵")
                break

            # 파일 내용 미리보기 (SKILL.md만 전문, 나머지는 이름만)
            content_preview = ""
            if name == "SKILL.md":
                download_url = item.get("download_url", "")
                if download_url:
                    try:
                        dl_resp = await client.get(download_url, headers=headers)
                        if dl_resp.status_code == 200:
                            content_preview = dl_resp.text
                            skill_md_preview = content_preview[:2000]
                    except Exception as e:
                        logger.debug("SKILL.md 다운로드 실패: %s", e)

            files_info.append({
                "name": name,
                "size_kb": round(size_kb, 1),
                "content_preview": content_preview[:500] if content_preview else "",
            })
            total_size_kb += size_kb

    skill_name = skill_path.split("/")[-1] if skill_path else repo

    return SkillPackage(
        skill_name=skill_name,
        files=files_info,
        total_size_kb=round(total_size_kb),
        install_path_project=f".claude/skills/{skill_name}/",
        install_path_personal=f"~/.claude/skills/{skill_name}/",
        install_command=f"# 프로젝트에 설치\nmkdir -p .claude/skills/{skill_name}\n# GitHub에서 SKILL.md를 다운로드하여 위 경로에 저장하세요\n# 또는: curl -o .claude/skills/{skill_name}/SKILL.md {github_url.replace('github.com', 'raw.githubusercontent.com')}/main/{skill_path}/SKILL.md" if skill_path else "",
        skill_md_preview=skill_md_preview,
    )


def prepare_install_command(
    skill_name: str,
    github_url: str,
    skill_path: str,
    target: str = "project",
) -> dict:
    """설치 경로와 명령어를 생성합니다. 실제 복사는 하지 않습니다."""
    if target == "personal":
        install_dir = f"~/.claude/skills/{skill_name}"
    else:
        install_dir = f".claude/skills/{skill_name}"

    match = re.match(r"https://github\.com/([^/]+)/([^/]+)", github_url)
    owner_repo = f"{match.group(1)}/{match.group(2)}" if match else ""
    path_prefix = f"{skill_path}/" if skill_path else ""

    return {
        "install_path": install_dir,
        "commands": [
            f"mkdir -p {install_dir}",
            f"curl -sL https://raw.githubusercontent.com/{owner_repo}/main/{path_prefix}SKILL.md -o {install_dir}/SKILL.md",
        ],
        "note": "Claude Code가 자동으로 해당 디렉토리의 스킬을 인식합니다.",
    }
