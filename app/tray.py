from __future__ import annotations

import pathlib
import platform
import subprocess
import sys
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


def _find_uv(root: pathlib.Path) -> str:
    """Find uv executable (system or local)."""
    # Check system uv
    result = subprocess.run(["uv", "--version"], capture_output=True)
    if result.returncode == 0:
        return "uv"
    # Check local uv
    system = platform.system().lower()
    if system == "windows":
        local_uv = root / ".uv" / "uv.exe"
    else:
        local_uv = root / ".uv" / "uv"
    if local_uv.exists():
        return str(local_uv)
    # Fallback to system uv
    return "uv"


def _start_server(root: pathlib.Path) -> subprocess.Popen:
    uv = _find_uv(root)
    _log(root, f"[tray] start server using: {uv}")
    log_path = root / "data" / "server.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        uv,
        "run",
        "--no-dev",
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
    system = platform.system().lower()
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
        server = _start_server(root)
    except Exception:
        _log(root, "[tray] server start failed")
        _log(root, traceback.format_exc())
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
