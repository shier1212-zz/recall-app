@echo off
setlocal
chcp 65001 >nul
echo 正在停止 Recall 前后端服务...

for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /PID %%p /F >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do taskkill /PID %%p /F >nul 2>&1

echo 已停止（8000 后端 / 5173 前端）
pause
