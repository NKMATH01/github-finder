-- ===================================================
-- GitHub 기능 조달 워크벤치 — Supabase PostgreSQL 스키마
-- v6-normalized (정규화 완료)
-- ===================================================
-- 사용법: Supabase Dashboard > SQL Editor에서 실행

-- 1. searches
CREATE TABLE IF NOT EXISTS searches (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  query_ko TEXT NOT NULL,
  brief JSONB NOT NULL DEFAULT '{}'::JSONB,
  keywords_en TEXT[] NOT NULL DEFAULT '{}',
  target_platform TEXT DEFAULT 'any',
  candidate_count INTEGER DEFAULT 0,
  status TEXT DEFAULT 'pending'
    CHECK (status IN ('pending','running','processing','completed','failed','no_results')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  current_step INTEGER DEFAULT 0,
  error_log JSONB DEFAULT '[]'::JSONB
);

CREATE INDEX IF NOT EXISTS idx_searches_created_at ON searches(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_searches_query_ko ON searches(query_ko);

-- 2. cloned_repos (먼저 생성 — candidates에서 FK 참조)
CREATE TABLE IF NOT EXISTS cloned_repos (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  repo_url TEXT NOT NULL,
  repo_name TEXT NOT NULL,
  clone_path TEXT NOT NULL DEFAULT '',
  file_count INTEGER DEFAULT 0,
  code_file_count INTEGER DEFAULT 0,
  total_size_mb FLOAT DEFAULT 0,
  file_tree JSONB NOT NULL DEFAULT '[]'::JSONB,
  structure_report TEXT,
  integration_safe JSONB DEFAULT '[]'::JSONB,
  integration_risky JSONB DEFAULT '[]'::JSONB,
  integration_fail JSONB DEFAULT '[]'::JSONB,
  dependency_conflicts JSONB DEFAULT '[]'::JSONB,
  status TEXT DEFAULT 'cloning'
    CHECK (status IN ('cloning','scanning','analyzing','completed','failed','deleted')),
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_cloned_repos_status ON cloned_repos(status);
CREATE INDEX IF NOT EXISTS idx_cloned_repos_repo_url ON cloned_repos(repo_url);
CREATE INDEX IF NOT EXISTS idx_cloned_repos_created_at ON cloned_repos(created_at DESC);

-- 3. candidates (정규화: clone_id FK로 cloned_repos 참조)
CREATE TABLE IF NOT EXISTS candidates (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  search_id UUID REFERENCES searches(id) ON DELETE CASCADE,
  repo_url TEXT NOT NULL,
  repo_name TEXT NOT NULL,
  stars INTEGER DEFAULT 0,
  last_updated TIMESTAMPTZ,
  category TEXT NOT NULL
    CHECK (category IN ('완성도최고','통합용이','고정밀','난이도하','난이도중','난이도상')),
  category_reason TEXT,
  total_score INTEGER DEFAULT 0,
  score_detail JSONB NOT NULL DEFAULT '{}'::JSONB,
  confidence_label TEXT DEFAULT 'LLM 분석 기반 (실행 미검증)',
  key_files JSONB DEFAULT '[]'::JSONB,
  pros TEXT[] DEFAULT '{}',
  cons TEXT[] DEFAULT '{}',
  failure_scenarios TEXT[] DEFAULT '{}',
  estimated_size_mb FLOAT,
  estimated_clone_seconds INTEGER,
  known_install_issues TEXT[] DEFAULT '{}',
  stack_conflicts TEXT[] DEFAULT '{}',
  clone_id UUID REFERENCES cloned_repos(id) ON DELETE SET NULL,
  rank INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_candidates_search_id ON candidates(search_id);
CREATE INDEX IF NOT EXISTS idx_candidates_search_rank ON candidates(search_id, rank);

-- 4. prompts
CREATE TABLE IF NOT EXISTS prompts (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  candidate_id UUID REFERENCES candidates(id) ON DELETE CASCADE,
  clone_id UUID REFERENCES cloned_repos(id) ON DELETE SET NULL,
  target TEXT DEFAULT 'claude'
    CHECK (target IN ('claude','codex','cursor')),
  content TEXT NOT NULL,
  enhanced_content TEXT,
  alternative_prompts JSONB DEFAULT '[]'::JSONB,
  copy_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prompts_candidate_id ON prompts(candidate_id);

-- 5. github_cache (API 응답 캐시)
CREATE TABLE IF NOT EXISTS github_cache (
  cache_key TEXT PRIMARY KEY,
  response_data JSONB NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_github_cache_expires ON github_cache(expires_at);

-- 6. favorites
CREATE TABLE IF NOT EXISTS favorites (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  repo_url TEXT NOT NULL UNIQUE,
  repo_name TEXT NOT NULL,
  category TEXT,
  query_ko TEXT,
  note TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_favorites_created_at ON favorites(created_at DESC);

-- 7. skill_searches (스킬 검색 이력)
CREATE TABLE IF NOT EXISTS skill_searches (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  query_ko TEXT NOT NULL,
  brief JSONB NOT NULL DEFAULT '{}'::JSONB,
  keywords_en TEXT[] NOT NULL DEFAULT '{}',
  candidate_count INTEGER DEFAULT 0,
  status TEXT DEFAULT 'pending'
    CHECK (status IN ('pending','running','processing','completed','failed','no_results')),
  current_step INTEGER DEFAULT 0,
  error_log JSONB DEFAULT '[]'::JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skill_searches_created_at ON skill_searches(created_at DESC);

-- 8. skill_candidates (스킬 후보)
CREATE TABLE IF NOT EXISTS skill_candidates (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  search_id UUID REFERENCES skill_searches(id) ON DELETE CASCADE,
  skill_id TEXT NOT NULL,
  skill_name TEXT NOT NULL,
  github_url TEXT NOT NULL,
  skill_path TEXT NOT NULL DEFAULT '',
  author TEXT,
  stars INTEGER DEFAULT 0,
  category TEXT NOT NULL
    CHECK (category IN ('완성도최고','바로적용','가장강력')),
  category_reason TEXT,
  total_score INTEGER DEFAULT 0,
  score_detail JSONB NOT NULL DEFAULT '{}'::JSONB,
  confidence_label TEXT DEFAULT 'LLM 분석 기반 (실행 미검증)',
  skill_md_preview TEXT,
  pros TEXT[] DEFAULT '{}',
  cons TEXT[] DEFAULT '{}',
  warnings TEXT[] DEFAULT '{}',
  install_command TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skill_candidates_search_id ON skill_candidates(search_id);

-- RLS 비활성화 (개인용 로컬 도구)
ALTER TABLE searches ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE cloned_repos ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE favorites ENABLE ROW LEVEL SECURITY;
ALTER TABLE github_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_searches ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_candidates ENABLE ROW LEVEL SECURITY;

-- 모든 작업 허용 (service_key 사용)
CREATE POLICY "Allow all for service key" ON searches FOR ALL USING (true);
CREATE POLICY "Allow all for service key" ON candidates FOR ALL USING (true);
CREATE POLICY "Allow all for service key" ON cloned_repos FOR ALL USING (true);
CREATE POLICY "Allow all for service key" ON prompts FOR ALL USING (true);
CREATE POLICY "Allow all for service key" ON favorites FOR ALL USING (true);
CREATE POLICY "Allow all for service key" ON github_cache FOR ALL USING (true);
CREATE POLICY "Allow all for service key" ON skill_searches FOR ALL USING (true);
CREATE POLICY "Allow all for service key" ON skill_candidates FOR ALL USING (true);
