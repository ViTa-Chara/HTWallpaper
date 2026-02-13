from __future__ import annotations

import json
import pathlib
from typing import Iterable


class ToneStore:
    def __init__(self, json_path: pathlib.Path, frames_dir: pathlib.Path) -> None:
        self.json_path = json_path
        self.frames_dir = frames_dir
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.json_path.exists():
            self.json_path.write_text("{}", encoding="utf-8")

    def set_tone(self, frame_path: pathlib.Path, tone: str) -> None:
        data = self._load()
        key = self._normalize_key(frame_path)
        data[key] = tone
        self._save(data)

    def get_tone(self, frame_path: pathlib.Path) -> str | None:
        data = self._load()
        return data.get(self._normalize_key(frame_path))

    def filter_frames(self, frames: Iterable[pathlib.Path], tones: list[str]) -> list[pathlib.Path]:
        if not tones:
            return list(frames)
        data = self._load()
        tone_set = {tone.strip().lower() for tone in tones if tone.strip()}
        filtered = []
        for frame in frames:
            key = self._normalize_key(frame)
            if data.get(key, "").lower() in tone_set:
                filtered.append(frame)
        return filtered

    def _normalize_key(self, frame_path: pathlib.Path) -> str:
        try:
            return str(frame_path.relative_to(self.frames_dir)).replace("\\", "/")
        except ValueError:
            return frame_path.name

    def _load(self) -> dict:
        try:
            return json.loads(self.json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _save(self, data: dict) -> None:
        self.json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
