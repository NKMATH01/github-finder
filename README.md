# GitHub 기능 조달 워크벤치

바이브 코더가 한국어로 브리프를 작성하면, GitHub에서 **최적의 오픈소스 3개**를 찾아 비교하고,
선택한 레포를 자동 클론한 뒤 **구조 분석 리포트**(✅가능/⚠️위험/❌실패)를 제공하며,
Claude Code에 바로 붙여넣을 **통합 프롬프트**를 생성하는 로컬 웹앱입니다.

> "한 번에 완벽한 답"이 아니라 **"최선의 후보군을 빠르게 검증할 수 있는 도우미"**

## 주요 기능

- **상세 브리프 입력** — 필수 3개(목표/스택/환경) + 선택 3개(우선순위/참고레포/추가조건)
- **성격별 3종 분류** — 완성도 최고 / 통합 용이 / 고정밀
- **7축 신뢰성 스코어링** — 기능일치, 실행가능성, 유지보수, 이슈해결, 설치난이도, 문서품질, 스택호환
- **자동 클론 + 구조 분석** — git clone → ✅/⚠️/❌ 3분류 리포트
- **통합 프롬프트 생성** — 기본 + 강화(리포트 반영) 프롬프트
- **검색 이력/즐겨찾기** — Supabase에 영구 저장

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | Next.js 14+ (App Router) + Tailwind CSS + shadcn/ui |
| Backend | Python 3.11+ / FastAPI / uvicorn |
| Database | Supabase (PostgreSQL) |
| LLM | OpenAI GPT-4o (Structured Output) |
| GitHub | REST API v3 |

## 빠른 시작

### 1. 환경 변수 설정

```bash
cp .env.example .env
```

`.env`를 열고 API 키를 입력하세요:

```
GITHUB_TOKEN=ghp_xxxx          # https://github.com/settings/tokens
OPENAI_API_KEY=sk-xxxx         # https://platform.openai.com/api-keys
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJxxxx
SUPABASE_SERVICE_KEY=eyJxxxx
```

### 2. Supabase 테이블 생성

Supabase Dashboard > SQL Editor에서 `supabase_migration.sql`을 실행하세요.

### 3. 실행

**방법 A: 실행 스크립트 (권장)**

```bash
# Windows
start.bat

# Unix/Mac
chmod +x start.sh && ./start.sh
```

**방법 B: 수동 실행**

```bash
# 백엔드
cd backend
python -m venv .venv
.venv/Scripts/activate    # Windows
# source .venv/bin/activate  # Unix
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 프론트엔드 (새 터미널)
cd frontend
npm install
npm run dev
```

**방법 C: Docker**

```bash
docker-compose up
```

### 4. 접속

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs (Swagger UI)

## 사용 방법

1. 브리프 폼에서 **목표 기능**, **프로젝트 스택**, **실행 환경**을 입력
2. "GitHub에서 찾기" 클릭 → 약 25~30초 대기
3. **성격별 Top 3** 후보 카드에서 비교
4. "📦 가져오기" → 자동 클론 + 구조 분석 리포트
5. "📋 프롬프트 복사" → Claude Code에 붙여넣기

## 프로젝트 구조

```
github-finder/
├── backend/              # FastAPI
│   ├── services/         # 11개 서비스 모듈
│   ├── routers/          # 4개 API 라우터 (18 엔드포인트)
│   ├── models/           # Pydantic + LLM Schema + Error
│   └── tests/            # pytest 34개 테스트
├── frontend/             # Next.js
│   ├── components/       # 11개 커스텀 컴포넌트
│   ├── hooks/            # 3개 SWR 훅
│   └── lib/              # API client, types, Supabase
├── cloned_repos/         # 클론 저장소 (gitignore)
├── CLAUDE.md             # 프로젝트 지시서
├── supabase_migration.sql
├── docker-compose.yml
├── start.sh / start.bat
└── .env.example
```

## 테스트

```bash
cd backend
python -m pytest tests/ -v
```

## 주의사항

- 모든 신뢰도 점수에는 **"LLM 분석 기반 (실행 미검증)"** 라벨이 표시됩니다
- 구조 분석 리포트는 참고용이며, 실제 실행 전에는 보장할 수 없습니다
- 개인 사용 전용 도구입니다 (인증/과금 없음)
- GitHub API rate limit: 인증 토큰 사용 시 시간당 5,000회

## 라이선스

개인 프로젝트
