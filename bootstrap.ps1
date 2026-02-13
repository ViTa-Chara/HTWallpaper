param(
  [Parameter(Mandatory=$true)][string]$Root
)

$ErrorActionPreference = 'Stop'
$dataDir = Join-Path $Root 'data'
$log = Join-Path $dataDir 'run.log'
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

try {
  Log 'start'

  $venv = Join-Path $Root '.venv'
  $venvPy = Join-Path $venv 'Scripts\python.exe'
  $venvPyw = Join-Path $venv 'Scripts\pythonw.exe'

  if (!(Test-Path $venvPy)) {
    Log 'bootstrap: create venv'

    $pyCmd = (Get-Command python -ErrorAction SilentlyContinue).Source
    $usePyLauncher = $false
    if (!$pyCmd) {
      $pyCmd = (Get-Command py -ErrorAction SilentlyContinue).Source
      if ($pyCmd) {
        $usePyLauncher = $true
      }
    }

    if (!$pyCmd) {
      Show-Err 'HTWallpaper 初始化失败' '未检测到 Python。请安装 Python 3.10+（勾选 Add to PATH）后重试。'
      exit 1
    }

    if ($usePyLauncher) {
      & $pyCmd -3 -m venv $venv
    } else {
      & $pyCmd -m venv $venv
    }

    if (!(Test-Path $venvPy)) {
      Show-Err 'HTWallpaper 初始化失败' '虚拟环境创建后仍未找到 .venv\Scripts\python.exe'
      exit 1
    }

    & $venvPy -m pip install -U pip
    & $venvPy -m pip install -r (Join-Path $Root 'requirements.txt')

    Log 'bootstrap ok'
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
    Log "exception:"
    Add-Content $log $detail
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
