@echo off
setlocal
net session >nul 2>&1
if %errorLevel% neq 0 (
  powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)
cd /d %~dp0
set ROOT=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root='%ROOT%'; $log=Join-Path $root 'data\run.log'; New-Item -ItemType Directory -Path (Join-Path $root 'data') -Force | Out-Null; Add-Content $log ('[' + (Get-Date) + '] start'); $pyw=Join-Path $root '.venv\Scripts\pythonw.exe'; $py=Join-Path $root '.venv\Scripts\python.exe'; if (!(Test-Path $pyw)) { $pyw=$py } if (!(Test-Path $pyw)) { $pyw='pythonw.exe' } Add-Content $log ('[' + (Get-Date) + '] python=' + $pyw); $p=Start-Process -FilePath $pyw -ArgumentList '-m','app.tray' -WorkingDirectory $root -WindowStyle Hidden -PassThru; Add-Content $log ('[' + (Get-Date) + '] pid=' + $p.Id)"
