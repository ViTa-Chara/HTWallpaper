# fix.ps1 - Auto-detect Python and update pyvenv.cfg
$ErrorActionPreference = 'Stop'
$cfg = Join-Path $PSScriptRoot '.venv\pyvenv.cfg'

if (-not (Test-Path -LiteralPath $cfg)) {
    Write-Host '[ERROR] pyvenv.cfg not found. Please create virtual environment first.'
    exit 1
}

$lines = Get-Content -LiteralPath $cfg -Encoding UTF8

# Get target version from pyvenv.cfg
$versionLine = $lines | Where-Object { $_ -match '^\s*version\s*=\s*' } | Select-Object -First 1
$targetVersion = $null
if ($versionLine -match '([0-9]+\.[0-9]+)') {
    $targetVersion = $Matches[1]
}

# Build candidate list
$candidates = @()
if ($targetVersion) {
    $candidates += @("py -$targetVersion", "python$($targetVersion.Replace('.',''))", "python$targetVersion")
}
$candidates += @('py -3', 'python3', 'python')

# Find available Python
$exePath = $null
foreach ($candidate in $candidates) {
    $parts = $candidate -split '\s+'
    $cmd = $parts[0]
    $args = @()
    if ($parts.Length -gt 1) {
        $args = $parts[1..($parts.Length-1)]
    }
    try {
        $resolved = & $cmd @args -c 'import sys; print(sys.executable)' 2>$null
        if ($LASTEXITCODE -eq 0 -and $resolved) {
            $exePath = ($resolved | Select-Object -First 1).Trim()
            break
        }
    } catch {}
}

if (-not $exePath) {
    Write-Host '[ERROR] No Python found. Please install Python 3 first.'
    exit 1
}

# Get actual Python version
$actualVersion = $null
try {
    $result = Start-Process -FilePath $exePath -ArgumentList @('--version') -NoNewWindow -Wait -RedirectStandardOutput "$env:TEMP\pyver.txt" -PassThru
    if ($result.ExitCode -eq 0) {
        $verOutput = (Get-Content "$env:TEMP\pyver.txt" -Raw).Trim()
        if ($verOutput -match 'Python\s+([0-9]+\.[0-9]+)') {
            $actualVersion = $Matches[1]
        }
    }
    Remove-Item "$env:TEMP\pyver.txt" -ErrorAction SilentlyContinue
} catch {}

$homeDir = Split-Path -Path $exePath -Parent

# Update lines
$updatedHome = $false
$updatedVersion = $false
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^\s*home\s*=') {
        $lines[$i] = "home = $homeDir"
        $updatedHome = $true
    }
    if ($lines[$i] -match '^\s*version\s*=') {
        if ($actualVersion) {
            $lines[$i] = "version = $actualVersion"
            $updatedVersion = $true
        }
    }
}

if (-not $updatedHome) {
    $lines = @("home = $homeDir") + $lines
}

# Save
Set-Content -LiteralPath $cfg -Value $lines -Encoding UTF8
Write-Host "[OK] pyvenv.cfg updated: home = $homeDir"
if ($actualVersion) {
    Write-Host "[OK] version = $actualVersion"
}
