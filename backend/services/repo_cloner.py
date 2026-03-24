"""레포 다운로드 — GitHub tarball API + 보안 검증.

보안 강화:
- git clone 대신 GitHub tarball API 사용 (.git/hooks, 서브모듈 위험 제거)
- 심볼릭 링크 자동 제거
- 허용 확장자 화이트리스트
- 파일 크기 제한 (500MB)
"""

import io
import logging
import os
import re
import shutil
import tarfile
from datetime import datetime
from pathlib import Path

import httpx

from config import settings
from models.error_models import AppException, ErrorCodes

logger = logging.getLogger(__name__)

# GitHub URL 화이트리스트 패턴
GITHUB_URL_PATTERN = re.compile(
    r"^https://github\.com/[a-zA-Z0-9_.\-]+/[a-zA-Z0-9_.\-]+(?:\.git)?$"
)

# 파일 트리 스캔 시 제외 목록
EXCLUDED_DIRS = {
    "node_modules", "__pycache__", ".git", "venv", ".venv",
    "dist", "build", ".next", ".cache", ".tox", "eggs",
    "*.egg-info", ".mypy_cache", ".pytest_cache",
}

# 허용 확장자 화이트리스트 (코드 + 설정 파일)
ALLOWED_EXTENSIONS = {
    # 코드
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs",
    ".rb", ".php", ".c", ".cpp", ".h", ".hpp", ".cs", ".swift", ".kt",
    ".vue", ".svelte", ".html", ".css", ".scss", ".less", ".sass",
    ".sh", ".bash", ".zsh", ".fish", ".bat", ".ps1",
    ".sql", ".graphql", ".gql", ".proto",
    ".r", ".R", ".jl", ".lua", ".ex", ".exs", ".erl", ".hrl",
    ".dart", ".scala", ".clj", ".hs", ".elm", ".ml", ".mli",
    # 설정 / 메타
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".xml", ".env.example", ".editorconfig", ".gitignore", ".gitattributes",
    ".dockerignore", ".eslintrc", ".prettierrc", ".babelrc",
    ".lock",  # package-lock.json, yarn.lock 등
    # 문서
    ".md", ".txt", ".rst", ".adoc",
    # 데이터
    ".csv", ".tsv",
    # 기타
    "", # Makefile, Dockerfile 등 확장자 없는 파일
}

# 확장자 없이 이름으로 허용하는 파일
ALLOWED_FILENAMES = {
    "Makefile", "Dockerfile", "Procfile", "Gemfile", "Rakefile",
    "LICENSE", "LICENCE", "COPYING", "NOTICE",
    "Vagrantfile", "Brewfile", "Taskfile",
    ".env.example", ".env.sample",
}

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs",
    ".rb", ".php", ".c", ".cpp", ".h", ".cs", ".swift", ".kt",
    ".vue", ".svelte", ".html", ".css", ".scss",
}


def validate_clone_url(url: str) -> str:
    """GitHub URL만 허용. 인젝션 차단."""
    if not GITHUB_URL_PATTERN.match(url):
        raise AppException(
            code=ErrorCodes.CLONE_FAILED,
            message="유효하지 않은 GitHub URL입니다. https://github.com/owner/repo 형식만 허용됩니다.",
            status_code=400,
        )
    return url


