"""환경변수 로딩 및 설정 관리."""

import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드 — 여러 위치 시도
_possible_paths = [
    Path.cwd() / ".env",
    Path.cwd().parent / ".env",
    Path(__file__).resolve().parent / ".env",
    Path(__file__).resolve().parent.parent / ".env",
]

_loaded = False
for _p in _possible_paths:
    if _p.exists():
        load_dotenv(str(_p), override=True)
        _loaded = True
        break

if not _loaded:
    # 최후 수단: find_dotenv
    from dotenv import find_dotenv
    _found = find_dotenv(usecwd=True)
    if _found:
        load_dotenv(_found, override=True)


class Settings:
    @property
    def GITHUB_TOKEN(self) -> str:
        return os.getenv("GITHUB_TOKEN", "")

    @property
    def GITHUB_API_BASE(self) -> str:
        return "https://api.github.com"

    @property
    def OPENAI_API_KEY(self) -> str:
        return os.getenv("OPENAI_API_KEY", "")

    @property
    def LLM_MODEL(self) -> str:
        return os.getenv("LLM_MODEL", "gpt-4o")

    @property
    def LLM_MAX_RETRIES(self) -> int:
        return int(os.getenv("LLM_MAX_RETRIES", "3"))

    @property
    def LLM_TIMEOUT_SEC(self) -> int:
        return int(os.getenv("LLM_TIMEOUT_SEC", "60"))

    @property
    def SUPABASE_URL(self) -> str:
        return os.getenv("SUPABASE_URL", "")

    @property
    def SUPABASE_ANON_KEY(self) -> str:
        return os.getenv("SUPABASE_ANON_KEY", "")

    @property
    def SUPABASE_SERVICE_KEY(self) -> str:
        return os.getenv("SUPABASE_SERVICE_KEY", "")

    @property
    def CLONE_BASE_PATH(self) -> str:
        return os.getenv("CLONE_BASE_PATH", "./cloned_repos")

    @property
    def CLONE_MAX_SIZE_MB(self) -> int:
        return int(os.getenv("CLONE_MAX_SIZE_MB", "500"))

    @property
    def CLONE_TIMEOUT_SEC(self) -> int:
        return int(os.getenv("CLONE_TIMEOUT_SEC", "120"))

    @property
    def FRONTEND_URL(self) -> str:
        return os.getenv("FRONTEND_URL", "http://localhost:3000")


settings = Settings()
