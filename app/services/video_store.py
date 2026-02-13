from __future__ import annotations

import json
import pathlib


class VideoStore:
    def __init__(self, json_path: pathlib.Path) -> None:
        self.json_path = json_path
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.json_path.exists():
            self.json_path.write_text("[]", encoding="utf-8")

    def add(self, video_path: pathlib.Path) -> None:
        data = self._load()
        record = {"name": video_path.name, "path": str(video_path)}
        if record not in data:
            data.append(record)
            self._save(data)

    def sync_from_directory(self, directory: pathlib.Path) -> None:
        data = self._load()
        known_paths = {item.get("path") for item in data}
        for video in directory.glob("*.*"):
            record = {"name": video.name, "path": str(video)}
            if record["path"] not in known_paths:
                data.append(record)
        self._save(data)

    def list_paths(self) -> list[pathlib.Path]:
        data = self._load()
        return [pathlib.Path(item["path"]) for item in data if item.get("path")]

    def list_records(self) -> list[dict]:
        data = self._load()
        return [item for item in data if item.get("path") and pathlib.Path(item["path"]).exists()]

    def remove(self, path: str) -> bool:
        data = self._load()
        next_data = [item for item in data if item.get("path") != path]
        if len(next_data) == len(data):
            return False
        self._save(next_data)
        return True

    def _load(self) -> list[dict]:
        try:
            return json.loads(self.json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def _save(self, data: list[dict]) -> None:
        self.json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