async def clone_repo(repo_url: str, owner: str, repo_name: str) -> dict:
    """GitHub tarball API로 레포를 다운로드 + 보안 검증 + 파일 트리 스캔.

    Returns:
        {clone_path, file_count, code_file_count, total_size_mb, file_tree}
    """
    validate_clone_url(repo_url)

    # 클론 경로 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clone_dir_name = f"{owner}_{repo_name}_{timestamp}"
    clone_path = os.path.join(settings.CLONE_BASE_PATH, clone_dir_name)

    # 이미 존재하면 삭제
    if os.path.exists(clone_path):
        shutil.rmtree(clone_path)

    os.makedirs(clone_path, exist_ok=True)

    logger.info("tarball 다운로드 시작: %s/%s → %s", owner, repo_name, clone_path)

    # GitHub tarball API로 다운로드
    tarball_url = f"{settings.GITHUB_API_BASE}/repos/{owner}/{repo_name}/tarball"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

    try:
        async with httpx.AsyncClient(
            timeout=settings.CLONE_TIMEOUT_SEC,
            follow_redirects=True,
        ) as client:
            resp = await client.get(tarball_url, headers=headers)

            if resp.status_code == 404:
                raise AppException(
                    code=ErrorCodes.CLONE_FAILED,
                    message="레포를 찾을 수 없습니다.",
                    status_code=404,
                )

            if resp.status_code != 200:
                raise AppException(
                    code=ErrorCodes.CLONE_FAILED,
                    message=f"tarball 다운로드 실패 (HTTP {resp.status_code})",
                    status_code=502,
                )

            tarball_data = resp.content

    except httpx.TimeoutException:
        shutil.rmtree(clone_path, ignore_errors=True)
        raise AppException(
            code=ErrorCodes.CLONE_TIMEOUT,
            message=f"다운로드 시간이 {settings.CLONE_TIMEOUT_SEC}초를 초과했습니다.",
            status_code=504,
        )
    except AppException:
        raise
    except Exception as e:
        shutil.rmtree(clone_path, ignore_errors=True)
        raise AppException(
            code=ErrorCodes.CLONE_FAILED,
            message=f"다운로드 실패: {e}",
            status_code=500,
        )

    # tarball 압축 해제 (보안 검증 포함)
    symlinks_removed = 0
    disallowed_removed = 0

    try:
        with tarfile.open(fileobj=io.BytesIO(tarball_data), mode="r:gz") as tar:
            for member in tar.getmembers():
                # 경로 순회 공격 차단 (path traversal)
                member_path = os.path.normpath(member.name)
                if member_path.startswith("..") or os.path.isabs(member_path):
                    logger.warning("경로 순회 공격 차단: %s", member.name)
                    continue

                # GitHub tarball은 최상위에 {owner}-{repo}-{hash}/ 접두사를 붙임
                # 이를 제거하여 clone_path에 직접 압축 해제
                parts = member.name.split("/", 1)
                if len(parts) < 2:
                    continue
                relative_path = parts[1]
                if not relative_path:
                    continue

                target_path = os.path.join(clone_path, relative_path)

                # 심볼릭 링크 차단
                if member.issym() or member.islnk():
                    symlinks_removed += 1
                    logger.debug("심볼릭 링크 제거: %s", relative_path)
                    continue

                # 디렉토리
                if member.isdir():
                    os.makedirs(target_path, exist_ok=True)
                    continue

                # 파일: 허용 확장자 검증
                if not _is_allowed_file(relative_path):
                    disallowed_removed += 1
                    continue

                # 파일 추출
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                try:
                    with tar.extractfile(member) as src:
                        if src is None:
                            continue
                        with open(target_path, "wb") as dst:
                            dst.write(src.read())
                except Exception as e:
                    logger.debug("파일 추출 실패 (스킵): %s — %s", relative_path, e)

    except tarfile.TarError as e:
        shutil.rmtree(clone_path, ignore_errors=True)
        raise AppException(
            code=ErrorCodes.CLONE_FAILED,
            message=f"압축 해제 실패: {e}",
            status_code=500,
        )

    if symlinks_removed:
        logger.info("심볼릭 링크 %d개 제거됨", symlinks_removed)
    if disallowed_removed:
        logger.info("비허용 파일 %d개 제거됨", disallowed_removed)

    # 압축 해제 후 추가 심볼릭 링크 검증 (방어적)
    _remove_symlinks(clone_path)

    # 파일 트리 스캔
    file_tree = scan_file_tree(clone_path)
    file_count = sum(1 for _ in _iter_files(clone_path))
    code_file_count = sum(
        1 for f in _iter_files(clone_path)
        if Path(f).suffix in CODE_EXTENSIONS
    )
    total_size_mb = _get_dir_size_mb(clone_path)

    # 용량 체크
    if total_size_mb > settings.CLONE_MAX_SIZE_MB:
        shutil.rmtree(clone_path, ignore_errors=True)
        raise AppException(
            code=ErrorCodes.CLONE_SIZE_EXCEEDED,
            message=f"레포 크기({total_size_mb:.0f}MB)가 상한({settings.CLONE_MAX_SIZE_MB}MB)을 초과합니다.",
            status_code=413,
        )

    logger.info(
        "다운로드 완료: %s (files=%d, code=%d, size=%.1fMB, symlinks_removed=%d)",
        clone_dir_name, file_count, code_file_count, total_size_mb, symlinks_removed,
    )

    return {
        "clone_path": clone_path,
        "file_count": file_count,
        "code_file_count": code_file_count,
        "total_size_mb": round(total_size_mb, 1),
        "file_tree": file_tree,
    }


