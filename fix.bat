@echo off
setlocal EnableExtensions
cd /d %~dp0

set "CFG=%CD%\.venv\pyvenv.cfg"
if not exist "%CFG%" (
  echo [ERROR] 未找到 .venv\pyvenv.cfg，请先创建虚拟环境。
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$cfg = Join-Path (Get-Location) '.venv\pyvenv.cfg';" ^
  "$lines = Get-Content -LiteralPath $cfg -ErrorAction Stop;" ^
  "$versionLine = $lines | Where-Object { $_ -match '^\s*version\s*=\s*' } | Select-Object -First 1;" ^
  "$targetVersion = $null; if ($versionLine -match '([0-9]+\.[0-9]+)') { $targetVersion = $Matches[1] };" ^
  "$candidates = @();" ^
  "if ($targetVersion) { $candidates += @('py -' + $targetVersion,'python' + $targetVersion.Replace('.',''),'python' + $targetVersion) };" ^
  "$candidates += @('py -3','python3','python');" ^
  "$exePath = $null;" ^
  "foreach ($candidate in $candidates) {" ^
  "  $parts = $candidate -split '\\s+';" ^
  "  $cmd = $parts[0];" ^
  "  $args = @(); if ($parts.Length -gt 1) { $args = $parts[1..($parts.Length-1)] };" ^
  "  try {" ^
  "    $resolved = & $cmd @args -c 'import sys; print(sys.executable)' 2>$null;" ^
  "    if ($LASTEXITCODE -eq 0 -and $resolved) { $exePath = ($resolved | Select-Object -First 1).Trim(); break }" ^
  "  } catch {}" ^
  "}" ^
  "if (-not $exePath) { Write-Host '[ERROR] 没有找到可用的 Python，可先安装 Python 3。'; exit 1 }" ^
  "$homeDir = Split-Path -Path $exePath -Parent;" ^
  "$updated = $false;" ^
  "for ($i = 0; $i -lt $lines.Count; $i++) {" ^
  "  if ($lines[$i] -match '^\s*home\s*=') { $lines[$i] = 'home = ' + $homeDir; $updated = $true; break }" ^
  "}" ^
  "if (-not $updated) { $lines = @('home = ' + $homeDir) + $lines }" ^
  "Set-Content -LiteralPath $cfg -Value $lines -Encoding UTF8;" ^
  "Write-Host ('[OK] pyvenv.cfg 已更新: home = ' + $homeDir)"

if errorlevel 1 exit /b 1
exit /b 0
