from __future__ import annotations

import pathlib
import random
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .services.library import VideoLibrary
from .services.wallpaper import WallpaperService
from .services.tones import ToneStore
from .services.scheduler import WallpaperScheduler
from .services.compat import CompatibilityService
from .services.video_store import VideoStore
from .services.settings import SettingsStore
from .services.doctor import DoctorService

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "app" / "static"

DATA_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="HTWallpaper")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

video_store = VideoStore(DATA_DIR / "videos.json")
video_library = VideoLibrary(DATA_DIR / "videos", video_store)
tone_store = ToneStore(DATA_DIR / "tones.json", DATA_DIR / "frames")
wallpaper_service = WallpaperService(DATA_DIR / "frames", tone_store)
compat_service = CompatibilityService()
wallpaper_scheduler = WallpaperScheduler(wallpaper_service, compat_service)
settings_store = SettingsStore(DATA_DIR / "settings.json")
video_library.set_videos_dir(settings_store.get_video_dir(DATA_DIR / "videos"))
doctor_service = DoctorService(BASE_DIR, DATA_DIR)


@app.on_event("startup")
def restore_schedule() -> None:
    if not settings_store.get_schedule_enabled():
        return
    style_value = settings_store.get_style()
    multi_screen_enabled = settings_store.get_multi_screen_enabled()
    multi_screen_mode = settings_store.get_multi_screen_mode()
    span_layout = settings_store.get_span_layout()
    wallpaper_scheduler.start(
        interval_minutes=settings_store.get_schedule_interval(),
        tones=settings_store.get_schedule_tones(),
        video_paths=video_library.list_videos(),
        max_frames=settings_store.get_limit(),
        max_attempts=settings_store.get_max_attempts(),
        style=style_value,
        multi_screen_enabled=multi_screen_enabled,
        multi_screen_mode=multi_screen_mode,
        span_layout=span_layout,
    )


def _parse_bool(value: bool | str) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/HTW.ico")
def favicon() -> FileResponse:
    return FileResponse(BASE_DIR / "HTW.ico")


@app.post("/api/upload")
def upload_videos(files: list[UploadFile] = File(...)) -> JSONResponse:
    saved = video_library.save_uploads(files)
    return JSONResponse({"saved": [str(s) for s in saved]})


@app.get("/api/videos")
def list_videos() -> JSONResponse:
    video_library.set_videos_dir(settings_store.get_video_dir(DATA_DIR / "videos"))
    video_store.sync_from_directory(video_library.videos_dir)
    return JSONResponse({"videos": video_store.list_records()})


@app.delete("/api/videos")
def delete_video(path: str) -> JSONResponse:
    removed = video_store.remove(path)
    file_path = pathlib.Path(path)
    video_dir = settings_store.get_video_dir(DATA_DIR / "videos")
    if removed and file_path.exists() and video_dir in file_path.parents:
        file_path.unlink(missing_ok=True)
    return JSONResponse({"ok": removed})


@app.post("/api/extract")
def extract_frames(
    rule: str = Form(...),
    interval_minutes: int | None = Form(default=None),
    tones: str | None = Form(default=None),
    random_count: int = Form(default=3),
) -> JSONResponse:
    videos = video_library.list_videos()
    if not videos:
        return JSONResponse({"ok": False, "message": "没有可用视频"})
    frames = []
    for video in videos:
        frames.extend(
            wallpaper_service.extract_frames(
                video,
                rule=rule,
                interval_minutes=interval_minutes,
                tones=_parse_list(tones),
                random_count=random_count,
                max_frames=settings_store.get_limit(),
            )
        )
    return JSONResponse({"ok": True, "frames": frames})


@app.post("/api/set")
def set_wallpaper(frame_name: str = Form(...)) -> JSONResponse:
    path = wallpaper_service.frames_dir / frame_name
    ok, message = wallpaper_service.set_wallpaper(path, settings_store.get_style())
    return JSONResponse({"ok": ok, "message": message})


@app.get("/api/status")
def get_status() -> JSONResponse:
    return JSONResponse(
        {
            "compat": compat_service.check(),
            "schedule": wallpaper_scheduler.status(),
        }
    )


@app.get("/api/doctor")
def doctor() -> JSONResponse:
    return JSONResponse(doctor_service.run())


@app.post("/api/schedule")
def schedule_wallpaper(
    enable: str = Form(...),
    interval_minutes: int = Form(default=60),
    tones: list[str] | None = Form(default=None),
    max_frames: int | None = Form(default=None),
    style: str | None = Form(default=None),
    multi_screen_enabled: bool | None = Form(default=None),
    multi_screen_mode: str | None = Form(default=None),
    span_layout: str | None = Form(default=None),
) -> JSONResponse:
    enable_flag = enable.lower() == "true"
    tone_list = tones or []
    frame_limit = max_frames or settings_store.get_limit()
    if enable_flag:
        style_value = style or settings_store.get_style()
        if multi_screen_enabled is None:
            multi_screen_enabled = settings_store.get_multi_screen_enabled()
        mode_value = multi_screen_mode or settings_store.get_multi_screen_mode()
        span_layout_value = span_layout or settings_store.get_span_layout()
        settings_store.set_style(style_value)
        settings_store.set_schedule_interval(interval_minutes)
        settings_store.set_schedule_enabled(True)
        settings_store.set_schedule_tones(tone_list)
        multi_screen_enabled_flag = _parse_bool(multi_screen_enabled)
        settings_store.set_multi_screen_enabled(multi_screen_enabled_flag)
        settings_store.set_multi_screen_mode(mode_value)
        settings_store.set_span_layout(span_layout_value)
        wallpaper_scheduler.start(
            interval_minutes=interval_minutes,
            tones=tone_list,
            video_paths=video_library.list_videos(),
            max_frames=frame_limit,
            max_attempts=settings_store.get_max_attempts(),
            style=style_value,
            multi_screen_enabled=multi_screen_enabled_flag,
            multi_screen_mode=mode_value,
            span_layout=span_layout_value,
        )
    else:
        settings_store.set_schedule_enabled(False)
        wallpaper_scheduler.stop()
    return JSONResponse({"ok": True, "schedule": wallpaper_scheduler.status()})


