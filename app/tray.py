from __future__ import annotations

import pathlib
import platform
import subprocess
import sys
import time
import traceback
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


def _server_ready(timeout_seconds: float = 8.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8787/api/status", timeout=1):
                return True
        except Exception:
            time.sleep(0.2)
    return False


def main() -> None:
    root = pathlib.Path(__file__).resolve().parents[1]
    _log(root, "[tray] starting")
    server: subprocess.Popen | None = None
    if _server_ready(timeout_seconds=1.2):
        _log(root, "[tray] server already running")
    else:
        try:
            server = _start_server(root)
        except Exception:
            _log(root, "[tray] server start failed")
            _log(root, traceback.format_exc())
            return
        if not _server_ready():
            _log(root, "[tray] server not ready after start")

    def open_ui() -> None:
        if not _server_ready(timeout_seconds=1.2):
            _log(root, "[tray] ui open blocked: server unavailable")
            return
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
        if server and server.poll() is None:
            server.terminate()

    try:
        import pystray

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
        _log(root, traceback.format_exc())


if __name__ == "__main__":
    main()
