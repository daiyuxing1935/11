"""Persistent, project-shaped workspaces for the guided Agent labs.

The lab terminal behaves like a normal project terminal.  Its working directory
and virtual-environment state are persisted between requests so the browser UI
can offer the same workflow as a desktop IDE.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import queue
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path, PurePosixPath

from config import BASE_DIR
from services.agent_lab_specs import SPECS
from services.judge_service import get_flagship_exercise, judge_submission


WORKSPACE_ROOT = Path(BASE_DIR) / "data" / "lab_workspaces"
MAX_FILE_SIZE = 300_000
SKIP_PARTS = {".venv", "__pycache__", ".git", ".pytest_cache"}
TRACK_CONFIG = {
    "1": {
        "framework": "LangChain",
        "packages": ["langchain", "langchain-openai", "python-dotenv"],
        "imports": ["langchain", "langchain_openai"],
    },
    "2": {
        "framework": "LangChain",
        "packages": ["langchain", "langchain-openai", "python-dotenv"],
        "imports": ["langchain", "langchain_openai"],
    },
    "3": {
        "framework": "LangGraph",
        "packages": ["langgraph", "langchain"],
        "imports": ["langgraph"],
    },
    "4": {
        "framework": "LangChain + LangGraph",
        "packages": ["langchain", "langgraph", "python-dotenv"],
        "imports": ["langchain", "langgraph"],
    },
}


def _safe_part(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]", "-", str(value or ""))
    if not value:
        raise ValueError("工作区标识不能为空")
    return value[:80]


def _root(user_id: int, exercise_id: str) -> Path:
    if exercise_id not in SPECS:
        raise ValueError("未找到该实验项目")
    path = WORKSPACE_ROOT / f"user-{int(user_id)}" / _safe_part(exercise_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_path(root: Path, relative_path: str, *, allow_hidden: bool = True) -> Path:
    raw = str(relative_path or "").replace("\\", "/").strip("/")
    pure = PurePosixPath(raw)
    if not raw or pure.is_absolute() or ".." in pure.parts:
        raise ValueError("文件路径不合法")
    if len(pure.parts) > 64 or any(len(part) > 255 for part in pure.parts):
        raise ValueError("文件路径过深或名称过长")
    if not allow_hidden and any(part.startswith(".") for part in pure.parts):
        raise ValueError("该隐藏目录不可操作")
    resolved = (root / Path(*pure.parts)).resolve()
    if root.resolve() not in resolved.parents:
        raise ValueError("文件必须位于当前项目内")
    return resolved


def _course(exercise_id: str) -> dict:
    exercise = get_flagship_exercise(exercise_id) or {}
    track = TRACK_CONFIG[exercise_id.split("-", 1)[0]]
    spec = SPECS[exercise_id]
    targets = [spec.get("target")] if spec.get("target") else []
    if spec.get("mode") == "checkpoint":
        targets = ["save_checkpoint", "load_checkpoint"]

    implementation_steps = [str(item).strip() for item in exercise.get("steps", []) if str(item).strip()]
    implementation_hint = (
        f" 建议按这个顺序完成：{' → '.join(implementation_steps)}。"
        if implementation_steps else ""
    )
    test_count = max(len(spec.get("cases", [])) + int(spec.get("extra_cases", 0)), 4)
    integration_hint = ""
    if exercise_id == "1-1":
        integration_hint = " 把 build_chat_messages 的返回值传给 model.invoke()，让个性化系统指令真正进入模型上下文。"
    elif exercise_id == "1-3":
        integration_hint = " 必须遍历 model.stream()，并在循环内使用 flush=True 逐片段输出；不能等所有片段结束后一次性打印。"

    project_files = ["requirements.txt", ".env", "solution.py", "app.py"]
    stages = [
        {
            "id": "structure", "title": "搭好项目骨架", "icon": "FolderOpened",
            "instruction": "在项目中创建 requirements.txt、.env、solution.py 和 app.py，文件名必须完全一致。",
            "command": "tree", "checks": ["必需文件存在", "文件名大小写一致"],
        },
        {
            "id": "environment", "title": "创建虚拟环境", "icon": "Cpu",
            "instruction": "在终端执行 python -m venv .venv，让项目依赖与系统 Python 隔离。",
            "command": "python -m venv .venv", "checks": [".venv 已创建", "Python 版本可读取"],
        },
        {
            "id": "dependencies", "title": f"声明 {track['framework']} 依赖", "icon": "Box",
            "instruction": "把本项目需要的框架包写入 requirements.txt，再从终端安装。不要把 API Key 写进该文件。",
            "command": "pip install -r requirements.txt", "checks": [f"包含 {', '.join(track['packages'])}", "依赖已安装到当前虚拟环境"],
        },
        {
            "id": "implementation", "title": "完成核心模块", "icon": "EditPen",
            "instruction": f"在 solution.py 中真正实现 {', '.join(targets)}，不能只保留函数定义或占位语句。{implementation_hint}",
            "command": "", "test_count": test_count,
            "checks": ["Python 语法正确", "目标函数已定义", f"{test_count} 个业务测试点通过"],
        },
        {
            "id": "integration", "title": "接入可运行应用", "icon": "Connection",
            "instruction": f"在 app.py 中导入 solution，并接入 {track['framework']}。环境变量从 .env 读取，禁止把真实 Key 写进代码。{integration_hint}",
            "command": "python app.py", "checks": ["核心业务测试仍通过", "app.py 可解析", "框架调用方式正确", "没有疑似硬编码密钥"],
        },
        {
            "id": "acceptance", "title": "AI 工程验收", "icon": "CircleCheck",
            "instruction": "AI 助教将检查项目结构、环境、依赖、代码契约和服务端私有业务场景；全部通过后再进入能力答辩。",
            "command": "", "checks": ["前置阶段全部通过", "私有业务场景通过"],
        },
    ]
    return {
        "exercise_id": exercise_id,
        "title": exercise.get("title", exercise_id),
        "module": exercise.get("module", "Agent 工程实战"),
        "description": exercise.get("description", ""),
        "framework": track["framework"],
        "packages": track["packages"],
        "framework_imports": track["imports"],
        "targets": targets,
        "project_files": project_files,
        "starter_code": exercise.get("starter_code", ""),
        "stages": stages,
    }


def _read_files(root: Path) -> list[dict]:
    items = []
    env_names = set(_virtual_envs(root))
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in SKIP_PARTS for part in relative.parts) or (relative.parts and relative.parts[0] in env_names):
            continue
        if path.is_file() and path.name != ".lab-state.json":
            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            items.append({"path": relative.as_posix(), "content": content[:MAX_FILE_SIZE]})
    return items[:100]


def _read_directories(root: Path) -> list[str]:
    directories = []
    env_names = set(_virtual_envs(root))
    for path in sorted(root.rglob("*")):
        if not path.is_dir():
            continue
        relative = path.relative_to(root)
        if (any(part in SKIP_PARTS or part.startswith(".") for part in relative.parts)
                or (relative.parts and relative.parts[0] in env_names)):
            continue
        directories.append(relative.as_posix())
    return directories[:100]


def _virtual_envs(root: Path) -> list[str]:
    result = []
    for cfg in root.glob("*/pyvenv.cfg"):
        if cfg.is_file():
            result.append(cfg.parent.name)
    return sorted(result)


def _remove_extra_virtual_envs(root: Path, state: dict | None = None) -> list[str]:
    """Keep one predictable environment per exercise: ``.venv``."""
    removed = []
    for name in _virtual_envs(root):
        if name == ".venv":
            continue
        shutil.rmtree(root / name)
        removed.append(name)
    if state is not None and str(state.get("active_env", "")) in removed:
        state["active_env"] = ""
    return removed


def _read_state(root: Path) -> dict:
    path = root / ".lab-state.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"completed_stages": [], "commands": [], "terminal_cwd": "", "active_env": ""}


def _write_state(root: Path, state: dict) -> None:
    (root / ".lab-state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _seed(root: Path, course: dict) -> None:
    readme = f"""# {course['title']}

