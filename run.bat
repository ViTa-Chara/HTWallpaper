@echo off
setlocal
net session >nul 2>&1
if %errorLevel% neq 0 (
  powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)
cd /d %~dp0
set ROOT=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%bootstrap.ps1" -Root "%ROOT%"
if %errorlevel% neq 0 (
  start notepad "%ROOT%data\run.log"
)

