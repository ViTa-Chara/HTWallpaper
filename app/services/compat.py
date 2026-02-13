from __future__ import annotations

import platform

import psutil


class CompatibilityService:
    def check(self) -> dict:
        system = platform.system().lower()
        if system != "windows":
            return {"ok": True, "conflicts": []}
        processes = {p.name().lower() for p in psutil.process_iter(["name"]) if p.info.get("name")}
        conflicts = [
            name
            for name in processes
            if name in {"wallpaper64.exe", "wallpaper32.exe", "bingwallpaper.exe"}
        ]
        return {"ok": not conflicts, "conflicts": conflicts}

    def safe_to_run(self) -> bool:
        return self.check().get("ok", False)