这是你的独立实验项目。请跟随左侧阶段清单，从创建文件开始完成项目。

## 项目目标

{course['description']}

## 约定

- 核心可测试逻辑写在 `solution.py`
- 可运行的 {course['framework']} 应用写在 `app.py`
- 真实 API Key 只放在本地 `.env`，不要提交
"""
    (root / "README.md").write_text(readme, encoding="utf-8")
    (root / ".gitignore").write_text(".venv/\n.env\n__pycache__/\n.pytest_cache/\n", encoding="utf-8")
    _write_state(root, {"completed_stages": [], "commands": []})


def get_workspace(user_id: int, exercise_id: str, reset: bool = False) -> dict:
    root = _root(user_id, exercise_id)
    course = _course(exercise_id)
    if reset:
        for child in list(root.iterdir()):
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    if not any(root.iterdir()):
        _seed(root, course)
    state = _read_state(root)
    removed_virtual_envs = _remove_extra_virtual_envs(root, state)
    if removed_virtual_envs:
        _write_state(root, state)
    return {
        "project_name": f"agent-lab-{exercise_id}",
        "files": _read_files(root),
        "directories": _read_directories(root),
        "virtual_env": (root / ".venv" / "pyvenv.cfg").is_file(),
        "virtual_envs": _virtual_envs(root),
        "removed_virtual_envs": removed_virtual_envs,
        "terminal_cwd": state.get("terminal_cwd", ""),
        "active_env": state.get("active_env", ""),
        "course": course,
        "completed_stages": state.get("completed_stages", []),
    }


def get_progress_overview(user_id: int) -> dict:
    """Return lightweight stage progress for course trees and document badges."""
    user_root = WORKSPACE_ROOT / f"user-{int(user_id)}"
    overview = {}
    for exercise_id in sorted(SPECS):
        root = user_root / _safe_part(exercise_id)
        state = _read_state(root) if root.is_dir() else {"completed_stages": []}
        overview[exercise_id] = {
            "completed_stages": state.get("completed_stages", []),
            "virtual_env": (root / ".venv" / "pyvenv.cfg").is_file(),
            "total_stages": len(_course(exercise_id)["stages"]),
        }
    return overview


def save_file(user_id: int, exercise_id: str, path: str, content: str) -> dict:
    root = _root(user_id, exercise_id)
    target = _safe_path(root, path, allow_hidden=True)
    encoded = content.encode("utf-8")
    if len(encoded) > MAX_FILE_SIZE:
        raise ValueError("单个文件不能超过 300KB")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(encoded)
    return {"path": target.relative_to(root).as_posix(), "saved": True}


def create_directory(user_id: int, exercise_id: str, path: str) -> dict:
    root = _root(user_id, exercise_id)
    target = _safe_path(root, path, allow_hidden=True)
    target.mkdir(parents=True, exist_ok=True)
    return {"path": target.relative_to(root).as_posix(), "created": True}


def delete_file(user_id: int, exercise_id: str, path: str) -> dict:
    root = _root(user_id, exercise_id)
    target = _safe_path(root, path, allow_hidden=True)
    if not target.is_file():
        raise ValueError("文件不存在")
    target.unlink()
    return {"path": path, "deleted": True}


def move_entry(user_id: int, exercise_id: str, path: str, destination: str) -> dict:
    root = _root(user_id, exercise_id)
    source = _safe_path(root, path, allow_hidden=True)
    target = _safe_path(root, destination, allow_hidden=True)
    if not source.exists():
        raise ValueError("文件或文件夹不存在")
    if source == root / ".venv":
        raise ValueError(".venv 是本题唯一虚拟环境，不能重命名")
    if target.exists():
        raise ValueError("目标名称已经存在")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target))
    return {"path": path, "destination": target.relative_to(root).as_posix(), "moved": True}


def duplicate_entry(user_id: int, exercise_id: str, path: str, destination: str) -> dict:
    root = _root(user_id, exercise_id)
    source = _safe_path(root, path, allow_hidden=True)
    target = _safe_path(root, destination, allow_hidden=True)
    if not source.exists():
        raise ValueError("文件或文件夹不存在")
    if source == root / ".venv":
        raise ValueError("虚拟环境不需要复制")
    if target.exists():
        raise ValueError("目标名称已经存在")
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, target)
    return {"path": target.relative_to(root).as_posix(), "duplicated": True}


def delete_entry(user_id: int, exercise_id: str, path: str) -> dict:
    root = _root(user_id, exercise_id)
    target = _safe_path(root, path, allow_hidden=True)
    if not target.exists():
        raise ValueError("文件或文件夹不存在")
    if target == root / ".venv":
        raise ValueError("请使用“新建项目”重置虚拟环境")
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return {"path": path, "deleted": True}


def list_entries(user_id: int, exercise_id: str, path: str = "") -> dict:
    """List one project directory, including hidden and virtual-env entries."""
    root = _root(user_id, exercise_id)
    directory = root if not str(path or "").strip("/\\") else _safe_path(root, path, allow_hidden=True)
    if not directory.is_dir():
        raise ValueError("目录不存在")
    entries = []
    for child in sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        if child.name == ".lab-state.json":
            continue
        relative = child.relative_to(root).as_posix()
        try:
            size = child.stat().st_size if child.is_file() else 0
        except OSError:
            size = 0
        entries.append({
            "name": child.name,
            "path": relative,
            "is_directory": child.is_dir(),
            "size": size,
            "virtual": child.is_dir() and (child / "pyvenv.cfg").is_file(),
        })
    return {"path": "" if directory == root else directory.relative_to(root).as_posix(), "entries": entries}


def read_file(user_id: int, exercise_id: str, path: str) -> dict:
    """Read a project file on demand so large environments do not block loading."""
    root = _root(user_id, exercise_id)
    target = _safe_path(root, path, allow_hidden=True)
    if not target.is_file():
        raise ValueError("文件不存在")
    size = target.stat().st_size
    if size > 2_000_000:
        return {"path": path, "content": "", "binary": True, "size": size, "message": "文件过大，无法在编辑器中预览"}
    raw = target.read_bytes()
    if b"\x00" in raw:
        return {"path": path, "content": "", "binary": True, "size": size, "message": "二进制文件无法作为文本预览"}
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            content = raw.decode("gb18030")
        except UnicodeDecodeError:
            return {"path": path, "content": "", "binary": True, "size": size, "message": "该文件不是可识别的文本格式"}
    return {"path": path, "content": content, "binary": False, "size": size}


def _clean_output(value: str, limit: int = 12_000) -> str:
    return (value or "").replace(str(WORKSPACE_ROOT), "<workspace>")[-limit:]


def _terminal_directory(root: Path, state: dict) -> Path:
    relative = str(state.get("terminal_cwd", "") or "").replace("\\", "/").strip("/")
    try:
        candidate = root if not relative else _safe_path(root, relative, allow_hidden=True)
    except ValueError:
        candidate = root
    return candidate if candidate.is_dir() else root


def _activation_env(root: Path, command: str) -> Path | None:
    normalized = command.strip().replace("\\", "/")
    patterns = [
        # source .venv/bin/activate  /  . .venv/bin/activate  /  source .venv/Scripts/activate.bat
        r"^(?:source|\.)\s+['\"]?(.+?)/(?:bin/activate|Scripts/(?:activate(?:\.bat)?|Activate\.ps1))['\"]?$",
        # Bare Windows: .venv\Scripts\activate.bat  /  & .venv/Scripts/Activate.ps1
        r"^(?:&\s*)?['\"]?(.+?)/Scripts/(?:activate(?:\.bat)?|Activate\.ps1)['\"]?$",
        # Bare Unix path (without source/.) — user typed path directly: .venv/bin/activate
        r"^['\"]?(.+?)/bin/activate['\"]?$",
        # bash/sh wrapper: bash .venv/bin/activate  /  sh .venv/bin/activate
        r"^(?:bash|sh|zsh)\s+['\"]?(.+?)/(?:bin/activate|Scripts/(?:activate(?:\.bat)?|Activate\.ps1))['\"]?$",
    ]
    for pattern in patterns:
        match = re.match(pattern, normalized, re.IGNORECASE)
        if not match:
            continue
        raw = match.group(1).strip("'\"")
        try:
            target = _safe_path(root, raw, allow_hidden=True)
        except ValueError:
            return None
        if (target / "pyvenv.cfg").is_file():
            return target
    return None


def _ensure_activate_executable(venv_root: Path) -> None:
    """确保虚拟环境的激活脚本有执行权限（python -m venv 在 Linux 上创建的文件默认为 0644）"""
    try:
        for script in ["bin/activate", "Scripts/activate.bat", "Scripts/Activate.ps1"]:
            sp = venv_root / script
            if sp.is_file():
                sp.chmod(sp.stat().st_mode | 0o111)  # 添加执行权限
    except OSError:
        pass  # 权限修改失败不阻塞主流程


def _terminal_environment(root: Path, state: dict) -> tuple[dict, str]:
    env = os.environ.copy()
    env.update({"HOME": str(root), "PYTHONIOENCODING": "utf-8", "LAB_MODE": "1",
                "PIP_INDEX_URL": "https://pypi.tuna.tsinghua.edu.cn/simple"})
    active = str(state.get("active_env", "") or "")
    if active:
        try:
            target = _safe_path(root, active, allow_hidden=True)
        except ValueError:
            target = root / "__missing_environment__"
        executable_dir = target / ("Scripts" if os.name == "nt" else "bin")
        if (target / "pyvenv.cfg").is_file() and executable_dir.is_dir():
            env["VIRTUAL_ENV"] = str(target)
            env["PATH"] = str(executable_dir) + os.pathsep + env.get("PATH", "")
        else:
            active = ""
            state["active_env"] = ""
    return env, active


def _terminal_result(command: str, state: dict, exit_code: int, output: str = "") -> dict:
    return {
        "command": command,
        "output": output,
        "exit_code": exit_code,
        "cwd": state.get("terminal_cwd", ""),
        "active_env": state.get("active_env", ""),
    }


def _canonical_venv_command(command: str) -> tuple[str, str]:
    """Redirect the common venv creation form to the exercise's only environment."""
    match = re.fullmatch(
        r"((?:python(?:3(?:\.\d+)?)?|py(?:\s+-\d+(?:\.\d+)?)?)\s+-m\s+venv(?:\s+--[\w-]+)*)\s+([^\s;&|]+)",
        command.strip(),
        re.IGNORECASE,
    )
    if not match:
        return command, ""
    requested = match.group(2).strip("'\"").replace("\\", "/").strip("/")
    if requested == ".venv":
        return command, ""
    return f"{match.group(1)} .venv", f"每道题只使用一个虚拟环境，已将 {requested} 统一为 .venv。\n"