def _is_allowed_file(relative_path: str) -> bool:
    """화이트리스트 기반 파일 허용 여부 판단."""
    filename = os.path.basename(relative_path)

    # 이름 기반 허용
    if filename in ALLOWED_FILENAMES:
        return True

    # 확장자 기반 허용
    ext = Path(filename).suffix.lower()
    if ext in ALLOWED_EXTENSIONS:
        return True

    # 확장자 없는 파일 중 dot으로 시작하지 않는 것 (Makefile 등)
    if not ext and not filename.startswith("."):
        return True

    return False


def _remove_symlinks(root_path: str) -> int:
    """디렉토리 내 모든 심볼릭 링크를 재귀적으로 제거."""
    removed = 0
    for dirpath, dirnames, filenames in os.walk(root_path, topdown=False):
        for name in filenames + dirnames:
            full_path = os.path.join(dirpath, name)
            if os.path.islink(full_path):
                os.unlink(full_path)
                removed += 1
                logger.debug("심볼릭 링크 제거: %s", full_path)
    if removed:
        logger.info("추가 심볼릭 링크 %d개 제거됨", removed)
    return removed


def scan_file_tree(root_path: str, max_depth: int = 3) -> list[dict]:
    """파일 트리를 재귀적으로 스캔합니다."""
    tree = []
    root = Path(root_path)

    for item in sorted(root.iterdir()):
        name = item.name
        if name in EXCLUDED_DIRS or name.startswith("."):
            continue

        if item.is_dir():
            children = []
            if max_depth > 0:
                children = scan_file_tree(str(item), max_depth - 1)
            tree.append({
                "name": name,
                "type": "directory",
                "children": children,
            })
        elif item.is_file():
            size = item.stat().st_size
            tree.append({
                "name": name,
                "type": "file",
                "size": size,
                "is_key_file": False,
            })

    return tree


def read_file_head(file_path: str, max_lines: int = 200) -> str:
    """파일의 첫 N줄을 읽습니다 (구조 분석용)."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                lines.append(line)
            return "".join(lines)
    except Exception:
        return ""


def delete_clone(clone_path: str) -> bool:
    """클론된 디렉토리를 삭제합니다."""
    try:
        if os.path.exists(clone_path):
            shutil.rmtree(clone_path)
            logger.info("클론 삭제: %s", clone_path)
            return True
        return False
    except Exception as e:
        logger.error("클론 삭제 실패: %s — %s", clone_path, e)
        return False


def _iter_files(root_path: str):
    """제외 목록을 적용하여 파일 경로를 순회합니다."""
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [
            d for d in dirnames
            if d not in EXCLUDED_DIRS and not d.startswith(".")
        ]
        for f in filenames:
            yield os.path.join(dirpath, f)


def _get_dir_size_mb(path: str) -> float:
    """디렉토리 총 크기(MB)를 계산합니다."""
    total = 0
    for f in _iter_files(path):
        try:
            total += os.path.getsize(f)
        except OSError:
            pass
    return total / (1024 * 1024)
