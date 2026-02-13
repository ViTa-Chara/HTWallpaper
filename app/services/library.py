from __future__ import annotations

import pathlib
import shutil
from typing import Iterable

from fastapi import UploadFile

from .video_store import VideoStore
from .wallpaper import WallpaperService


class VideoLibrary:
    def __init__(self, videos_dir: pathlib.Path, video_store: VideoStore) -> None:
        self.videos_dir = videos_dir
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.video_store = video_store

    def set_videos_dir(self, videos_dir: pathlib.Path) -> None:
        self.videos_dir = videos_dir
        self.videos_dir.mkdir(parents=True, exist_ok=True)

    def save_uploads(self, files: Iterable[UploadFile]) -> list[pathlib.Path]:
        saved: list[pathlib.Path] = []
        for file in files:
            target = self.videos_dir / pathlib.Path(file.filename or "upload.mp4").name
            with target.open("wb") as handle:
                shutil.copyfileobj(file.file, handle)
            saved.append(target)
            self.video_store.add(target)
        return saved

    def list_videos(self) -> list[pathlib.Path]:
        self.video_store.sync_from_directory(self.videos_dir)
        return self.video_store.list_paths()

    def extract_frames(
        self,
        wallpaper_service: WallpaperService,
        rule: str,
        interval_minutes: int | None,
        tones: list[str] | None,
        random_count: int,
        max_frames: int,
    ) -> dict:
        videos = self.list_videos()
        if not videos:
            return {"ok": False, "message": "没有可用视频"}
        results = []
        for video in videos:
            frames = wallpaper_service.extract_frames(
                video,
                rule=rule,
                interval_minutes=interval_minutes,
                tones=tones,
                random_count=random_count,
                max_frames=max_frames,
            )
            results.append({"video": video.name, "frames": frames})
        return {"ok": True, "results": results}
