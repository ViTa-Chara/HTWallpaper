# HTWallpaper

> **CN**：将本地视频自动抽帧并设置为桌面壁纸，支持立即切换、定时轮换、色调过滤、多屏模式与托盘启动。  
> **EN**: Automatically extracts frames from local videos and applies them as desktop wallpapers, with instant apply, scheduled rotation, tone filtering, multi-monitor modes, and tray startup.  
> **JP**: ローカル動画からフレームを自動抽出して壁紙に設定するツール。即時適用、定期切替、トーンフィルタ、マルチモニター、トレイ起動に対応。

---

## 1) Overview / 概要 / 概要

- **CN**：HTWallpaper 是一个基于 **FastAPI + 原生前端** 的轻量桌面壁纸管理工具。它会从视频随机或按规则截帧，并调用系统接口设置壁纸。  
- **EN**: HTWallpaper is a lightweight wallpaper manager built with **FastAPI + vanilla frontend**. It captures frames from videos (randomly or by rule) and applies them using OS wallpaper APIs.  
- **JP**: HTWallpaper は **FastAPI + 素のフロントエンド** で構成された軽量壁紙マネージャーです。動画からルールベース/ランダムでフレーム抽出し、OS API で壁紙を設定します。

### Core capabilities / 核心能力 / 主な機能

- 视频上传与管理 / Upload & manage videos / 動画の登録・管理
- 随机抽帧并立即应用 / Random frame + instant apply / ランダム抽出して即時適用
- 定时自动切换 / Scheduled wallpaper rotation / 定期自動切替
- 色调识别与筛选（红橙黄绿青蓝紫粉、灰、暗）/ Tone analysis and filtering / トーン解析とフィルタ
- 多屏模式（独立随机、跨屏拼接、克隆）/ Multi-monitor modes / マルチモニターモード
- 开机启动配置（Windows/macOS）/ Startup registration / 起動時自動開始設定
- 托盘运行（启动本地服务 + 打开 UI + 快速换图）/ Tray workflow / トレイ運用

---

## 2) Tech Stack / 技术栈 / 技術スタック

- **Backend**: FastAPI, Uvicorn, APScheduler
- **Frontend**: HTML + CSS + Vanilla JavaScript
- **Media processing**: FFmpeg
- **System integration**:
  - Windows: `ctypes`, `pywin32`, `winreg`, 任务计划
  - macOS: `osascript`, LaunchAgents
- **Python dependencies**: see `requirements.txt`

---

## 3) Project Structure / 目录结构 / ディレクトリ構成

```text
HTWallpaper/
├─ app/
│  ├─ main.py               # FastAPI 入口与 API
│  ├─ tray.py               # 托盘启动器
│  ├─ services/
│  │  ├─ wallpaper.py       # 抽帧、色调分析、设壁纸（含多屏）
│  │  ├─ scheduler.py       # 定时调度与开机启动配置
│  │  ├─ settings.py        # settings.json 读写
│  │  ├─ video_store.py     # videos.json 读写
│  │  ├─ tones.py           # tones.json 读写
│  │  ├─ library.py         # 上传与视频目录管理
│  │  └─ compat.py          # 兼容性检测（冲突进程）
│  └─ static/
│     ├─ index.html         # Web UI
│     ├─ app.js             # 前端交互逻辑
│     └─ styles.css         # 样式
├─ data/
│  ├─ videos.json           # 视频索引
│  ├─ tones.json            # 帧色调索引
│  ├─ settings.json         # 用户设置
│  └─ frames/               # 抽帧输出目录
├─ run.bat / run.command / run.vbs
├─ fix.bat / fix.command
└─ requirements.txt
```

---

## 4) Requirements / 环境要求 / 動作要件

### Required

- Python **3.10+** (recommended)
- **FFmpeg** available in PATH
- OS: Windows / macOS (Linux can run server/UI but wallpaper setting is not implemented)

### Optional but recommended

- Virtual environment (`.venv`)
- On Windows: `pywin32` for per-monitor APIs

---

## 5) Quick Start / 快速开始 / クイックスタート

### A. Create venv & install deps

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows PowerShell/CMD
pip install -r requirements.txt
```

### B. Start service (dev/manual)

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8787
# Windows: .venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8787
```

Open: `http://127.0.0.1:8787`

### C. Start with launcher scripts

- **Windows**: `run.bat` (admin-elevated launcher), or `run.vbs` (silent)
- **macOS/Linux**: `./run.command`

