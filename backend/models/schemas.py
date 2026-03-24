"""Pydantic 요청/응답 모델."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ─── Brief 입력 ───

class BriefInput(BaseModel):
    goal_description: str = Field(..., max_length=2000, description="목표 기능 (한국어)")
    project_stack: list[str] = Field(default=["any"], description="프로젝트 스택 (비워두면 AI 추천)")
    execution_environment: str = Field(
        ...,
        pattern="^(web_browser|server|local_app|any)$",
        description="실행 환경",
    )
    priority: str = Field(
        default="balanced",
        pattern="^(accuracy|speed|balanced)$",
    )
    reference_repo: Optional[str] = Field(
        default=None,
        pattern=r"^https://github\.com/.+/.+$",
    )
    additional_conditions: Optional[str] = Field(default=None, max_length=1000)


# ─── Search ───

class SearchRequest(BaseModel):
    brief: BriefInput


class SearchResponse(BaseModel):
    search_id: str
    keywords_en: list[str]
    status: str


class SearchStatus(BaseModel):
    status: str  # pending, running, completed, failed, no_results
    progress: int
    message: str
    step: int = 0  # 현재 단계 (1~7)
    warnings: Optional[list[str]] = None  # 단계별 경고 메시지


class ScoreDetail(BaseModel):
    feature_match: int = 0
    runnability: int = 0
    maintenance: int = 0
    issue_resolution: int = 0
    install_ease: int = 0
    documentation: int = 0
    stack_compatibility: int = 0


class KeyFile(BaseModel):
    path: str
    role: str
    importance: str  # core, supporting, example


class CandidateResult(BaseModel):
    id: str
    rank: int
    category: str
    repo_url: str
    repo_name: str
    total_score: int
    score_detail: ScoreDetail
    confidence_label: str
    stars: int
    last_updated: Optional[str] = None
    key_files: list[KeyFile]
    pros: list[str]
    cons: list[str]
    failure_scenarios: list[str]
    estimated_size_mb: Optional[float] = None
    estimated_clone_seconds: Optional[int] = None
    known_install_issues: list[str] = []
    stack_conflicts: list[str] = []
    prompt_id: Optional[str] = None
    clone_id: Optional[str] = None


class SearchResults(BaseModel):
    search_id: str
    brief_summary: dict
    candidates: list[CandidateResult]
    comparison_table: Optional[dict] = None


# ─── Clone ───

class CloneRequest(BaseModel):
    candidate_id: str


class ClonePreviewResponse(BaseModel):
    repo_name: str
    estimated_size_mb: Optional[float] = None
    estimated_seconds: Optional[int] = None
    known_issues: list[str] = []
    stack_conflicts: list[str] = []
    recommendation: str


class SafeModule(BaseModel):
    file_path: str
    target_path: Optional[str] = None
    action: str
    reason: str


class RiskyModule(BaseModel):
    file_path: str
    package_name: Optional[str] = None
    issue: str
    solution: str
    severity: str  # low, medium, high


class FailModule(BaseModel):
    file_path: str
    issue: str
    environment_constraint: Optional[str] = None
    alternative: str


class CloneStatusResponse(BaseModel):
    clone_id: str
    status: str  # cloning, scanning, analyzing, completed, failed
    progress: int
    clone_path: Optional[str] = None
    file_count: Optional[int] = None
    code_file_count: Optional[int] = None
    total_size_mb: Optional[float] = None
    file_tree: Optional[list] = None
    structure_report: Optional[str] = None
    integration_safe: list[SafeModule] = []
    integration_risky: list[RiskyModule] = []
    integration_fail: list[FailModule] = []
    enhanced_prompt: Optional[str] = None
    error_message: Optional[str] = None


# ─── Prompts ───

class PromptResponse(BaseModel):
    id: str
    candidate_id: str
    target: str
    content: str
    enhanced_content: Optional[str] = None
    alternative_prompts: list[dict] = []
    copy_count: int = 0


# ─── Favorites ───

class FavoriteCreate(BaseModel):
    repo_url: str
    repo_name: str
    category: Optional[str] = None
    query_ko: Optional[str] = None
    note: Optional[str] = None


class FavoriteResponse(BaseModel):
    id: str
    repo_url: str
    repo_name: str
    category: Optional[str] = None
    query_ko: Optional[str] = None
    note: Optional[str] = None
    created_at: str


# ─── Storage ───

class StorageInfo(BaseModel):
    total_size_mb: float
    repo_count: int
    repos: list[dict]
