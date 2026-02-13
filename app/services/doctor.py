from __future__ import annotations

import pathlib
import platform
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class DoctorIssue:
    id: str
    title: str
    severity: str
    details: str
    fix: str


class DoctorService:
    def __init__(self, base_dir: pathlib.Path, data_dir: pathlib.Path) -> None:
        self.base_dir = base_dir
        self.data_dir = data_dir

    def run(self) -> dict:
        issues: list[DoctorIssue] = []

        issues.extend(self._check_python_version())
        issues.extend(self._check_running_interpreter_location())
        issues.extend(self._check_data_dir_writable())
        issues.extend(self._check_venv_health())
        issues.extend(self._check_required_packages())
        issues.extend(self._check_ffmpeg())

        return {
            "ok": not issues,
            "issues": [issue.__dict__ for issue in issues],
            "platform": platform.system().lower(),
            "python": sys.executable,
        }

    def _check_python_version(self) -> list[DoctorIssue]:
        major, minor = sys.version_info[:2]
        if (major, minor) >= (3, 10):
            return []
        return [
            DoctorIssue(
                id="python_too_old",
                title="Python 版本过低",
                severity="error",
                details=f"当前版本: {major}.{minor}，建议 >= 3.10",
                fix="请安装 Python 3.10+ 并勾选 Add to PATH，然后按引导重建 .venv。",
            )
        ]

    def _check_running_interpreter_location(self) -> list[DoctorIssue]:
        venv_dir = self.base_dir / ".venv"
        if not venv_dir.exists():
            return []
        exe = pathlib.Path(sys.executable).resolve()
        try:
            in_venv = venv_dir.resolve() in exe.parents
        except OSError:
            in_venv = False
        if in_venv:
            return []
        return [
            DoctorIssue(
                id="not_running_in_venv",
                title="当前未使用项目 .venv 启动",
                severity="warning",
                details=f"当前 Python: {exe}\n期望使用: {venv_dir}",
                fix=(
                    "建议使用项目自带启动脚本（Windows: run.bat / run.vbs）启动。\n"
                    "如果 .venv 已损坏，请按“重建虚拟环境”的步骤重新安装依赖。"
                ),
            )
        ]

    def _check_data_dir_writable(self) -> list[DoctorIssue]:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        probe = self.data_dir / ".write_test"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return []
        except OSError as exc:
            return [
                DoctorIssue(
                    id="data_dir_not_writable",
                    title="数据目录不可写",
                    severity="error",
                    details=f"无法写入: {self.data_dir} ({exc})",
                    fix=(
                        "1) 把整个程序文件夹移动到不需要管理员权限的位置（例如 D:\\Apps 或你的桌面）。\n"
                        "2) 确保 data 文件夹未被杀毒/权限策略阻止。"
                    ),
                )
            ]

    def _check_venv_health(self) -> list[DoctorIssue]:
        venv_dir = self.base_dir / ".venv"
        pyvenv_cfg = venv_dir / "pyvenv.cfg"
        if not venv_dir.exists():
            return [
                DoctorIssue(
                    id="venv_missing",
                    title="未找到 .venv 虚拟环境",
                    severity="warning",
                    details="程序目录下缺少 .venv。压缩包分发时不建议直接携带虚拟环境。",
                    fix=self._fix_recreate_venv(),
                )
            ]

        if not pyvenv_cfg.exists():
            return [
                DoctorIssue(
                    id="pyvenv_cfg_missing",
                    title="虚拟环境配置缺失 (pyvenv.cfg)",
                    severity="error",
                    details=f"未找到: {pyvenv_cfg}",
                    fix=self._fix_recreate_venv(),
                )
            ]

        home = self._read_pyvenv_home(pyvenv_cfg)
        if home and not pathlib.Path(home).exists():
            return [
                DoctorIssue(
                    id="pyvenv_home_invalid",
                    title="虚拟环境已失效（pyvenv.cfg 指向旧机器）",
                    severity="error",
                    details=f"pyvenv.cfg 的 home= 指向不存在路径: {home}",
                    fix=self._fix_recreate_venv(),
                )
            ]

        system = platform.system().lower()
        if system == "windows":
            python_exec = venv_dir / "Scripts" / "python.exe"
        else:
            python_exec = venv_dir / "bin" / "python3"
            if not python_exec.exists():
                python_exec = venv_dir / "bin" / "python"
        if not python_exec.exists():
            return [
                DoctorIssue(
                    id="venv_python_missing",
                    title="虚拟环境解释器缺失",
                    severity="error",
                    details=f"未找到虚拟环境解释器: {python_exec}",
                    fix=self._fix_recreate_venv(),
                )
            ]
        return []

    def _check_required_packages(self) -> list[DoctorIssue]:
        required = [
            "fastapi",
            "uvicorn",
            "apscheduler",
            "psutil",
            "pystray",
            "PIL",
        ]
        if platform.system().lower() == "windows":
            required.append("win32com")

        code = (
            "import importlib; "
            + "; ".join([f"importlib.import_module('{name}')" for name in required])
        )
        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            return [
                DoctorIssue(
                    id="python_unusable",
                    title="当前 Python 无法运行",
                    severity="error",
                    details=str(exc),
                    fix="安装/修复 Python 后重试。建议安装 Python 3.10+，并勾选 Add to PATH。",
                )
            ]
        if result.returncode == 0:
            return []
        stderr = (result.stderr or result.stdout or "").strip()
        return [
            DoctorIssue(
                id="deps_missing",
                title="依赖包缺失或损坏",
                severity="error",
                details=stderr[:1500],
                fix=self._fix_install_deps(),
            )
        ]

    def _check_ffmpeg(self) -> list[DoctorIssue]:
        missing = []
        for tool in ("ffmpeg", "ffprobe"):
            try:
                result = subprocess.run(
                    [tool, "-version"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    missing.append(tool)
            except OSError:
                missing.append(tool)
        if not missing:
            return []
        return [
            DoctorIssue(
                id="ffmpeg_missing",
                title="未检测到 FFmpeg",
                severity="warning",
                details=f"缺少命令: {', '.join(sorted(set(missing)))}（用于从视频截取帧）",
                fix=(
                    "1) 安装 FFmpeg，并确保 ffmpeg/ffprobe 在 PATH 中。\n"
                    "2) 重新打开本应用后再试。\n"
                    "Windows 快速验证：在 cmd 里运行 `ffmpeg -version`。"
                ),
            )
        ]

    def _read_pyvenv_home(self, cfg_path: pathlib.Path) -> str | None:
        try:
            for line in cfg_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.strip().lower().startswith("home") and "=" in line:
                    return line.split("=", 1)[1].strip()
        except OSError:
            return None
        return None

    def _fix_recreate_venv(self) -> str:
        system = platform.system().lower()
        if system == "windows":
            return (
                "建议删除 .venv 后重建（虚拟环境不能跨机器复制）：\n"
                "1) 安装 Python 3.10+（勾选 Add to PATH）\n"
                "2) 在程序根目录打开 PowerShell：\n"
                "   - `python -m venv .venv`\n"
                "   - `./.venv/Scripts/python -m pip install -U pip`\n"
                "   - `./.venv/Scripts/pip install -r requirements.txt`\n"
                "3) 再次运行 run.bat"
            )
        return (
            "建议删除 .venv 后重建：\n"
            "1) `python3 -m venv .venv`\n"
            "2) `./.venv/bin/python -m pip install -U pip`\n"
            "3) `./.venv/bin/pip install -r requirements.txt`"
        )

    def _fix_install_deps(self) -> str:
        system = platform.system().lower()
        if system == "windows":
            return (
                "在程序根目录打开 PowerShell 执行：\n"
                "- `./.venv/Scripts/python -m pip install -U pip`\n"
                "- `./.venv/Scripts/pip install -r requirements.txt`\n"
                "如果没有 .venv，请先按“重建虚拟环境”的步骤执行。"
            )
        return (
            "在程序根目录执行：\n"
            "- `./.venv/bin/python -m pip install -U pip`\n"
            "- `./.venv/bin/pip install -r requirements.txt`"
        )
