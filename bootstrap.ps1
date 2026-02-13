param(
  [Parameter(Mandatory=$true)][string]$Root
)

$ErrorActionPreference = 'Stop'
$dataDir = Join-Path $Root 'data'
$log = Join-Path $dataDir 'run.log'
$stateFile = Join-Path $dataDir 'env_state.json'
New-Item -ItemType Directory -Path $dataDir -Force | Out-Null

function Log([string]$msg) {
  Add-Content $log ("[" + (Get-Date) + "] " + $msg)
}

function Show-Err([string]$title, [string]$msg) {
  try {
    Log ("error: " + $title + " " + $msg)
    Add-Type -AssemblyName System.Windows.Forms | Out-Null
    [System.Windows.Forms.MessageBox]::Show($msg, $title, [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error) | Out-Null
  } catch {
  }
}

function Show-Info([string]$title, [string]$msg) {
  try {
    Log ("info: " + $title + " " + $msg)
    Add-Type -AssemblyName System.Windows.Forms | Out-Null
    [System.Windows.Forms.MessageBox]::Show($msg, $title, [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null
  } catch {
  }
}

function Save-State([string]$status, [string]$python, [string]$message='') {
  try {
    $payload = [ordered]@{
      status = $status
      python = $python
      message = $message
      updatedAt = (Get-Date).ToString('s')
    }
    $payload | ConvertTo-Json | Set-Content -Path $stateFile -Encoding UTF8
  } catch {
    Log 'warn: failed writing env_state.json'
  }
}

function Find-SystemPython {
  $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
  if ($pyLauncher) {
    foreach ($ver in @('3.12', '3.11', '3.10', '3')) {
      try {
        $out = & $pyLauncher.Source "-$ver" -c "import sys;print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) {
          return @{ path = $pyLauncher.Source; launcherArgs = @("-$ver"); display = ($out | Select-Object -First 1).Trim() }
        }
      } catch {
      }
    }
  }

  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) {
    try {
      $ok = & $python.Source -c "import sys; assert sys.version_info >= (3,10); print(sys.executable)" 2>$null
      if ($LASTEXITCODE -eq 0) {
        return @{ path = $python.Source; launcherArgs = @(); display = ($ok | Select-Object -First 1).Trim() }
      }
    } catch {
    }
  }
  return $null
}

function Test-VenvHealthy([string]$VenvPy) {
  if (!(Test-Path $VenvPy)) { return $false }

  $pyvenvCfg = Join-Path (Split-Path -Parent (Split-Path -Parent $VenvPy)) 'pyvenv.cfg'
  if (!(Test-Path $pyvenvCfg)) { return $false }

  try {
    $homeLine = Select-String -Path $pyvenvCfg -Pattern '^home\s*=\s*(.+)$' -CaseSensitive:$false | Select-Object -First 1
    if ($homeLine) {
      $homePath = $homeLine.Matches[0].Groups[1].Value.Trim()
      if ($homePath -and !(Test-Path $homePath)) {
        Log ("venv invalid: pyvenv home not found -> " + $homePath)
        return $false
      }
    }
  } catch {
    return $false
  }

  $probe = @(
    'import fastapi',
    'import uvicorn',
    'import apscheduler',
    'import psutil',
    'import pystray',
    'from PIL import Image'
  ) -join '; '

  try {
    & $VenvPy -c $probe 2>$null
    return ($LASTEXITCODE -eq 0)
  } catch {
    return $false
  }
}

function Install-Requirements([string]$VenvPy) {
  $req = Join-Path $Root 'requirements.txt'
  if (!(Test-Path $req)) {
    throw 'requirements.txt 不存在。'
  }

  Log 'install: upgrade pip'
  & $VenvPy -m pip install --disable-pip-version-check -U pip
  if ($LASTEXITCODE -ne 0) { throw 'pip 升级失败。' }

  for ($i = 1; $i -le 2; $i++) {
    Log ("install: requirements attempt=" + $i)
    & $VenvPy -m pip install --disable-pip-version-check -r $req
    if ($LASTEXITCODE -eq 0) { return }
    Start-Sleep -Seconds 1
  }
  throw '依赖安装失败，请检查网络或 Python/pip 环境。'
}

try {
  Log 'start'

  $venv = Join-Path $Root '.venv'
  $venvPy = Join-Path $venv 'Scripts\python.exe'
  $venvPyw = Join-Path $venv 'Scripts\pythonw.exe'
  $firstLaunch = !(Test-Path $stateFile)

  if ($firstLaunch) {
    Show-Info 'HTWallpaper 首次启动' '检测到首次启动，正在自动检测 Python 并初始化运行环境，请稍候。'
  }

  $venvHealthy = Test-VenvHealthy -VenvPy $venvPy
  if (!$venvHealthy) {
    Log 'bootstrap: venv missing or unhealthy, rebuilding'

    if (Test-Path $venv) {
      Remove-Item -Path $venv -Recurse -Force -ErrorAction SilentlyContinue
    }

    $python = Find-SystemPython
    if (!$python) {
      Save-State -status 'failed' -python '' -message 'python_not_found'
      Show-Err 'HTWallpaper 初始化失败' '未检测到可用的 Python 3.10+。请安装 Python（勾选 Add to PATH）后重新打开。'
      exit 1
    }

    New-Item -ItemType Directory -Path $venv -Force | Out-Null
    Log ("bootstrap: using python=" + $python.display)

    & $python.path @($python.launcherArgs + @('-m', 'venv', $venv))
    if ($LASTEXITCODE -ne 0 -or !(Test-Path $venvPy)) {
      Save-State -status 'failed' -python $python.display -message 'venv_create_failed'
      Show-Err 'HTWallpaper 初始化失败' '创建虚拟环境失败，请确认 Python 安装完整后重试。'
      exit 1
    }

    Install-Requirements -VenvPy $venvPy

    if (!(Test-VenvHealthy -VenvPy $venvPy)) {
      Save-State -status 'failed' -python $python.display -message 'deps_check_failed'
      Show-Err 'HTWallpaper 初始化失败' '依赖安装后校验未通过，请检查网络并重试。'
      exit 1
    }

    Save-State -status 'ready' -python $python.display -message 'bootstrap_ok'
    Log 'bootstrap ok'
  } else {
    Save-State -status 'ready' -python $venvPy -message 'reuse_venv'
    Log 'venv health ok, reuse existing environment'
  }

  if (!(Test-Path $venvPyw)) {
    $venvPyw = $venvPy
  }

  Log ("python=" + $venvPyw)
  $p = Start-Process -FilePath $venvPyw -ArgumentList @('-m','app.tray') -WorkingDirectory $Root -WindowStyle Hidden -PassThru
  Log ("pid=" + $p.Id)

  exit 0
} catch {
  $detail = ($_ | Out-String)
  try {
    Log 'exception:'
    Add-Content $log $detail
    Save-State -status 'failed' -python '' -message $_.Exception.Message
  } catch {
  }
  $msg = $_.Exception.Message
  Show-Err 'HTWallpaper 启动失败' ("初始化/启动失败：" + $msg + "`n`n已自动打开 data\\run.log 以查看详情。")
  try {
    Start-Process -FilePath notepad.exe -ArgumentList @($log) | Out-Null
  } catch {
  }
  exit 1
}