@app.post("/api/apply")
def apply_wallpaper(
    tones: list[str] | None = Form(default=None),
    max_frames: int | None = Form(default=None),
    style: str | None = Form(default=None),
) -> JSONResponse:
    videos = video_library.list_videos()
    if not videos:
        return JSONResponse({"ok": False, "message": "没有可用视频"})
    tone_list = tones or []
    frame_limit = max_frames or settings_store.get_limit()
    style_value = style or settings_store.get_style()
    settings_store.set_style(style_value)
    multi_screen_enabled = settings_store.get_multi_screen_enabled()
    if multi_screen_enabled:
        mode_value = settings_store.get_multi_screen_mode()
        span_layout_value = settings_store.get_span_layout()
        screen_count = wallpaper_service.get_screen_count()
        frames = wallpaper_service.pick_random_frames(
            videos,
            count=screen_count,
            tones=tone_list,
            max_frames=frame_limit,
            attempts=settings_store.get_max_attempts(),
        )
        if not frames:
            return JSONResponse({"ok": False, "message": "没有可用壁纸"})
        ok, message = wallpaper_service.set_wallpapers(
            frames,
            style_value,
            mode=mode_value,
            span_layout=span_layout_value,
        )
        return JSONResponse(
            {"ok": ok, "message": message, "frames": [f.name for f in frames]}
        )
    frame = None
    for video_path in random.sample(videos, len(videos)):
        frame = wallpaper_service.extract_random_frame(
            video_path,
            tone_list,
            max_frames=frame_limit,
            attempts=settings_store.get_max_attempts(),
        )
        if frame:
            break
    if not frame:
        return JSONResponse({"ok": False, "message": "没有可用壁纸"})
    ok, message = wallpaper_service.set_wallpaper(frame, style_value)
    return JSONResponse({"ok": ok, "message": message, "frame": frame.name})
@app.post("/api/startup")
def configure_startup(enable: bool = Form(...)) -> JSONResponse:
    ok, message = wallpaper_scheduler.configure_startup(enable)
    return JSONResponse({"ok": ok, "message": message})


@app.get("/api/settings")
def get_settings() -> JSONResponse:
    data = settings_store.dump()
    data.setdefault("video_dir", str(settings_store.get_video_dir(DATA_DIR / "videos")))
    data.setdefault("max_attempts", settings_store.get_max_attempts())
    data.setdefault("schedule_interval_minutes", settings_store.get_schedule_interval())
    data.setdefault("multi_screen_enabled", settings_store.get_multi_screen_enabled())
    data.setdefault("multi_screen_mode", settings_store.get_multi_screen_mode())
    data.setdefault("span_layout", settings_store.get_span_layout())
    data.setdefault("debug_mode", settings_store.get_debug_mode())
    return JSONResponse(data)


@app.post("/api/settings")
def update_settings(
    frame_limit: int = Form(...),
    wallpaper_style: str | None = Form(default=None),
    video_dir: str | None = Form(default=None),
    max_attempts: int | None = Form(default=None),
    multi_screen_enabled: bool | None = Form(default=None),
    multi_screen_mode: str | None = Form(default=None),
    span_layout: str | None = Form(default=None),
    debug_mode: bool | None = Form(default=None),
) -> JSONResponse:
    settings_store.set_limit(frame_limit)
    if wallpaper_style:
        settings_store.set_style(wallpaper_style)
    if video_dir:
        resolved_dir = pathlib.Path(video_dir).expanduser()
        resolved_dir.mkdir(parents=True, exist_ok=True)
        settings_store.set_video_dir(resolved_dir)
        video_library.set_videos_dir(resolved_dir)
        video_store.sync_from_directory(resolved_dir)
    if max_attempts is not None:
        settings_store.set_max_attempts(max_attempts)
    if multi_screen_enabled is not None:
        settings_store.set_multi_screen_enabled(_parse_bool(multi_screen_enabled))
    if multi_screen_mode is not None:
        settings_store.set_multi_screen_mode(multi_screen_mode)
    if span_layout is not None:
        settings_store.set_span_layout(span_layout)
    if debug_mode is not None:
        settings_store.set_debug_mode(_parse_bool(debug_mode))
    return JSONResponse(
        {
            "ok": True,
            "frame_limit": settings_store.get_limit(),
            "wallpaper_style": settings_store.get_style(),
            "video_dir": str(settings_store.get_video_dir(DATA_DIR / "videos")),
            "max_attempts": settings_store.get_max_attempts(),
            "multi_screen_enabled": settings_store.get_multi_screen_enabled(),
            "multi_screen_mode": settings_store.get_multi_screen_mode(),
            "span_layout": settings_store.get_span_layout(),
            "debug_mode": settings_store.get_debug_mode(),
        }
    )
