#!/bin/bash
# GitHub 기능 조달 워크벤치 — 실행 스크립트

set -e

echo "🔍 GitHub 기능 조달 워크벤치 시작..."

# 1. git 존재 확인
if ! command -v git &> /dev/null; then
    echo "⚠️  git이 설치되지 않았습니다. clone 기능은 zipball 폴백으로 동작합니다."
fi

# 2. .env 확인
if [ ! -f .env ]; then
    echo "❌ .env 파일이 없습니다. .env.example을 복사하여 API 키를 설정하세요:"
    echo "   cp .env.example .env"
    exit 1
fi

# 3. Backend 구동
echo "🐍 백엔드 시작 (localhost:8000)..."
cd backend
if [ ! -d ".venv" ]; then
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# 4. Frontend 구동
echo "⚛️  프론트엔드 시작 (localhost:3000)..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run dev &
FRONTEND_PID=$!
cd ..

# 5. 브라우저 열기 (2초 대기)
sleep 2
if command -v open &> /dev/null; then
    open http://localhost:3000
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:3000
fi

echo ""
echo "✅ 워크벤치 실행 중!"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000/docs"
echo ""
echo "종료하려면 Ctrl+C를 누르세요."

# 종료 시 프로세스 정리
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