def stream_terminal(user_id: int, exercise_id: str, command: str):
    """Yield terminal events while a command is running."""
    root = _root(user_id, exercise_id)
    command = str(command or "").strip()
    state = _read_state(root)
    removed = _remove_extra_virtual_envs(root, state)
    cwd = _terminal_directory(root, state)
    output_already_streamed = False
    if not command:
        yield {"type": "done", **_terminal_result("", state, 0)}
        return
    if len(command) > 2_000:
        raise ValueError("单条命令不能超过 2000 个字符")

    yield {
        "type": "start", "command": command,
        "cwd": state.get("terminal_cwd", ""), "active_env": state.get("active_env", ""),
    }
    if removed:
        yield {"type": "output", "data": f"每道题仅保留 .venv，已清理重复环境：{', '.join(removed)}\n"}

    if command.lower() in {"clear", "cls"}:
        yield {"type": "clear"}
        yield {"type": "done", **_terminal_result(command, state, 0, "__CLEAR__")}
        return

    # ── lab-test 终端命令：在终端中运行实际判题测试 ──
    if re.match(r"^(?:python(?:3(?:\.\d+)?)?\s+(?:-m\s+)?)?lab[-_]?test\b", command.strip(), re.IGNORECASE):
        output = _handle_lab_test_command(root, exercise_id, state)
        exit_code = 0 if "全部通过" in output else 1
        output_already_streamed = True
        yield {"type": "output", "data": output}
        yield {"type": "done", **_terminal_result(command, state, exit_code, output)}
        return

    activated = _activation_env(root, command)
    if activated:
        active_env = activated.relative_to(root).as_posix()
        state["active_env"] = active_env
        # 确保 activate 脚本有执行权限（python -m venv 创建的文件可能没有）
        _ensure_activate_executable(activated)
        output, exit_code = f"已激活虚拟环境 {active_env}\n", 0
    elif command.lower() == "deactivate":
        state["active_env"] = ""
        output, exit_code = "已退出虚拟环境\n", 0
    else:
        shell_command, venv_notice = _canonical_venv_command(command)
        if venv_notice:
            yield {"type": "output", "data": venv_notice}
        try:
            parts = shlex.split(shell_command, posix=os.name != "nt")
        except ValueError as exc:
            raise ValueError(f"命令格式不完整：{exc}") from exc
        if parts and parts[0].lower() == "cd":
            requested = parts[1] if len(parts) > 1 else ""
            if len(parts) > 2:
                raise ValueError("cd 命令一次只能进入一个目录")
            try:
                target = root if not requested else (cwd / requested).resolve()
                if target != root.resolve() and root.resolve() not in target.parents:
                    raise ValueError
            except (OSError, ValueError):
                output, exit_code = "cd: 只能进入当前项目中的目录\n", 1
            else:
                if not target.is_dir():
                    output, exit_code = f"cd: 目录不存在：{requested}\n", 1
                else:
                    cwd = target
                    state["terminal_cwd"] = "" if target == root.resolve() else target.relative_to(root.resolve()).as_posix()
                    output, exit_code = "", 0
        else:
            env, _ = _terminal_environment(root, state)
            if parts == ["tree"] and shutil.which("tree", path=env.get("PATH")) is None:
                lines = ["."]
                for index, path in enumerate(sorted(cwd.rglob("*"))):
                    if index >= 5_000:
                        lines.append("… 项目内容较多，已显示前 5000 项")
                        break
                    relative = path.relative_to(cwd)
                    lines.append(f"{'    ' * (len(relative.parts) - 1)}└── {path.name}{'/' if path.is_dir() else ''}")
                output, exit_code = "\n".join(lines) + "\n", 0
            else:
                if os.name == "nt" and parts and parts[0].lower() in {"mkdir", "md"}:
                    shell_command = shell_command.replace("/", "\\")
                env["PYTHONUNBUFFERED"] = "1"
                chunks: queue.Queue[str | None] = queue.Queue()
                proc = None
                started = time.monotonic()
                try:
                    proc = subprocess.Popen(
                        shell_command, cwd=cwd, shell=True, executable=None if os.name == "nt" else "/bin/sh",
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                        encoding="utf-8", errors="replace", bufsize=1, env=env,
                    )
                    def read_process_output() -> None:
                        assert proc is not None and proc.stdout is not None
                        try:
                            for line in iter(proc.stdout.readline, ""):
                                # 将 \r 替换为 \n，防止 pip 进度条等原地刷新内容在终端中互相覆盖
                                clean_line = line.replace('\r\n', '\n').replace('\r', '\n')
                                chunks.put(clean_line)
                        finally:
                            chunks.put(None)

                    threading.Thread(target=read_process_output, daemon=True).start()
                    output_parts = []
                    stream_finished = False
                    while not stream_finished:
                        if time.monotonic() - started > 600:
                            proc.terminate()
                            notice = "\n命令运行超过 600 秒（10分钟），已停止。\n"
                            output_parts.append(notice)
                            yield {"type": "output", "data": notice}
                            exit_code = 124
                            break
                        try:
                            chunk = chunks.get(timeout=0.1)
                        except queue.Empty:
                            if proc.poll() is not None:
                                continue
                            continue
                        if chunk is None:
                            stream_finished = True
                        else:
                            clean = chunk.replace(str(WORKSPACE_ROOT), "<workspace>")
                            output_parts.append(clean)
                            yield {"type": "output", "data": clean}
                    if proc.poll() is None:
                        proc.wait(timeout=3)
                    if 'exit_code' not in locals() or exit_code != 124:
                        exit_code = proc.returncode
                    output = "".join(output_parts)
                    output_already_streamed = True
                finally:
                    if proc is not None and proc.poll() is None:
                        proc.terminate()
                        try:
                            proc.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                    if proc is not None and proc.stdout is not None:
                        proc.stdout.close()

    if output and not output_already_streamed:
        yield {"type": "output", "data": output}

    if exit_code == 0 and re.search(r"(?:^|[;&|]\s*)(?:python\s+-m\s+pip|pip)\s+install\s+-r\s+requirements\.txt(?:\s|$)", command, re.IGNORECASE):
        state["installed_requirements_hash"] = _requirements_hash(root)
    state.setdefault("commands", []).append({"command": command, "exit_code": exit_code})
    state["commands"] = state["commands"][-80:]
    _write_state(root, state)
    yield {"type": "done", **_terminal_result(command, state, exit_code)}


