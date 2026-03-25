"""SkillsMP 스킬 관련 Pydantic 모델."""

from typing import Optional
from pydantic import BaseModel, Field


# ─── 입력 ───

class SkillSearchInput(BaseModel):
    query_ko: str = Field(..., max_length=2000, description="원하는 기능 (한국어)")
    project_stack: Optional[str] = Field(default=None, description="프로젝트 스택")
    target_tool: str = Field(
        default="claude_code",
        pattern="^(claude_code|codex_cli|all)$",
        description="대상 도구",
    )


class SkillSearchRequest(BaseModel):
    brief: SkillSearchInput


class SkillSearchResponse(BaseModel):
    search_id: str
    status: str


# ─── 스킬 결과 ───

class SkillResult(BaseModel):
    skill_id: str
    name: str
    description: str = ""
    github_url: str = ""
    skill_path: str = ""
    category: str = ""
    stars: int = 0
    last_updated: Optional[str] = None
    author: str = ""


class SkillDetail(SkillResult):
    skill_md_content: str = ""
    dependencies: list[str] = []
    install_size_kb: int = 0


class SkillScoreDetail(BaseModel):
    feature_match: int = 0       # /30
    quality: int = 0             # /25
    compatibility: int = 0       # /20
    community_trust: int = 0     # /15
    install_ease: int = 0        # /10


class ScoredSkill(BaseModel):
    skill_id: str
    name: str
    description: str = ""
    github_url: str = ""
    skill_path: str = ""
    author: str = ""
    stars: int = 0
    last_updated: Optional[str] = None
    skill_md_content: str = ""
    total_score: int = 0
    score_detail: SkillScoreDetail = SkillScoreDetail()
    confidence_label: str = "LLM 분석 기반 (실행 미검증)"
    pros: list[str] = []
    cons: list[str] = []
    warnings: list[str] = []


class ClassifiedSkill(ScoredSkill):
    category: str = ""  # 완성도최고 | 바로적용 | 가장강력
    category_reason: str = ""
    rank: int = 0


# ─── 설치 ───

class SkillDownloadRequest(BaseModel):
    github_url: str = Field(..., description="GitHub URL of the skill")
    skill_path: str = Field(default="", description="Path to the skill within the repo")


class SkillPackage(BaseModel):
    skill_name: str
    files: list[dict] = []        # [{name, size_kb, content_preview}]
    total_size_kb: int = 0
    install_path_project: str = ""
    install_path_personal: str = ""
    install_command: str = ""
    skill_md_preview: str = ""


# ─── 검색 결과 ───

class SkillSearchResults(BaseModel):
    search_id: str
    query_ko: str = ""
    candidates: list[ClassifiedSkill] = []


# ─── 검색 상태 ───

class SkillSearchStatus(BaseModel):
    status: str  # pending, running, completed, failed, no_results
    progress: int = 0
    message: str = ""
    step: int = 0  # 1~4
    warnings: Optional[list[str]] = None