If virtualenv Python path is broken, use:

- **Windows**: `fix.bat`
- **macOS/Linux**: `./fix.command`

---

## 6) Feature Guide / 功能说明 / 機能ガイド

### Upload & Video Management

- Upload multiple video files via UI.
- Files are stored in configured `video_dir`; metadata synced to `data/videos.json`.
- Video list supports deletion.

### Apply Now

- Picks a random frame from available videos.
- Optional tone filtering.
- Applies wallpaper immediately.

### Schedule

- Enable periodic changes by interval (minutes).
- Supports tone-constrained randomization.
- Settings persist and are restored on next startup.

### Multi-monitor

- `per_monitor_pywin32`: independent random image per monitor (preferred on Windows).
- `per_monitor_ctypes`: fallback implementation.
- `span_mosaic`: builds a combined mosaic image and sets span wallpaper.
- `clone`: same image on all monitors.

### Startup Integration

- Windows: creates/deletes scheduled task `HTWallpaper`.
- macOS: creates/removes `~/Library/LaunchAgents/com.htwallpaper.app.plist`.

### Debug Mode

- When enabled in Settings, UI panels display JSON API responses for troubleshooting.

---

## 7) Configuration & Data / 配置与数据 / 設定とデータ

### `data/settings.json` (main keys)

- `frame_limit`: max number of stored frames
- `wallpaper_style`: `fill | fit | stretch | center | tile`
- `video_dir`: source video directory
- `max_attempts`: max retries when sampling tone-matched frames
- `schedule_enabled`: whether schedule is active
- `schedule_interval_minutes`: scheduler interval
- `schedule_tones`: tone filter list
- `multi_screen_enabled`: enable multi-monitor logic
- `multi_screen_mode`: multi-monitor mode
- `span_layout`: `auto | lr | rl | tb`
- `debug_mode`: show API JSON in UI

### Other data files

- `data/videos.json`: list of tracked videos
- `data/tones.json`: frame-tone index for filtering
- `data/frames/`: extracted JPG frames (`_live`, `_mosaic`, per-video folders)
- `data/*.log`: runtime logs (`server.log`, `tray.log`, etc.)

---

## 8) API Summary / API 概览 / API 一覧

Base URL: `http://127.0.0.1:8787`

- `GET /` - UI page
- `POST /api/upload` - upload videos (`files[]`)
- `GET /api/videos` - list videos
- `DELETE /api/videos?path=...` - delete one video
- `POST /api/extract` - rule-based extraction
- `POST /api/apply` - extract/apply immediately
- `POST /api/schedule` - start/stop scheduler
- `POST /api/startup` - configure startup behavior
- `GET /api/settings` - read settings
- `POST /api/settings` - update settings
- `GET /api/status` - compatibility + scheduler status

---

## 9) Platform Notes / 平台说明 / プラットフォーム注意

- **Windows**
  - Full feature support (including advanced multi-monitor modes).
  - Compatibility check reports known conflicting wallpaper processes.
- **macOS**
  - Wallpaper apply and startup supported via AppleScript + LaunchAgents.
  - Multi-desktop handled through `System Events` scripts.
- **Linux**
  - Server and UI can run, but wallpaper setting currently returns unsupported.

---

## 10) Troubleshooting / 故障排查 / トラブルシューティング

1. **FFmpeg not found / ffmpeg 不可用 / ffmpeg が見つからない**  
   Ensure `ffmpeg -version` works in terminal.

2. **No wallpaper changes / 壁纸未切换 / 壁紙が変わらない**  
   - Check `data/server.log` and `data/tray.log`.  
   - Verify video list is not empty and frame extraction succeeds.

3. **Startup not working / 开机启动失败 / 自動起動失敗**  
   - Windows: verify Task Scheduler has `HTWallpaper`.  
   - macOS: inspect LaunchAgent plist and `launchctl list`.

4. **Virtualenv path mismatch / 虚拟环境路径错误 / venv パス不整合**  
   Run `fix.bat` or `fix.command`.

---

## 11) Development / 开发说明 / 開発メモ

```bash
# Run backend with reload
uvicorn app.main:app --host 127.0.0.1 --port 8787 --reload

# Basic syntax check
python -m compileall app
```

---

## 12) License / 许可 / ライセンス

No explicit license file is currently included. If you plan to publish publicly, add a license (e.g., MIT) before wide distribution.