def run_terminal(user_id: int, exercise_id: str, command: str) -> dict:
    """Compatibility wrapper for tests and non-streaming clients."""
    output_parts = []
    result = None
    for event in stream_terminal(user_id, exercise_id, command):
        if event["type"] == "output":
            output_parts.append(event.get("data", ""))
        elif event["type"] == "clear":
            output_parts = ["__CLEAR__"]
        elif event["type"] == "done":
            result = event
    result = result or {"command": command, "exit_code": 1, "cwd": "", "active_env": ""}
    result.pop("type", None)
    result["output"] = _clean_output("".join(output_parts))
    return result


def _requirements(root: Path) -> list[str]:
    path = root / "requirements.txt"
    if not path.is_file():
        return []
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip().lower()
        if line:
            result.append(re.split(r"[<>=!~\[]", line, 1)[0].strip().replace("_", "-"))
    return result


def _requirements_hash(root: Path) -> str:
    path = root / "requirements.txt"
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _contains_secret(root: Path) -> bool:
    pattern = re.compile(r"(?i)(api[_-]?key|secret)\s*=\s*['\"][a-z0-9_-]{16,}['\"]")
    for name in ["solution.py", "app.py"]:
        path = root / name
        if path.is_file() and pattern.search(path.read_text(encoding="utf-8")):
            return True
    return False


