from __future__ import annotations

import pathlib
import platform
import subprocess
import sys
import traceback
import time
import urllib.parse
import urllib.request
import webbrowser

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pystray
    from PIL import Image


def _log(root: pathlib.Path, message: str) -> None:
    log_path = root / "data" / "tray.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def _show_error(title: str, message: str) -> None:
    if platform.system().lower() != "windows":
        return
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
    except Exception:
        return


def _create_icon(root: pathlib.Path) -> "Image.Image":
    from PIL import Image, ImageDraw

    icon_path = root / "HTW.ico"
    if icon_path.exists():
        _log(root, f"[tray] load icon: {icon_path}")
        return Image.open(icon_path)
    image = Image.new("RGB", (64, 64), "#f1efe9")
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 54, 54), fill="#c24b26")
    draw.rectangle((18, 18, 46, 46), fill="#fdf6e3")
    return image


def _start_server(root: pathlib.Path) -> subprocess.Popen:
    system = platform.system().lower()
    if system == "windows":
        python_exec = root / ".venv" / "Scripts" / "python.exe"
    else:
        python_exec = root / ".venv" / "bin" / "python3"
        if not python_exec.exists():
            python_exec = root / ".venv" / "bin" / "python"
    if not python_exec.exists():
        python_exec = pathlib.Path(sys.executable)
    _log(root, f"[tray] start server using: {python_exec}")
    log_path = root / "data" / "server.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(python_exec),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8787",
    ]
    popen_kwargs = {
        "cwd": str(root),
        "stdout": log_path.open("a", encoding="utf-8"),
        "stderr": log_path.open("a", encoding="utf-8"),
    }
    if system == "windows":
        popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.Popen(
        command,
        **popen_kwargs,
    )


def main() -> None:
    root = pathlib.Path(__file__).resolve().parents[1]
    _log(root, "[tray] starting")

    try:
        from .services.doctor import DoctorService

        doctor = DoctorService(root, root / "data")
        report = doctor.run()
        issues = report.get("issues") or []
        critical = [item for item in issues if item.get("severity") == "error"]
        if critical:
            merged = "\n\n".join(
                [
                    f"{item.get('title','')}\n{item.get('details','')}\n\n解决方案:\n{item.get('fix','')}"
                    for item in critical
                ]
            )
            _log(root, "[tray] doctor found critical issues")
            _show_error("HTWallpaper 启动失败（环境问题）", merged[:3500])
            return
    except Exception:
        _log(root, "[tray] doctor failed")
        _log(root, traceback.format_exc())

    try:
        server = _start_server(root)
    except Exception:
        _log(root, "[tray] server start failed")
        _log(root, traceback.format_exc())
        _show_error(
            "HTWallpaper 启动失败",
            "服务启动失败。请检查 data/server.log 与 data/tray.log 获取详细错误。",
        )
        return

    def open_ui() -> None:
        webbrowser.open("http://127.0.0.1:8787")

    def change_wallpaper() -> None:
        url = "http://127.0.0.1:8787/api/apply"
        data = urllib.parse.urlencode({}).encode("utf-8")
        request = urllib.request.Request(url, data=data, method="POST")
        try:
            urllib.request.urlopen(request, timeout=3)
        except Exception:
            _log(root, "[tray] apply failed")

    def exit_app(icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        icon.stop()
        server.terminate()

    try:
        import pystray

        try:
            # Give the server a brief moment to start, then open UI once so the user
            # can confirm the app is running even if the tray icon is hidden.
            time.sleep(0.6)
            open_ui()
        except Exception:
            _log(root, "[tray] open ui failed")

        icon = pystray.Icon(
            "HTWallpaper",
            _create_icon(root),
            title="HTWallpaper",
            menu=pystray.Menu(
                pystray.MenuItem("打开界面", lambda: open_ui()),
                pystray.MenuItem("换一张", lambda: change_wallpaper()),
                pystray.MenuItem("退出", exit_app),
            ),
        )
        _log(root, "[tray] icon run")
        icon.run()
    except Exception:
        _log(root, "[tray] icon failed")
        detail = traceback.format_exc()
        _log(root, detail)
        _show_error(
            "HTWallpaper 托盘启动失败",
            ("托盘图标创建失败。\n\n" + detail)[:3500],
        )


if __name__ == "__main__":
    main()
