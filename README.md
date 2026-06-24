# Agent Launcher

Desktop GUI for launching Claude Code or Hermes in working directories, with a real-time Session Monitor panel and Windows Terminal background customization.

## Project Structure

```text
Agent-Launcher/
├── README.md
├── python/
│   ├── terminal_manager.py          # Application entry point
│   ├── terminal_manager_core.py     # Launcher, tray, terminal focus, base panel
│   ├── session_panel_ui.py          # Compact Session Monitor presentation
│   ├── session_monitor.py           # Session monitoring engine
│   ├── tests/                       # Display-independent helper tests
│   ├── run.bat                      # Double-click launcher
│   └── DEVELOPMENT.md               # Python development notes
├── icon.png                         # Shared application/tray icon source
└── .gitignore
```

## Features

| Feature | Description |
|---|---|
| Agent Launch | Launch Claude Code or Hermes in a selected working directory |
| Directory Tree | Collapsible directory groups |
| Terminal Themes | Acrylic, opacity, or solid Windows Terminal backgrounds |
| Session Monitor | Compact, borderless, always-on-top monitoring panel |
| Reusable Session Cards | Session cards update in place by session ID |
| Context Progress | Green-to-red animated context usage bar |
| Hover Details | Token totals and estimated cost |
| Live Session Filtering | Closed sessions and exited PIDs are removed |
| System Tray | Close minimizes to tray; tooltip shows live totals |
| Terminal Focus | Click a card or complete a task to focus its terminal |
| Edge Snapping | Panel snaps to screen edges while dragging |
| Taskbar Awareness | Resizing respects the Windows work area |

## Quick Start

```batch
cd python
run.bat
```

## Development Checks

```bash
python -m unittest discover -s python/tests -v
python -m py_compile python/terminal_manager.py python/terminal_manager_core.py python/session_panel_ui.py python/session_monitor.py
```

Final visual and Windows Terminal behavior should be validated on Windows.

## Configuration

Edit the Python settings in `python/terminal_manager_core.py`:

```python
BASE_DIRS = [
    r"D:\Quantitative Trading",
    r"D:\University\Kaggle",
]

CLAUDE_ARGS = "--dangerously-skip-permissions"
```
