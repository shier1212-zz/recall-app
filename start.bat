@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo    Recall AI Mistake Notebook - one-click startup
echo ============================================
echo.

if not exist "backend\.venv\Scripts\python.exe" (
    echo [Error] backend deps missing. Run:
    echo   cd backend
    echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

echo [1/3] start backend FastAPI  (http://localhost:8000)
start "Recall-Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/3] start frontend Vite   (http://localhost:5173)
start "Recall-Frontend" cmd /k "cd /d %~dp0frontend && npm run dev -- --host --port 5173"

echo [3/3] wait 8s and open browser...
timeout /t 8 /nobreak >nul
start http://localhost:5173

echo.
echo Started. Two black windows are backend/frontend. Close them to stop.
echo To stop everything: double-click stop.bat
echo.
pause
