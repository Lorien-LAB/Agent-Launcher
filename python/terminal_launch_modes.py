from __future__ import annotations

import os
import subprocess
import threading
import time
import uuid


def build_tab_command(directory: str, title: str, script_path: str) -> list[str]:
    return [
        "wt",
        "-w",
        "0",
        "new-tab",
        "-d",
        directory,
        "--title",
        title,
        "--suppressApplicationTitle",
        "pwsh",
        "-NoExit",
        "-File",
        script_path,
    ]


def launch_with_mode(
    base_launcher,
    dir_path: str,
    exe_path: str,
    args: str,
    title: str,
    terminal_mode: str = "window",
) -> bool:
    if terminal_mode == "window":
        return bool(base_launcher(dir_path, exe_path, args, title))
    if terminal_mode != "tab":
        raise ValueError("terminal_mode must be 'window' or 'tab'")
    if not os.path.isdir(dir_path):
        return False

    token = uuid.uuid4().hex[:12]
    stable_title = f"{title} — {os.path.basename(dir_path)} · TAB-{token}"
    safe_title = stable_title.replace("'", "''")
    safe_exe = exe_path.replace("'", "''")
    script = (
        f"$Host.UI.RawUI.WindowTitle = '{safe_title}'{os.linesep}"
        f"& '{safe_exe}' {args}{os.linesep}"
    )
    temporary = os.path.join(
        os.environ.get("TEMP", os.path.expanduser("~")),
        f"launch_tab_{token}.ps1",
    )
    try:
        with open(temporary, "w", encoding="utf-8") as handle:
            handle.write(script)
        subprocess.Popen(
            build_tab_command(dir_path, stable_title, temporary),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, ValueError):
        try:
            os.remove(temporary)
        except OSError:
            pass
        return False

    def cleanup() -> None:
        time.sleep(5)
        try:
            os.remove(temporary)
        except OSError:
            pass

    threading.Thread(target=cleanup, daemon=True, name="tab-launch-cleanup").start()
    return True
