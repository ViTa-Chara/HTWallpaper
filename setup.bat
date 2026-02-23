@echo off
setlocal EnableExtensions
cd /d %~dp0
set ROOT=%~dp0

echo ========================================
echo HTWallpaper Setup
echo ========================================
echo.

:: Check if uv is already installed system-wide
where uv >nul 2>&1
if %errorLevel% equ 0 (
    echo [OK] uv is already installed system-wide.
    set "UV=uv"
    goto :sync
)

:: Check if local uv exists
set "LOCAL_UV=%ROOT%.uv\uv.exe"
if exist "%LOCAL_UV%" (
    echo [OK] Found local uv at .uv\uv.exe
    set "UV=%LOCAL_UV%"
    goto :sync
)

:: Download and install uv locally
echo [INFO] uv not found. Installing uv locally...
set "UV_DIR=%ROOT%.uv"
if not exist "%UV_DIR%" mkdir "%UV_DIR%"

:: Download uv installer script
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$url = 'https://astral.sh/uv/install.ps1'; " ^
    "$script = Join-Path $env:TEMP 'uv-install.ps1'; " ^
    "Invoke-WebRequest -Uri $url -OutFile $script -UseBasicParsing; " ^
    "& $script -TargetDir '%UV_DIR%'"

if %errorLevel% neq 0 (
    echo [ERROR] Failed to install uv.
    pause
    exit /b 1
)

set "UV=%UV_DIR%\uv.exe"
echo [OK] uv installed at %UV%

:sync
:: Sync dependencies
echo.
echo [INFO] Syncing dependencies...
"%UV%" sync --no-dev
if %errorLevel% neq 0 (
    echo [ERROR] Failed to sync dependencies.
    pause
    exit /b 1
)

echo.
echo ========================================
echo [OK] Setup complete!
echo ========================================
echo.
echo You can now run the application using:
echo   - run.bat (requires admin)
echo   - run.vbs (no admin, double-click)
echo.
pause
