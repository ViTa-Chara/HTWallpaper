from __future__ import annotations

import json
import pathlib


class SettingsStore:
    def __init__(self, json_path: pathlib.Path) -> None:
        self.json_path = json_path
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.json_path.exists():
            self.json_path.write_text("{}", encoding="utf-8")

    def get_limit(self, default_value: int = 60) -> int:
        data = self._load()
        value = data.get("frame_limit", default_value)
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return default_value

    def get_style(self, default_value: str = "fill") -> str:
        data = self._load()
        style = data.get("wallpaper_style", default_value)
        return str(style) if style else default_value

    def get_video_dir(self, default_value: pathlib.Path) -> pathlib.Path:
        data = self._load()
        raw_value = data.get("video_dir")
        if raw_value:
            return pathlib.Path(raw_value)
        return default_value

    def get_max_attempts(self, default_value: int = 40) -> int:
        data = self._load()
        value = data.get("max_attempts", default_value)
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return default_value

    def get_schedule_interval(self, default_value: int = 60) -> int:
        data = self._load()
        value = data.get("schedule_interval_minutes", default_value)
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return default_value

    def get_schedule_enabled(self, default_value: bool = False) -> bool:
        data = self._load()
        value = data.get("schedule_enabled", default_value)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    def get_multi_screen_enabled(self, default_value: bool = False) -> bool:
        data = self._load()
        value = data.get("multi_screen_enabled", default_value)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    def get_multi_screen_mode(self, default_value: str = "per_monitor_pywin32") -> str:
        data = self._load()
        mode = data.get("multi_screen_mode", default_value)
        return str(mode) if mode else default_value

    def get_span_layout(self, default_value: str = "auto") -> str:
        data = self._load()
        layout = data.get("span_layout", default_value)
        return str(layout) if layout else default_value

    def get_debug_mode(self, default_value: bool = False) -> bool:
        data = self._load()
        value = data.get("debug_mode", default_value)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    def get_schedule_tones(self, default_value: list[str] | None = None) -> list[str]:
        data = self._load()
        tones = data.get("schedule_tones", default_value or [])
        if not isinstance(tones, list):
            return default_value or []
        return [str(tone) for tone in tones if str(tone).strip()]

    def set_limit(self, value: int) -> None:
        data = self._load()
        data["frame_limit"] = max(1, int(value))
        self._save(data)

    def set_style(self, style: str) -> None:
        data = self._load()
        data["wallpaper_style"] = style
        self._save(data)

    def set_video_dir(self, video_dir: pathlib.Path) -> None:
        data = self._load()
        data["video_dir"] = str(video_dir)
        self._save(data)

    def set_max_attempts(self, value: int) -> None:
        data = self._load()
        data["max_attempts"] = max(1, int(value))
        self._save(data)

    def set_schedule_interval(self, value: int) -> None:
        data = self._load()
        data["schedule_interval_minutes"] = max(1, int(value))
        self._save(data)

    def set_schedule_enabled(self, value: bool) -> None:
        data = self._load()
        data["schedule_enabled"] = bool(value)
        self._save(data)

    def set_multi_screen_enabled(self, value: bool) -> None:
        data = self._load()
        data["multi_screen_enabled"] = bool(value)
        self._save(data)

    def set_multi_screen_mode(self, mode: str) -> None:
        data = self._load()
        data["multi_screen_mode"] = str(mode)
        self._save(data)

    def set_span_layout(self, layout: str) -> None:
        data = self._load()
        data["span_layout"] = str(layout)
        self._save(data)

    def set_debug_mode(self, value: bool) -> None:
        data = self._load()
        data["debug_mode"] = bool(value)
        self._save(data)

    def set_schedule_tones(self, tones: list[str] | None) -> None:
        data = self._load()
        cleaned = [str(tone).strip() for tone in (tones or []) if str(tone).strip()]
        data["schedule_tones"] = cleaned
        self._save(data)

    def dump(self) -> dict:
        return self._load()

    def _load(self) -> dict:
        try:
            return json.loads(self.json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _save(self, data: dict) -> None:
        self.json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
