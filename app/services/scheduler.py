from __future__ import annotations

import pathlib
import platform
import plistlib
import random
import subprocess
import sys
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

from .compat import CompatibilityService
from .wallpaper import WallpaperService


class WallpaperScheduler:
    def __init__(
        self, wallpaper_service: WallpaperService, compat_service: CompatibilityService
    ) -> None:
        self.wallpaper_service = wallpaper_service
        self.compat_service = compat_service
        self.scheduler = BackgroundScheduler()
        self._job = None
        self._interval_minutes = None
        self._tag = None
        self._tones: list[str] | None = None
        self._max_frames: int = 60
        self._max_attempts: int = 40
        self._style: str = "fill"
        self._multi_screen_enabled: bool = False
        self._multi_screen_mode: str = "per_monitor_pywin32"
        self._span_layout: str = "auto"

    def start(
        self,
        interval_minutes: int,
        tones: list[str] | None,
        video_paths: list[pathlib.Path],
        max_frames: int,
        max_attempts: int,
        style: str,
        multi_screen_enabled: bool = False,
        multi_screen_mode: str = "per_monitor_pywin32",
        span_layout: str = "auto",
    ) -> None:
        self._interval_minutes = interval_minutes
        self._tones = tones
        self._max_frames = max_frames
        self._max_attempts = max_attempts
        self._style = style
        self._multi_screen_enabled = multi_screen_enabled
        self._multi_screen_mode = multi_screen_mode
        self._span_layout = span_layout
        if not self.scheduler.running:
            self.scheduler.start()
        if self._job:
            self._job.remove()
        self._job = self.scheduler.add_job(
            self._tick,
            "interval",
            minutes=interval_minutes,
            kwargs={"video_paths": video_paths},
            next_run_time=datetime.now(),
        )

    def stop(self) -> None:
        if self._job:
            self._job.remove()
            self._job = None

    def status(self) -> dict:
        return {
            "enabled": self._job is not None,
            "interval_minutes": self._interval_minutes,
            "tones": self._tones,
            "max_frames": self._max_frames,
            "max_attempts": self._max_attempts,
            "style": self._style,
            "multi_screen_enabled": self._multi_screen_enabled,
            "multi_screen_mode": self._multi_screen_mode,
            "span_layout": self._span_layout,
        }

    def configure_startup(self, enable: bool) -> tuple[bool, str]:
        system = platform.system().lower()
        if system == "windows":
            task_name = "HTWallpaper"
            base_dir = pathlib.Path(__file__).resolve().parents[2]
            pythonw = base_dir / ".venv" / "Scripts" / "pythonw.exe"
            if not pythonw.exists():
                pythonw = pathlib.Path(sys.executable)
            if enable:
                startup_cmd = (
                    f'cmd.exe /c "cd /d \"{base_dir}\" && '
                    f'\"{pythonw}\" -m app.tray"'
                )
                command = [
                    "schtasks",
                    "/Create",
                    "/F",
                    "/SC",
                    "ONLOGON",
                    "/RL",
                    "LIMITED",
                    "/TN",
                    task_name,
                    "/TR",
                    startup_cmd,
                ]
            else:
                command = ["schtasks", "/Delete", "/F", "/TN", task_name]
            result = subprocess.run(command, check=False, capture_output=True, text=True)
            ok = result.returncode == 0
            return ok, result.stdout.strip() or result.stderr.strip()
        if system == "darwin":
            base_dir = pathlib.Path(__file__).resolve().parents[2]
            python_exec = base_dir / ".venv" / "bin" / "python3"
            if not python_exec.exists():
                python_exec = base_dir / ".venv" / "bin" / "python"
            if not python_exec.exists():
                python_exec = pathlib.Path(sys.executable)
            label = "com.htwallpaper.app"
            launch_dir = pathlib.Path.home() / "Library" / "LaunchAgents"
            launch_dir.mkdir(parents=True, exist_ok=True)
            plist_path = launch_dir / f"{label}.plist"
            log_dir = base_dir / "data"
            log_dir.mkdir(parents=True, exist_ok=True)
            if enable:
                payload = {
                    "Label": label,
                    "ProgramArguments": [str(python_exec), "-m", "app.tray"],
                    "WorkingDirectory": str(base_dir),
                    "RunAtLoad": True,
                    "KeepAlive": True,
                    "StandardOutPath": str(log_dir / "tray.out.log"),
                    "StandardErrorPath": str(log_dir / "tray.err.log"),
                }
                with plist_path.open("wb") as handle:
                    plistlib.dump(payload, handle)
                command = ["launchctl", "load", "-w", str(plist_path)]
            else:
                if not plist_path.exists():
                    return True, "未配置启动项"
                command = ["launchctl", "unload", "-w", str(plist_path)]
            result = subprocess.run(command, check=False, capture_output=True, text=True)
            ok = result.returncode == 0
            if not enable and plist_path.exists():
                plist_path.unlink(missing_ok=True)
            return ok, result.stdout.strip() or result.stderr.strip()
        return False, "当前系统不支持开机启动配置"

    def _tick(self, video_paths: list[pathlib.Path]) -> None:
        if not self.compat_service.safe_to_run():
            return
        if not video_paths:
            return
        if self._multi_screen_enabled:
            screen_count = self.wallpaper_service.get_screen_count()
            frames = self.wallpaper_service.pick_random_frames(
                video_paths,
                count=screen_count,
                tones=self._tones,
                max_frames=self._max_frames,
                attempts=self._max_attempts,
            )
            if frames:
                self.wallpaper_service.set_wallpapers(
                    frames,
                    self._style,
                    mode=self._multi_screen_mode,
                    span_layout=self._span_layout,
                )
            return
        video_path = random.choice(video_paths)
        frame = self.wallpaper_service.extract_random_frame(
            video_path,
            self._tones,
            max_frames=self._max_frames,
            attempts=self._max_attempts,
        )
        if frame:
            self.wallpaper_service.set_wallpaper(frame, self._style)
