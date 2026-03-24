@echo off
REM GitHub 기능 조달 워크벤치 — Windows 실행 스크립트

echo 🔍 GitHub 기능 조달 워크벤치 시작...

REM 1. .env 확인
if not exist .env (
    echo ❌ .env 파일이 없습니다. .env.example을 복사하여 API 키를 설정하세요:
    echo    copy .env.example .env
    exit /b 1
)

REM 2. Backend 구동
echo 🐍 백엔드 시작 (localhost:8000)...
cd backend
if not exist .venv (
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)
start /B uvicorn main:app --host 0.0.0.0 --port 8000 --reload
cd ..

REM 3. Frontend 구동
echo ⚛️ 프론트엔드 시작 (localhost:3000)...
cd frontend
if not exist node_modules (
    npm install
)
start /B npm run dev
cd ..

REM 4. 브라우저 열기
timeout /t 3 /nobreak > nul
start http://localhost:3000

echo.
echo ✅ 워크벤치 실행 중!
echo    Frontend: http://localhost:3000
echo    Backend:  http://localhost:8000/docs
echo.
echo 종료하려면 이 창을 닫으세요.
pause
