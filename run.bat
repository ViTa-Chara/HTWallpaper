@echo off
setlocal
net session >nul 2>&1
if %errorLevel% neq 0 (
  powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)
cd /d %~dp0
set ROOT=%~dp0

:: Check if uv is available
where uv >nul 2>&1
if %errorLevel% neq 0 (
  :: Try local uv
  set "UV=%ROOT%.uv\uv.exe"
  if not exist "%UV%" (
    echo [ERROR] uv not found. Please run setup.bat first.
    pause
    exit /b 1
  )
) else (
  set "UV=uv"
)

:: Start tray app with uv run
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root='%ROOT%'; $log=Join-Path $root 'data\run.log'; New-Item -ItemType Directory -Path (Join-Path $root 'data') -Force | Out-Null; Add-Content $log ('[' + (Get-Date) + '] start'); $uv=if ($env:UV) { $env:UV } else { 'uv' }; Add-Content $log ('[' + (Get-Date) + '] uv=' + $uv); $p=Start-Process -FilePath $uv -ArgumentList 'run','--no-dev','-m','app.tray' -WorkingDirectory $root -WindowStyle Hidden -PassThru; Add-Content $log ('[' + (Get-Date) + '] pid=' + $p.Id)"