def _stage_result(stage: dict, checks: list[dict]) -> dict:
    passed = all(item["passed"] for item in checks)
    return {**stage, "passed": passed, "checks": checks, "summary": "检查通过，可以进入下一步" if passed else "还有项目项需要完善"}


def _judge_check_detail(judged: dict) -> str:
    """Turn private judge output into concise, actionable learner feedback."""
    passed_count = judged.get("passed_count", 0)
    total = judged.get("total", 0)
    if judged.get("passed"):
        return f"通过 {passed_count}/{total} 个业务场景，函数已有可运行的真实行为"
    if judged.get("compile_error"):
        return f"业务测试无法运行：{judged['compile_error']}"
    failed = [
        str(item.get("description", "")).strip()
        for item in judged.get("results", [])
        if not item.get("passed") and str(item.get("description", "")).strip()
    ]
    suffix = f"；请先修正：{'、'.join(failed[:3])}" if failed else ""
    return f"仅通过 {passed_count}/{total} 个业务场景{suffix}"


def _judge_case_feedback(judged: dict) -> list[dict]:
    if judged.get("compile_error"):
        return []
    return [
        {
            "label": str(item.get("description") or f"测试点 {item.get('case_index', '?')}")[:80],
            "passed": bool(item.get("passed")),
            "detail": "通过" if item.get("passed") else str(item.get("error") or "未满足业务契约")[:240],
        }
        for item in judged.get("results", [])
    ]


def _is_named_call(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Call) and (
        (isinstance(node.func, ast.Name) and node.func.id == name)
        or (isinstance(node.func, ast.Attribute) and node.func.attr == name)
    )


