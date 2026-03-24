# CLAUDE.md — GitHub 기능 조달 워크벤치 프로젝트 지시서

## 프로젝트 개요
바이브 코더가 한국어 브리프(필수 3개 + 선택 3개)를 작성하면 GitHub에서 최적의 오픈소스 3개를 찾아
비교해주고, 선택 레포를 자동 클론한 뒤 **구조 분석 리포트(✅가능/⚠️위험/❌실패)를 먼저 보여준 후**
강화 통합 프롬프트를 생성하는 로컬 웹앱.

## 핵심 원칙 (반드시 준수)
- ★ clone 후 바로 프롬프트를 뱉지 말 것. 반드시 구조 분석 리포트를 거칠 것
- ★ 모든 신뢰도 점수에 "LLM 분석 기반 (실행 미검증)" 라벨 필수
- ★ 각 서비스 모듈은 독립적으로 테스트 가능하도록 인터페이스 분리
- 개인 사용 전용: 인증/과금/멀티유저 로직 불필요
- "한 번에 완벽한 답"이 아니라 "최선의 후보군을 빠르게 검증할 수 있는 도우미"

## 기술 스택
- Frontend: Next.js 14+ (App Router) + Tailwind CSS + shadcn/ui
- Backend: Python 3.11+ / FastAPI / uvicorn
- Database: Supabase (PostgreSQL)
- LLM: OpenAI GPT-4o (Structured Output — JSON Schema 보장)
- 실행: localhost:3000 (FE) + localhost:8000 (BE)

## 코딩 컨벤션
- TypeScript: strict mode, 함수형 컴포넌트, 명시적 타입
- Python: type hints 필수, Pydantic 모델 사용, async/await 기본
- 변수명: camelCase(TS), snake_case(Python)
- 에러: 모든 외부 API 호출에 try/catch + AppException으로 통일
- 보안: subprocess는 shell=False 필수, URL은 정규식 검증 후 사용

## LLM 호출 규칙
- 모든 GPT-4o 호출은 services/llm_client.py의 call_gpt4o_structured() 사용
- JSON Schema는 models/llm_schemas.py에 정의된 5종만 사용
- 에러 시 최대 3회 재시도 (exponential backoff)
- 비용 추적: 모든 호출에 input/output 토큰 수 로깅

## DB 스키마 핵심
- cloned_repos가 클론/분석 데이터의 단일 진실 원천 (Single Source of Truth)
- candidates에서는 clone_id FK로 참조만 함 (중복 저장 금지)
- 에러 응답은 models/error_models.py의 ErrorResponse 형식으로 통일

## 핵심 파이프라인 (10단계)
1. 브리프 파싱 + 기능 분해
2. 검색어 확장 (GPT-4o Call Point 1)
3. GitHub API 1차 필터링 (Stars≥50, 12개월 내 커밋)
4. LLM 딥 리딩 + 7축 스코어링 (GPT-4o Call Point 2)
5. 성격별 3종 분류 (GPT-4o Call Point 3)
6. 핵심 파일 특정 + 기본 프롬프트 생성 (GPT-4o Call Point 4)
7. 클론 사전 정보 표시
8. git clone --depth 1 + 파일 트리 스캔
9. 구조 분석 리포트 생성 (GPT-4o Call Point 5)
10. 강화 통합 프롬프트 생성
