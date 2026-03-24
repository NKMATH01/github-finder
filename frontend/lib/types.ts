/** GitHub 기능 조달 워크벤치 — TypeScript 타입 정의 */

// ─── Brief ───

export interface BriefInput {
  goal_description: string;
  project_stack: string[];
  execution_environment: "web_browser" | "server" | "local_app" | "any";
  priority?: "accuracy" | "speed" | "balanced";
  reference_repo?: string;
  additional_conditions?: string;
}

// ─── Search ───

export interface SearchResponse {
  search_id: string;
  keywords_en: string[];
  status: string;
}

export interface SearchStatus {
  status: "pending" | "running" | "processing" | "completed" | "failed" | "no_results";
  progress: number;
  message: string;
  step?: number;
  warnings?: string[];
}

export interface SSEEvent {
  step: number;
  progress: number;
  message: string;
  status: "running" | "completed" | "failed" | "no_results" | "heartbeat" | "pending";
  warnings?: string[];
  error?: string;
  result_id?: string;
}

export interface ScoreDetail {
  feature_match: number;
  runnability: number;
  maintenance: number;
  issue_resolution: number;
  install_ease: number;
  documentation: number;
  stack_compatibility: number;
}

export interface KeyFile {
  path: string;
  role: string;
  importance: "core" | "supporting" | "example";
}

export interface Candidate {
  id: string;
  rank: number;
  category: string;
  repo_url: string;
  repo_name: string;
  total_score: number;
  score_detail: ScoreDetail;
  confidence_label: string;
  stars: number;
  last_updated?: string;
  key_files: KeyFile[];
  pros: string[];
  cons: string[];
  failure_scenarios: string[];
  estimated_size_mb?: number;
  estimated_clone_seconds?: number;
  known_install_issues: string[];
  stack_conflicts: string[];
  prompt_id?: string;
  clone_id?: string;
}

export interface SearchResults {
  search_id: string;
  brief_summary: Record<string, unknown>;
  candidates: Candidate[];
  comparison_table?: Record<string, unknown>;
}

// ─── Clone ───

export interface ClonePreview {
  repo_name: string;
  estimated_size_mb?: number;
  estimated_seconds?: number;
  known_issues: string[];
  stack_conflicts: string[];
  recommendation: string;
}

export interface SafeModule {
  file_path: string;
  target_path?: string;
  action: string;
  reason: string;
}

export interface RiskyModule {
  file_path: string;
  package_name?: string;
  issue: string;
  solution: string;
  severity: "low" | "medium" | "high";
}

export interface FailModule {
  file_path: string;
  issue: string;
  environment_constraint?: string;
  alternative: string;
}

export interface CloneStatus {
  clone_id: string;
  status: "cloning" | "scanning" | "analyzing" | "completed" | "failed";
  progress: number;
  clone_path?: string;
  file_count?: number;
  code_file_count?: number;
  total_size_mb?: number;
  file_tree?: FileTreeNode[];
  structure_report?: string;
  integration_safe: SafeModule[];
  integration_risky: RiskyModule[];
  integration_fail: FailModule[];
  enhanced_prompt?: string;
  error_message?: string;
}

export interface FileTreeNode {
  name: string;
  type: "file" | "directory";
  size?: number;
  children?: FileTreeNode[];
  is_key_file?: boolean;
}

// ─── Prompt ───

export interface Prompt {
  id: string;
  candidate_id: string;
  target: string;
  content: string;
  enhanced_content?: string;
  alternative_prompts: Array<{ label: string; content: string }>;
  copy_count: number;
}

// ─── Favorite ───

export interface Favorite {
  id: string;
  repo_url: string;
  repo_name: string;
  category?: string;
  query_ko?: string;
  note?: string;
  created_at: string;
}

// ─── Storage ───

export interface StorageInfo {
  total_size_mb: number;
  repo_count: number;
  repos: Array<{
    name: string;
    size_mb: number;
    created_at: string;
  }>;
}

// ─── Error ───

export interface ApiError {
  error: {
    code: string;
    message: string;
    detail?: string;
    retry_after?: number;
  };
}

// ─── App State ───

export type AppView = "brief" | "loading" | "results" | "clone";
