from __future__ import annotations

import os
import pathlib
import platform
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse
import urllib.request
import webbrowser

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pystray
    from PIL import Image

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8787


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


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0


def _pick_server_port(host: str = "127.0.0.1", preferred: int = 8787) -> int:
    if not _port_open(host, preferred):
        return preferred

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _start_server(root: pathlib.Path, port: int) -> subprocess.Popen:
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
        SERVER_HOST,
        "--port",
        str(port),
    ]
    _log(root, f"[tray] start server command: {' '.join(command)}")
    popen_kwargs = {
        "cwd": str(root),
        "stdout": log_path.open("a", encoding="utf-8"),
        "stderr": log_path.open("a", encoding="utf-8"),
    }
    if system == "windows":
        popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.Popen(command, **popen_kwargs)


def _server_ready(port: int, timeout_seconds: float = 8.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=1):
                return True
        except Exception:
            time.sleep(0.2)
    return False




def _open_browser_url(root: pathlib.Path, url: str) -> bool:
    try:
        opened = webbrowser.open(url)
        _log(root, f"[tray] browser open via webbrowser: {opened}")
        if opened:
            return True
    except Exception:
        _log(root, "[tray] webbrowser.open failed")
        _log(root, traceback.format_exc())

    system = platform.system().lower()
    try:
        if system == "windows":
            os.startfile(url)
            _log(root, "[tray] browser open via os.startfile")
            return True
        if system == "darwin":
            subprocess.Popen(["open", url])
            _log(root, "[tray] browser open via open")
            return True
        subprocess.Popen(["xdg-open", url])
        _log(root, "[tray] browser open via xdg-open")
        return True
    except Exception:
        _log(root, "[tray] browser fallback open failed")
        _log(root, traceback.format_exc())
        return False

def main() -> None:
    root = pathlib.Path(__file__).resolve().parents[1]
    _log(root, "[tray] starting")
    server: subprocess.Popen | None = None
    server_port = _pick_server_port()
    guard = threading.Lock()
    _log(root, f"[tray] selected server port: {server_port}")

    def ensure_server(timeout_seconds: float = 8.0) -> bool:
        nonlocal server
        with guard:
            if _server_ready(server_port, timeout_seconds=1.2):
                return True

            should_start = server is None or server.poll() is not None
            if should_start:
                try:
                    server = _start_server(root, server_port)
                except Exception:
                    _log(root, "[tray] server start failed")
                    _log(root, traceback.format_exc())
                    return False
            if _server_ready(server_port, timeout_seconds=timeout_seconds):
                return True

            if server and server.poll() is not None:
                _log(root, f"[tray] server exited early with code: {server.poll()}")
            _log(root, "[tray] server not ready")
            return False

    if ensure_server(timeout_seconds=8.0):
        _log(root, "[tray] server ready")
    else:
        _log(root, "[tray] initial server start failed; will retry on demand")

    def open_ui(
        _icon: pystray.Icon | None = None, _item: pystray.MenuItem | None = None
    ) -> None:
        if not ensure_server(timeout_seconds=12.0):
            _log(root, "[tray] ui open blocked: server unavailable")
            return
        webbrowser.open(f"http://127.0.0.1:{server_port}")

    def change_wallpaper(
        _icon: pystray.Icon | None = None, _item: pystray.MenuItem | None = None
    ) -> None:
        if not ensure_server(timeout_seconds=8.0):
            _log(root, "[tray] apply blocked: server unavailable")
            return
        url = f"http://127.0.0.1:{server_port}/api/apply"
        data = urllib.parse.urlencode({}).encode("utf-8")
        request = urllib.request.Request(url, data=data, method="POST")
        try:
            urllib.request.urlopen(request, timeout=3)
        except Exception:
            _log(root, "[tray] apply failed")
            _log(root, traceback.format_exc())

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
                pystray.MenuItem(
                    "打开界面",
                    lambda icon, item: threading.Thread(
                        target=open_ui, args=(icon, item), daemon=True
                    ).start(),
                ),
                pystray.MenuItem(
                    "换一张",
                    lambda icon, item: threading.Thread(
                        target=change_wallpaper, args=(icon, item), daemon=True
                    ).start(),
                ),
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
