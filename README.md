# Agent Launcher

Desktop GUI for launching Claude Code / Hermes in working directories, with a real-time Session Monitor panel and Windows Terminal transparency customization.

---

## Project Structure

```
Agent-Launcher/
├── README.md
├── docs/superpowers/                 # Approved UI spec and implementation plan
├── python/                           # Python 3.14 + tkinter edition
│   ├── terminal_manager.py           # Main application + SessionCard UI
│   ├── session_monitor.py            # Monitoring engine
│   ├── tests/                        # Display-independent panel helper tests
│   ├── run.bat                       # Double-click launcher
│   ├── .gitignore
│   └── DEVELOPMENT.md                # Python development notes
├── csharp/AgentLauncher/             # C# 12 / .NET 8 WPF edition
├── icon.png                          # Tray icon source
└── .gitignore
```

## Two Implementations

| | Python | C# WPF |
|------|--------|--------|
| **Language** | Python 3.14 | C# 12 / .NET 8 |
| **Framework** | tkinter | WPF |
| **Tray** | pystray | P/Invoke Shell_NotifyIcon |
| **Packaging** | PyInstaller | dotnet publish |
| **Best for** | Quick iteration | Native Windows UI |

Both editions monitor the same `~/.claude/sessions/` data. Their presentation can evolve independently.

## Features

| Feature | Description |
|---------|-------------|
| **Agent Launch** | Double-click a directory to launch Claude Code or Hermes in Windows Terminal |
| **Directory Tree** | Collapsible section headers group subdirectories |
| **Terminal Themes** | Acrylic, opacity, or solid Windows Terminal backgrounds |
| **Session Monitor** | Floating, borderless, rounded, always-on-top panel |
| **Reusable Session Cards** | Cards are reconciled by session ID and updated in place without full panel rebuilds |
| **Hover Details** | Hover one card to reveal input/output tokens, estimated cost, path, and update age |
| **Gradient Context Bar** | Fixed true-width green→yellow→orange→red gradient with a moving running-state highlight |
| **Status Treatment** | Pulsing RUNNING, temporary five-second DONE, and subdued IDLE states |
| **Model & Git Badges** | Compact model, branch, and sub-agent metadata |
| **Scrollable Card Area** | Up to 12 cards remain accessible on shorter screens |
| **System Tray** | Close minimizes to tray; tooltip shows live totals |
| **Terminal Pop-to-Front** | Completed session brings its matching terminal to the foreground |
| **Edge Snapping** | Header drag snaps the panel to screen edges |
| **Taskbar Aware** | Top/bottom pinning respects the Windows work area |

## Quick Start

### Python

```batch
cd python
run.bat
```

### C# WPF

```batch
cd csharp\AgentLauncher
run.bat
```

## Python Checks

```bash
python -m unittest discover -s python/tests -v
python -m py_compile python/terminal_manager.py python/session_monitor.py
```

The final visual validation must be performed on Windows because the launcher uses Windows Terminal and Win32 APIs.

## Key Interactions

| Input | Action |
|-------|--------|
| Double-click directory | Launch Claude Code |
| Click section header | Expand/collapse |
| Drag Session Monitor header | Move/snap the floating panel |
| Hover session card | Expand details |
| Click session card | Focus matching terminal |
| Mouse wheel over cards | Scroll the session list |
| Close button | Minimize to tray |
| Tray right-click → Exit | Quit |

## Configuration

### Python: `python/terminal_manager.py`

```python
BASE_DIRS = [
    r"D:\Quantitative Trading",
    r"D:\University\Kaggle",
    # ...
]
CLAUDE_ARGS = "--dangerously-skip-permissions"
```
