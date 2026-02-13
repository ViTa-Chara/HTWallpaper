from __future__ import annotations

import colorsys
import ctypes
import pathlib
import platform
import random
import subprocess
import time
from typing import Iterable

try:
    import winreg
except ImportError:  # pragma: no cover - non-Windows platforms
    winreg = None

try:
    import pythoncom
    import win32com.client
except ImportError:  # pragma: no cover - optional dependency
    pythoncom = None
    win32com = None

from .tones import ToneStore


class WallpaperService:
    def __init__(self, frames_dir: pathlib.Path, tone_store: ToneStore) -> None:
        self.frames_dir = frames_dir
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.tone_store = tone_store

    def extract_frames(
        self,
        video_path: pathlib.Path,
        rule: str,
        interval_minutes: int | None,
        tones: list[str] | None,
        random_count: int,
        max_frames: int,
    ) -> list[str]:
        output_dir = self.frames_dir / video_path.stem
        output_dir.mkdir(parents=True, exist_ok=True)

        if rule == "interval":
            if not interval_minutes:
                interval_minutes = 60
            frames = self._extract_interval(video_path, output_dir, interval_minutes)
            self._enforce_limit(max_frames)
            return frames
        if rule == "tone":
            frames = self._extract_tone(video_path, output_dir, tones, random_count)
            self._enforce_limit(max_frames)
            return frames
        if rule == "random":
            frames = self._extract_random(video_path, output_dir, random_count)
            self._enforce_limit(max_frames)
            return frames
        return []

    def set_wallpaper(self, image_path: pathlib.Path, style: str = "fill") -> tuple[bool, str]:
        if not image_path.exists():
            return False, "图片不存在"
        system = platform.system().lower()
        if system == "windows":
            return self._set_wallpaper_windows(image_path, style)
        if system == "darwin":
            return self._set_wallpaper_macos(image_path, style)
        return False, "不支持的操作系统"

    def set_wallpapers(
        self,
        image_paths: list[pathlib.Path],
        style: str = "fill",
        mode: str = "per_monitor_pywin32",
        span_layout: str = "auto",
    ) -> tuple[bool, str]:
        if not image_paths:
            return False, "图片不存在"
        if mode == "clone":
            return self.set_wallpaper(image_paths[0], style)
        if len(image_paths) == 1:
            return self.set_wallpaper(image_paths[0], style)
        system = platform.system().lower()
        if system == "windows":
            if mode == "span_mosaic":
                ok, message = self._set_wallpaper_windows_span_mosaic(
                    image_paths,
                    layout=span_layout,
                )
            elif mode == "per_monitor_ctypes":
                ok, message = self._set_wallpaper_windows_multi_ctypes(image_paths, style)
            else:
                ok, message = self._set_wallpaper_windows_multi(image_paths, style)
        elif system == "darwin":
            ok, message = self._set_wallpaper_macos_multi(image_paths, style)
        else:
            return False, "不支持的操作系统"

        if ok:
            return ok, message

        fallback_ok, fallback_message = self.set_wallpaper(image_paths[0], style)
        if fallback_ok:
            return True, f"多屏设置失败，已回退单屏: {message}"
        return False, message or fallback_message

    def _set_wallpaper_windows_multi_ctypes(
        self, image_paths: list[pathlib.Path], style: str
    ) -> tuple[bool, str]:
        try:
            ok = self._set_wallpaper_windows_per_monitor(image_paths, style=style)
            return ok, "ok" if ok else "设置失败"
        except Exception:
            return self._set_wallpaper_windows(image_paths[0], style)

    def _get_windows_monitor_rects(self) -> list[tuple[int, int, int, int]]:
        rects: list[tuple[int, int, int, int]] = []
        if platform.system().lower() != "windows":
            return rects

        if win32com is not None:
            try:
                pythoncom.CoInitialize()
                desktop = win32com.client.Dispatch("Microsoft.Windows.DesktopWallpaper")
                count = desktop.GetMonitorDevicePathCount()
                for idx in range(count):
                    monitor_id = desktop.GetMonitorDevicePathAt(idx)
                    left, top, right, bottom = desktop.GetMonitorRect(monitor_id)
                    rects.append((int(left), int(top), int(right), int(bottom)))
                return rects
            except Exception:
                return rects
            finally:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

        MONITORINFOF_PRIMARY = 0x1

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", ctypes.c_ulong),
            ]

        user32 = ctypes.windll.user32

        MONITORENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.POINTER(RECT),
            ctypes.c_long,
        )

        def _callback(hmonitor, hdc, lprect, lparam):
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
                r = info.rcMonitor
                rects.append((int(r.left), int(r.top), int(r.right), int(r.bottom)))
            return 1

        user32.EnumDisplayMonitors(0, 0, MONITORENUMPROC(_callback), 0)
        return rects

    def get_screen_count(self) -> int:
        system = platform.system().lower()
        if system == "windows":
            try:
                return max(1, int(ctypes.windll.user32.GetSystemMetrics(80)))
            except Exception:
                return 1
        if system == "darwin":
            count = self._get_macos_desktop_count()
            return max(1, count)
        return 1

    def pick_random_frames(
        self,
        video_paths: list[pathlib.Path],
        count: int,
        tones: list[str] | None,
        max_frames: int,
        attempts: int,
    ) -> list[pathlib.Path]:
        if not video_paths or count <= 0:
            return []
        frames: list[pathlib.Path] = []
        used: set[pathlib.Path] = set()
        retries = max(3, attempts)
        for _ in range(count):
            frame = None
            for _ in range(retries):
                video_path = random.choice(video_paths)
                candidate = self.extract_random_frame(
                    video_path,
                    tones,
                    max_frames=max_frames,
                    attempts=attempts,
                )
                if not candidate:
                    continue
                if candidate in used:
                    continue
                frame = candidate
                break
            if frame is None:
                for _ in range(retries):
                    video_path = random.choice(video_paths)
                    candidate = self.extract_random_frame(
                        video_path,
                        tones,
                        max_frames=max_frames,
                        attempts=attempts,
                    )
                    if candidate:
                        frame = candidate
                        break
            if frame:
                frames.append(frame)
                used.add(frame)
        return frames

    def pick_random_frame(
        self,
        tones: list[str] | None = None,
        video_names: list[str] | None = None,
    ) -> pathlib.Path | None:
        frames = self._collect_frames(video_names)
        if tones:
            frames = self.tone_store.filter_frames(frames, tones)
        if not frames:
            return None
        return random.choice(frames)

    def extract_random_frame(
        self,
        video_path: pathlib.Path,
        tones: list[str] | None,
        max_frames: int,
        attempts: int = 6,
    ) -> pathlib.Path | None:
        duration = self._get_duration(video_path)
        if duration <= 0:
            return None
        target_dir = self.frames_dir / "_live"
        target_dir.mkdir(parents=True, exist_ok=True)
        self._cleanup_temp(target_dir)
        tones = [tone.strip().lower() for tone in (tones or []) if tone.strip()]
        max_attempts = max(attempts, 1)
        if tones:
            for _ in range(max_attempts):
                position = random.uniform(0, duration)
                output_path = target_dir / f"live_{int(time.time() * 1000)}.jpg"
                command = [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    f"{position}",
                    "-i",
                    str(video_path),
                    "-frames:v",
                    "1",
                    str(output_path),
                ]
                subprocess.run(command, check=False, capture_output=True)
                if not output_path.exists():
                    continue
                tone = self._analyze_tone(output_path)
                if tone and tone.lower() in tones:
                    self.tone_store.set_tone(output_path, tone)
                    self._enforce_limit(max_frames)
                    return output_path
            tones = []
        for _ in range(max_attempts if not tones else 1):
            position = random.uniform(0, duration)
            output_path = target_dir / f"live_{int(time.time() * 1000)}.jpg"
            command = [
                "ffmpeg",
                "-y",
                "-ss",
                f"{position}",
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                str(output_path),
            ]
            subprocess.run(command, check=False, capture_output=True)
            if not output_path.exists():
                continue
            self._index_tones([output_path])
            self._enforce_limit(max_frames)
            return output_path
        return None

    def _collect_frames(self, video_names: list[str] | None) -> list[pathlib.Path]:
        if not video_names:
            return list(self.frames_dir.rglob("*.jpg"))
        frames: list[pathlib.Path] = []
        for name in video_names:
            frames.extend((self.frames_dir / pathlib.Path(name).stem).glob("*.jpg"))
        return frames

    def _cleanup_temp(self, target_dir: pathlib.Path, keep: int = 3) -> None:
        items = sorted(target_dir.glob("live_*.jpg"), key=lambda p: p.stat().st_mtime)
        for item in items[:-keep]:
            item.unlink(missing_ok=True)

    def _extract_interval(
        self, video_path: pathlib.Path, output_dir: pathlib.Path, interval_minutes: int
    ) -> list[str]:
        interval_seconds = interval_minutes * 60
        output_pattern = output_dir / "frame_%04d.jpg"
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            f"fps=1/{interval_seconds}",
            str(output_pattern),
        ]
        subprocess.run(command, check=False, capture_output=True)
        frames = list(output_dir.glob("frame_*.jpg"))
        self._index_tones(frames)
        return [p.name for p in frames]

    def _extract_random(
        self, video_path: pathlib.Path, output_dir: pathlib.Path, random_count: int
    ) -> list[str]:
        duration = self._get_duration(video_path)
        if duration <= 0:
            return []
        frames = []
        frame_paths: list[pathlib.Path] = []
        for idx in range(random_count):
            position = random.uniform(0, duration)
            output_path = output_dir / f"rand_{idx:03d}.jpg"
            command = [
                "ffmpeg",
                "-y",
                "-ss",
                f"{position}",
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                str(output_path),
            ]
            subprocess.run(command, check=False, capture_output=True)
            if output_path.exists():
                frame_paths.append(output_path)
                frames.append(output_path.name)
        self._index_tones(frame_paths)
        return frames

    def _extract_tone(
        self,
        video_path: pathlib.Path,
        output_dir: pathlib.Path,
        tones: list[str] | None,
        random_count: int,
    ) -> list[str]:
        tones = [tone.strip().lower() for tone in (tones or []) if tone.strip()]
        candidates = self._extract_random(video_path, output_dir, random_count or 6)
        if not tones:
            return candidates
        matched: list[str] = []
        for name in candidates:
            frame_path = output_dir / name
            frame_tone = self.tone_store.get_tone(frame_path) or ""
            if frame_tone.lower() in tones:
                matched.append(name)
        return matched

    def _enforce_limit(self, max_frames: int) -> None:
        if max_frames <= 0:
            return
        items = sorted(self.frames_dir.rglob("*.jpg"), key=lambda p: p.stat().st_mtime)
        if len(items) <= max_frames:
            return
        for item in items[: max(0, len(items) - max_frames)]:
            item.unlink(missing_ok=True)

    def _index_tones(self, frames: Iterable[pathlib.Path]) -> None:
        for frame in frames:
            tone = self._analyze_tone(frame)
            if tone:
                self.tone_store.set_tone(frame, tone)

    def _analyze_tone(self, frame_path: pathlib.Path) -> str | None:
        command = [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(frame_path),
            "-vf",
            "scale=1:1",
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ]
        result = subprocess.run(command, check=False, capture_output=True)
        if not result.stdout or len(result.stdout) < 3:
            return None
        r, g, b = result.stdout[0], result.stdout[1], result.stdout[2]
        return self._classify_tone(r, g, b)

    def _classify_tone(self, r: int, g: int, b: int) -> str:
        r_f, g_f, b_f = r / 255.0, g / 255.0, b / 255.0
        h, s, v = colorsys.rgb_to_hsv(r_f, g_f, b_f)
        if v < 0.15:
            return "dark"
        if s < 0.18:
            return "neutral"
        hue = h * 360
        if 15 <= hue < 40:
            return "orange"
        if 40 <= hue < 70:
            return "yellow"
        if 70 <= hue < 160:
            return "green"
        if 160 <= hue < 220:
            return "cyan"
        if 220 <= hue < 260:
            return "blue"
        if 260 <= hue < 300:
            return "purple"
        if 300 <= hue < 340:
            return "pink"
        return "red"

    def _apply_style(self, style: str) -> None:
        if winreg is None:
            return
        style_map = {
            "fill": ("10", "0"),
            "fit": ("6", "0"),
            "stretch": ("2", "0"),
            "tile": ("0", "1"),
            "center": ("0", "0"),
            "span": ("22", "0"),
        }
        wallpaper_style, tile_wallpaper = style_map.get(style, ("10", "0"))
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Control Panel\Desktop",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, wallpaper_style)
            winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, tile_wallpaper)

    def _set_wallpaper_windows(
        self, image_path: pathlib.Path, style: str
    ) -> tuple[bool, str]:
        self._apply_style(style)
        result = ctypes.windll.user32.SystemParametersInfoW(20, 0, str(image_path), 3)
        return bool(result), "ok" if result else "设置失败"

    def _set_wallpaper_windows_multi(
        self, image_paths: list[pathlib.Path], style: str
    ) -> tuple[bool, str]:
        self._apply_style(style)
        try:
            ok = self._set_wallpaper_windows_pywin32(image_paths)
            if ok:
                return True, "ok"
            ok = self._set_wallpaper_windows_per_monitor(image_paths)
            return ok, "ok" if ok else "设置失败"
        except Exception as exc:
            return self._set_wallpaper_windows(image_paths[0], style)

    def _set_wallpaper_windows_pywin32(self, image_paths: list[pathlib.Path]) -> bool:
        if pythoncom is None or win32com is None:
            return False
        pythoncom.CoInitialize()
        try:
            desktop = win32com.client.Dispatch("Microsoft.Windows.DesktopWallpaper")
            count = desktop.GetMonitorDevicePathCount()
            if count <= 0:
                return False
            for idx in range(count):
                monitor_id = desktop.GetMonitorDevicePathAt(idx)
                image_path = image_paths[idx % len(image_paths)]
                desktop.SetWallpaper(monitor_id, str(image_path))
            return True
        finally:
            pythoncom.CoUninitialize()

    def _set_wallpaper_windows_span_mosaic(
        self,
        image_paths: list[pathlib.Path],
        layout: str = "auto",
    ) -> tuple[bool, str]:
        try:
            from PIL import Image
        except ImportError:
            return False, "缺少 pillow"

        rects = self._get_windows_monitor_rects()
        if not rects:
            return False, "无法获取显示器信息"
        min_left = min(r[0] for r in rects)
        min_top = min(r[1] for r in rects)
        max_right = max(r[2] for r in rects)
        max_bottom = max(r[3] for r in rects)
        canvas_w = max(1, int(max_right - min_left))
        canvas_h = max(1, int(max_bottom - min_top))

        if layout != "auto" and len(rects) == 2:
            if layout in {"lr", "rl"}:
                rects = sorted(rects, key=lambda r: (r[0], r[1]))
                if layout == "rl":
                    rects = list(reversed(rects))
            elif layout == "tb":
                rects = sorted(rects, key=lambda r: (r[1], r[0]))

        mosaic = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
        for idx, rect in enumerate(rects):
            left, top, right, bottom = rect
            w = max(1, int(right - left))
            h = max(1, int(bottom - top))
            src_path = image_paths[idx % len(image_paths)]
            if not src_path.exists():
                continue
            try:
                img = Image.open(src_path).convert("RGB")
                resized = self._resize_cover(img, w, h)
                mosaic.paste(resized, (int(left - min_left), int(top - min_top)))
            except Exception:
                continue

        target_dir = self.frames_dir / "_mosaic"
        target_dir.mkdir(parents=True, exist_ok=True)
        out_path = target_dir / f"span_{int(time.time() * 1000)}.jpg"
        mosaic.save(out_path, format="JPEG", quality=92)

        return self._set_wallpaper_windows(out_path, style="span")

    def _resize_cover(self, image, width: int, height: int):
        scale = max(width / image.width, height / image.height)
        target_w = max(1, int(round(image.width * scale)))
        target_h = max(1, int(round(image.height * scale)))
        resized = image.resize((target_w, target_h), 1)
        left = max(0, (target_w - width) // 2)
        top = max(0, (target_h - height) // 2)
        right = left + width
        bottom = top + height
        return resized.crop((left, top, right, bottom))

    def _set_wallpaper_macos(
        self, image_path: pathlib.Path, style: str
    ) -> tuple[bool, str]:
        style_map = {
            "fill": "fill screen",
            "fit": "fit to screen",
            "stretch": "stretch to fill",
            "tile": "tiled",
            "center": "centered",
        }
        scaling = style_map.get(style, "fill screen")
        posix_path = image_path.expanduser().resolve().as_posix().replace('"', '\\"')
        script_lines = [
            'tell application "System Events"',
            f'set picture of every desktop to POSIX file "{posix_path}"',
            f'set picture scaling of every desktop to {scaling}',
            'end tell',
        ]
        command: list[str] = ["osascript"]
        for line in script_lines:
            command.extend(["-e", line])
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        ok = result.returncode == 0
        message = "ok" if ok else (result.stderr.strip() or result.stdout.strip() or "设置失败")
        return ok, message

    def _set_wallpaper_macos_multi(
        self, image_paths: list[pathlib.Path], style: str
    ) -> tuple[bool, str]:
        style_map = {
            "fill": "fill screen",
            "fit": "fit to screen",
            "stretch": "stretch to fill",
            "tile": "tiled",
            "center": "centered",
        }
        scaling = style_map.get(style, "fill screen")
        count = self._get_macos_desktop_count()
        if count <= 1:
            return self._set_wallpaper_macos(image_paths[0], style)
        script_lines = ['tell application "System Events"']
        for idx in range(1, count + 1):
            image_path = image_paths[(idx - 1) % len(image_paths)]
            posix_path = image_path.expanduser().resolve().as_posix().replace('"', '\\"')
            script_lines.append(
                f'set picture of desktop {idx} to POSIX file "{posix_path}"'
            )
            script_lines.append(
                f'set picture scaling of desktop {idx} to {scaling}'
            )
        script_lines.append('end tell')
        command: list[str] = ["osascript"]
        for line in script_lines:
            command.extend(["-e", line])
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        ok = result.returncode == 0
        message = "ok" if ok else (result.stderr.strip() or result.stdout.strip() or "设置失败")
        return ok, message

    def _get_macos_desktop_count(self) -> int:
        command = ["osascript", "-e", 'tell application "System Events" to count of desktops']
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        try:
            return int(result.stdout.strip())
        except (TypeError, ValueError):
            return 1

    def _set_wallpaper_windows_per_monitor(
        self,
        image_paths: list[pathlib.Path],
        style: str = "fill",
    ) -> bool:
        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", ctypes.c_ulong),
                ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort),
                ("Data4", ctypes.c_ubyte * 8),
            ]

            def __init__(self, value: str):
                import uuid

                guid = uuid.UUID(value)
                ctypes.Structure.__init__(self)
                self.Data1 = guid.time_low
                self.Data2 = guid.time_mid
                self.Data3 = guid.time_hi_version
                for idx, byte in enumerate(guid.bytes[8:]):
                    self.Data4[idx] = byte

        CLSID_DesktopWallpaper = GUID("{C2CF3110-460E-4FC1-B9D0-8A1C0C9CC4BD}")
        IID_IDesktopWallpaper = GUID("{B92B56A9-8B55-4E14-9A89-0199BBB6F93B}")

        ole32 = ctypes.OleDLL("ole32")
        CoInitializeEx = ole32.CoInitializeEx
        CoUninitialize = ole32.CoUninitialize
        CoCreateInstance = ole32.CoCreateInstance
        CoTaskMemFree = ole32.CoTaskMemFree

        COINIT_APARTMENTTHREADED = 0x2
        CLSCTX_INPROC_SERVER = 0x1

        position_map = {
            "center": 0,
            "tile": 1,
            "stretch": 2,
            "fit": 3,
            "fill": 4,
            "span": 5,
        }
        position_value = position_map.get(style, 4)

        hr_init = CoInitializeEx(None, COINIT_APARTMENTTHREADED)
        try:
            instance = ctypes.c_void_p()
            hr = CoCreateInstance(
                ctypes.byref(CLSID_DesktopWallpaper),
                None,
                CLSCTX_INPROC_SERVER,
                ctypes.byref(IID_IDesktopWallpaper),
                ctypes.byref(instance),
            )
            if hr != 0:
                return False

            vtable = ctypes.cast(instance, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
            QueryInterface = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(
                vtable[0]
            )
            Release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtable[2])
            SetWallpaper = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p)(
                vtable[3]
            )
            SetPosition = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_int)(
                vtable[10]
            )
            GetMonitorDevicePathAt = ctypes.WINFUNCTYPE(
                ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_wchar_p)
            )(vtable[5])
            GetMonitorDevicePathCount = ctypes.WINFUNCTYPE(
                ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)
            )(vtable[6])

            count = ctypes.c_uint()
            hr = GetMonitorDevicePathCount(instance, ctypes.byref(count))
            if hr != 0 or count.value == 0:
                Release(instance)
                return False

            SetPosition(instance, int(position_value))

            for idx in range(count.value):
                monitor_id = ctypes.c_wchar_p()
                hr = GetMonitorDevicePathAt(instance, idx, ctypes.byref(monitor_id))
                if hr != 0:
                    continue
                image_path = image_paths[idx % len(image_paths)]
                hr = SetWallpaper(instance, monitor_id, str(image_path))
                if hr != 0:
                    if monitor_id:
                        CoTaskMemFree(monitor_id)
                    Release(instance)
                    return False
                if monitor_id:
                    CoTaskMemFree(monitor_id)

            Release(instance)
            return True
        finally:
            CoUninitialize()

    def _get_duration(self, video_path: pathlib.Path) -> float:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        try:
            return float(result.stdout.strip())
        except ValueError:
            return 0.0
