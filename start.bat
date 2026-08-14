@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo    Recall AI 智能错题本 · 一键启动
echo ============================================
echo.

if not exist "backend\.venv\Scripts\python.exe" (
    echo [错误] 后端依赖未安装。请先执行：
    echo   cd backend
    echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

echo [1/3] 启动后端 FastAPI  (http://localhost:8000)
start "Recall-Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo [2/3] 启动前端 Vite    (http://localhost:5173)
start "Recall-Frontend" cmd /k "cd /d %~dp0frontend && npm run dev -- --host --port 5173"

echo [3/3] 等待服务启动，自动打开浏览器...
timeout /t 8 /nobreak >nul
start http://localhost:5173

echo.
echo 启动完成！
echo   - 弹出的两个黑色窗口分别是「后端」和「前端」，关闭即停止服务
echo   - 停止全部服务可双击 stop.bat
echo.
pause