def _integration_contract_checks(exercise_id: str, tree: ast.AST) -> list[tuple[str, bool, str]]:
    """Check observable framework wiring without making a real paid model request."""
    if exercise_id == "1-1":
        builder_vars = {
            target.id
            for node in ast.walk(tree)
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            for target in ((node.targets if isinstance(node, ast.Assign) else [node.target]))
            if isinstance(target, ast.Name) and _is_named_call(node.value, "build_chat_messages")
        }
        invoke_calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "invoke"
        ]
        uses_messages = any(
            any(
                _is_named_call(arg, "build_chat_messages")
                or (isinstance(arg, ast.Name) and arg.id in builder_vars)
                for arg in [*call.args, *(keyword.value for keyword in call.keywords)]
            )
            for call in invoke_calls
        )
        return [
            ("聊天模型调用", bool(invoke_calls), "已调用 model.invoke()" if invoke_calls else "需要调用 model.invoke(messages)"),
            (
                "个性化消息接入", uses_messages,
                "build_chat_messages 的结果已传入模型" if uses_messages
                else "请把 build_chat_messages(...) 的返回值传给 model.invoke()",
            ),
        ]

    if exercise_id == "1-3":
        stream_vars = {
            target.id
            for node in ast.walk(tree)
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            for target in ((node.targets if isinstance(node, ast.Assign) else [node.target]))
            if isinstance(target, ast.Name) and _is_named_call(node.value, "stream")
        }
        loops = [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.For, ast.AsyncFor))
            and (_is_named_call(node.iter, "stream") or (isinstance(node.iter, ast.Name) and node.iter.id in stream_vars))
        ]
        immediate = False
        accumulates = False
        for loop in loops:
            loop_calls = [node for node in ast.walk(loop) if isinstance(node, ast.Call)]
            immediate = immediate or any(
                isinstance(call.func, ast.Name) and call.func.id == "print"
                and any(keyword.arg == "flush" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True for keyword in call.keywords)
                for call in loop_calls
            ) or (
                any(isinstance(call.func, ast.Attribute) and call.func.attr == "write" for call in loop_calls)
                and any(isinstance(call.func, ast.Attribute) and call.func.attr == "flush" for call in loop_calls)
            )
            accumulates = accumulates or any(
                isinstance(call.func, ast.Attribute) and call.func.attr == "append" for call in loop_calls
            )
        normalizes = any(_is_named_call(node, "normalize_stream_chunks") for node in ast.walk(tree))
        return [
            ("真实流式调用", bool(loops), "已逐个遍历 model.stream() 片段" if loops else "需要使用 for chunk in model.stream(messages)"),
            (
                "逐片段即时输出", immediate,
                "检测到循环内刷新输出" if immediate else "请在流式循环内输出片段，并设置 flush=True",
            ),
            (
                "完整回答累积", accumulates,
                "流式片段会被累积为完整回答" if accumulates else "请在输出片段的同时 append 到结果列表",
            ),
            (
                "片段规范化接入", normalizes,
                "已调用 normalize_stream_chunks" if normalizes else "请使用 normalize_stream_chunks 处理模型片段",
            ),
        ]
    return []


def _run_integration_runtime_test(root: Path, exercise_id: str, course: dict, add, user_id: int) -> None:
    """使用用户配置的真实 API Key 实际运行 app.py，验证端到端集成行为。

    与头歌/EduCoder 平台的关键区别：
    - 头歌：用预置测试用例匹配输出字符串（黑盒）
    - 本系统：实际调用用户配置的大模型 API，真正运行学生的 Agent 代码，
      验证模型调用是否成功、输出是否正确提取

    要求用户先在「个人中心 → AI大模型配置」中配置 API Key，
    未配置时明确提示，不允许"糊弄式"通过。
    """
    # 仅对有框架接入的关卡执行运行时测试
    if not course.get("framework_imports"):
        return

    app_path = root / "app.py"
    if not app_path.is_file():
        return

    app_code = app_path.read_text(encoding="utf-8")
    if len(app_code.strip()) < 30:
        add("运行时集成测试", False, "app.py 内容过短，请完成代码后再测试")
        return

    # ── 读取用户的真实 API 配置 ──
    try:
        from database import get_db
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM user_llm_config WHERE user_id = ?", (user_id,)
        ).fetchone()
        conn.close()
        user_config = dict(row) if row else None
    except Exception:
        user_config = None

    if not user_config or not user_config.get("api_key"):
        add(
            "运行时集成测试", False,
            "请先在「个人中心 → AI大模型配置」中配置您的 API Key、接口地址和模型名称，"
            "否则无法进行真实运行验证。配置后重新点击检查。"
        )
        return

    api_key = user_config["api_key"]
    base_url = user_config.get("base_url", "https://api.deepseek.com")
    model_name = user_config.get("model_name", "deepseek-chat")

    # ── 准备运行环境 ──
    env = os.environ.copy()
    env.update({
        "DEEPSEEK_API_KEY": api_key,
        "LLM_BASE_URL": base_url,
        "LLM_MODEL": model_name,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
        "LAB_MODE": "1",
        "PIP_INDEX_URL": "https://pypi.tuna.tsinghua.edu.cn/simple",
    })

    python_cmd = os.environ.get("PYTHON_PATH", sys.executable)
    # 不使用工作区的 .venv Python（里面可能没有安装 langchain 等依赖）
    # 集成测试直接使用系统 Python（Docker 镜像中已预装所有依赖）
    has_venv = (root / ".venv" / "pyvenv.cfg").is_file()
    if has_venv:
        # 只把 .venv 加入 PATH，让 app.py 中可能的 subprocess 能找到它
        # 但实际运行用系统 Python
        executable_dir = root / (".venv/Scripts" if os.name == "nt" else ".venv/bin")
        if executable_dir.is_dir():
            env["PATH"] = str(executable_dir) + os.pathsep + env.get("PATH", "")

    try:
        proc = subprocess.run(
            [python_cmd, "-X", "utf8", str(app_path)],
            cwd=root, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30, env=env,
        )
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        combined_output = (stdout + "\n" + stderr).strip()
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        add("运行时集成测试", False, "app.py 运行超时（>30秒），请检查是否有死循环或 API 调用未设置超时")
        return

    if exit_code != 0:
        error_lower = combined_output.lower()
        if "401" in error_lower or "unauthorized" in error_lower or "invalid api key" in error_lower:
            detail = "API Key 无效或已过期，请检查「个人中心 → AI大模型配置」中的 Key 是否正确"
        elif "modulenotfounderror" in error_lower or "no module named" in error_lower:
            detail = "缺少依赖包，请在终端执行 pip install -r requirements.txt"
        elif "importerror" in error_lower or "cannot import" in error_lower:
            detail = "导入失败，请检查 solution.py 中的函数名与 app.py 中的 import 语句是否一致"
        elif "connection" in error_lower or "timeout" in error_lower or "refused" in error_lower:
            detail = f"网络连接失败，请检查 Base URL ({base_url}) 是否可访问，以及网络/代理设置"
        elif "attributeerror" in error_lower:
            detail = "对象属性访问错误，请检查 response.content 等属性是否正确使用"
        else:
            last_lines = combined_output.splitlines()[-3:]
            detail = f"运行异常(exit={exit_code})：" + "；".join(line[:120] for line in last_lines)
        add("运行时集成测试", False, detail)
        return

    # ── 运行成功 ──
    output_len = len(combined_output)
    if output_len < 20:
        add("运行时集成测试", False, f"app.py 运行成功但输出仅 {output_len} 字符，请确保 print 了模型响应内容")
    else:
        detail = f"✓ 真实 API 调用成功（模型: {model_name}），app.py 输出 {output_len} 字符"
        add("运行时集成测试", True, detail)


