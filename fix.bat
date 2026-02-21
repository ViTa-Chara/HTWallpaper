@echo off
setlocal EnableExtensions
cd /d %~dp0

set "CFG=%CD%\.venv\pyvenv.cfg"
if not exist "%CFG%" (
  echo [ERROR] pyvenv.cfg not found. Please create virtual environment first.
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dpn0.ps1"
if errorlevel 1 exit /b 1
exit /b 0