def _handle_lab_test_command(root: Path, exercise_id: str, terminal_state: dict) -> str:
    """处理 `python -m lab_test` / `lab-test` 终端命令。

    在项目目录下运行实际判题测试并返回终端格式的结果。
    """
    solution = root / "solution.py"
    if not solution.is_file():
        return "错误: 当前目录下没有 solution.py，请先完成核心模块后再测试。\n"

    try:
        from services.lab_test_runner import run_tests, print_terminal_results
    except ImportError:
        return "错误: lab_test_runner 模块未加载，请通过UI检查阶段。\n"

    code = solution.read_text(encoding="utf-8")
    result = run_tests(exercise_id, code)
    return print_terminal_results(result) + "\n"


def check_stage(user_id: int, exercise_id: str, stage_id: str) -> dict:
    root = _root(user_id, exercise_id)
    course = _course(exercise_id)
    stage = next((item for item in course["stages"] if item["id"] == stage_id), None)
    if not stage:
        raise ValueError("未找到该阶段")
    checks: list[dict] = []

    def add(label: str, passed: bool, detail: str, cases: list[dict] | None = None) -> None:
        item = {"label": label, "passed": bool(passed), "detail": detail}
        if cases:
            item["cases"] = cases
        checks.append(item)

    if stage_id == "structure":
        for name in course["project_files"]:
            ok = (root / name).is_file()
            add(name, ok, "文件存在，名称完全一致" if ok else f"请在项目根目录创建 {name}")
    elif stage_id == "environment":
        cfg = root / ".venv" / "pyvenv.cfg"
        add("虚拟环境目录", cfg.is_file(), "检测到 .venv/pyvenv.cfg" if cfg.is_file() else "请执行 python -m venv .venv")
        add("Python 版本", sys.version_info >= (3, 11), f"当前沙箱 Python {sys.version.split()[0]}")
    elif stage_id == "dependencies":
        declared = _requirements(root)
        for package in course["packages"]:
            ok = package.lower().replace("_", "-") in declared
            add(package, ok, "已在 requirements.txt 声明" if ok else f"请把 {package} 写入 requirements.txt")
        state = _read_state(root)
        installed = bool(_requirements_hash(root)) and state.get("installed_requirements_hash") == _requirements_hash(root)
        add("虚拟环境依赖", installed, "当前 requirements.txt 已成功安装" if installed else "请先创建 .venv，再执行 pip install -r requirements.txt；修改依赖文件后需要重新安装")
    elif stage_id == "implementation":
        path = root / "solution.py"
        if not path.is_file():
            add("solution.py", False, "请先创建 solution.py")
        else:
            source = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source)
                add("Python 语法", True, "AST 解析成功")
                names = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
                for target in course["targets"]:
                    add(target, target in names, "目标函数已定义" if target in names else f"还没有定义 {target}")
                if all(target in names for target in course["targets"]):
                    judged = judge_submission(exercise_id, source)
                    add(
                        "核心函数行为", judged.get("passed", False), _judge_check_detail(judged),
                        _judge_case_feedback(judged),
                    )
            except SyntaxError as exc:
                add("Python 语法", False, f"第 {exc.lineno or '?'} 行：{exc.msg}")
    elif stage_id == "integration":
        solution = root / "solution.py"
        if solution.is_file():
            judged = judge_submission(exercise_id, solution.read_text(encoding="utf-8"))
            add(
                "核心模块业务测试", judged.get("passed", False), _judge_check_detail(judged),
                _judge_case_feedback(judged),
            )
        else:
            add("核心模块业务测试", False, "缺少 solution.py，不能接入空模块")
        path = root / "app.py"
        if not path.is_file():
            add("app.py", False, "请先创建 app.py")
        else:
            source = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source)
                add("app.py 语法", True, "可正常解析")
                imported = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imported.update(alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imported.add(node.module)
                has_framework = any(any(name == expected or name.startswith(expected + ".") for expected in course["framework_imports"]) for name in imported)
                add("框架接入", has_framework, f"检测到：{', '.join(sorted(imported)) or '无导入'}" if has_framework else f"需要导入 {course['framework']}")
                has_solution = any(name == "solution" or name.startswith("solution.") for name in imported)
                add("核心模块接入", has_solution, "已导入 solution" if has_solution else "请从 solution 导入你实现的函数")
                for label, passed, detail in _integration_contract_checks(exercise_id, tree):
                    add(label, passed, detail)
            except SyntaxError as exc:
                add("app.py 语法", False, f"第 {exc.lineno or '?'} 行：{exc.msg}")
            add("密钥安全", not _contains_secret(root), "未发现硬编码密钥" if not _contains_secret(root) else "疑似把真实密钥写进了代码，请改用环境变量")

            # ── 实际运行集成测试（使用用户真实 API Key）──
            _run_integration_runtime_test(root, exercise_id, course, add, user_id)
    elif stage_id == "acceptance":
        prior = [check_stage(user_id, exercise_id, item["id"]) for item in course["stages"][:-1]]
        for item in prior:
            add(item["title"], item["passed"], item["summary"])
        solution = root / "solution.py"
        if solution.is_file():
            judged = judge_submission(exercise_id, solution.read_text(encoding="utf-8"))
            add(
                "私有业务场景", judged.get("passed", False), _judge_check_detail(judged),
                _judge_case_feedback(judged),
            )
        else:
            add("私有业务场景", False, "缺少 solution.py")

        # 验收阶段也执行运行时集成测试（使用用户真实 API Key）
        if solution.is_file() and (root / "app.py").is_file():
            _run_integration_runtime_test(root, exercise_id, course, add, user_id)

    result = _stage_result(stage, checks)
    state = _read_state(root)
    completed = set(state.get("completed_stages", []))
    if result["passed"]:
        completed.add(stage_id)
    else:
        completed.discard(stage_id)
    state["completed_stages"] = [item["id"] for item in course["stages"] if item["id"] in completed]
    _write_state(root, state)
    result["completed_stages"] = state["completed_stages"]
    return result


async def ask_assistant(user_id: int, exercise_id: str, question: str, active_file: str = "", mode: str = "agent") -> dict:
    root = _root(user_id, exercise_id)
    course = _course(exercise_id)
    question = str(question or "").strip()
    if not question:
        raise ValueError("请先输入问题")
    mode = "chat" if mode == "chat" else "agent"
    from services.guidance_context_service import build_learning_context, public_learning_context
    learning_context = build_learning_context(user_id, question, exercise_id)
    snippets = []
    for item in _read_files(root):
        if item["path"].endswith((".py", ".txt", ".md")) and (mode == "agent" or item["path"] == active_file):
            snippets.append(f"--- {item['path']} ---\n{item['content'][:2500]}")
    role_hint = (
        "你处于 Chat 问答模式：直接解释学生的问题，不规划或声称执行项目操作。"
        if mode == "chat" else
        "你处于 Agent 项目模式：结合整个项目进行分步诊断，但所有代码或命令都只作为建议，必须由学生手动确认后填入。"
    )
    prompt = f"""你是 Agent 工程编程实验室中的结对导师。当前实验：{course['title']}，框架：{course['framework']}。
{role_hint}
学生问题：{question}
当前文件：{active_file or '未选择'}

项目内容：
{chr(10).join(snippets)[:9000]}

{learning_context['prompt']}

要求：
1. 重点解释 LangChain/LangGraph 的导入包、类、方法、参数、返回对象和工程作用。
2. 不讲学生已经掌握的基础 Python 语法，除非基础语法正是报错根因。
3. 优先定位到文件名和下一步操作；不要一次贴出整个项目答案。
4. 若发现文件名、虚拟环境、依赖或密钥安全问题，要明确指出。
5. 使用规范 Markdown；命令和代码必须放进带语言标识的围栏代码块，不要输出未闭合的符号。
6. 用中文，控制在 500 字以内。"""
    try:
        from services.ai_service import call_llm
        from services.personalization_service import build_personalized_system_prompt
        system_prompt = build_personalized_system_prompt(
            user_id,
            question,
            "你是 Agent 工程编程实验室中的结对导师。只提供与当前实验相关的分步诊断，不直接替学生完成整个项目。",
        )
        system_prompt += "\n\n" + learning_context["prompt"]
        answer = await call_llm(
            user_id,
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=900,
        )
        if answer.startswith("LLM调用异常:"):
            raise ValueError(answer)
        return {
            "answer": answer,
            "mode": mode,
            "notice": f"已结合学习路径：{learning_context.get('topic', course['title'])}",
            "learning_context": public_learning_context(learning_context),
        }
    except Exception:
        missing = [name for name in course["project_files"] if not (root / name).is_file()]
        if missing:
            answer = f"先完成项目骨架：当前还缺少 {', '.join(missing)}。建议从 requirements.txt 开始，再创建 solution.py。创建后点击左侧“AI 检查本阶段”，我会逐项核对文件名。"
        elif not (root / ".venv" / "pyvenv.cfg").is_file():
            answer = "项目文件已经齐了。下一步在终端执行 `python -m venv .venv`。这个命令会为当前项目创建独立解释器环境，避免不同项目的 LangChain 版本互相影响。"
        else:
            answer = f"请先聚焦 {active_file or 'solution.py'}。本实验的核心目标是 `{', '.join(course['targets'])}`；完成后先运行 `python -m py_compile solution.py` 检查语法，再让左侧阶段检查器验证业务契约。若要获得生成式分析，请先在个人中心配置模型。"
        return {
            "answer": answer,
            "mode": mode,
            "notice": f"已结合学习路径：{learning_context.get('topic', course['title'])}。当前使用内置项目诊断。",
            "learning_context": public_learning_context(learning_context),
        }
