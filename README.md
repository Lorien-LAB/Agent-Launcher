# Agent Launcher

Desktop GUI for launching Claude Code or Hermes in working directories, with a real-time Session Monitor panel and Windows Terminal background customization.

## Project Structure

```text
Agent-Launcher/
├── README.md
├── python/
│   ├── terminal_manager.py          # Application entry point and terminal focus behavior
│   ├── terminal_manager_core.py     # Launcher, tray, terminal focus, base panel
│   ├── session_panel_ui.py          # Progress animation and session filtering
│   ├── session_panel_layout.py      # Narrow card layout and hover details
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
| Session Monitor | 260px compact, borderless, always-on-top monitoring panel |
| Reusable Session Cards | Session cards update in place by session ID |
| Compact Collapsed Cards | Collapsed cards show only session name, state, and context bar |
| Hover Details | Branch, agents, context percentage, token totals, and estimated cost |
| Context Progress | Green-to-red whole-fill animated context usage bar |
| Live Session Filtering | Closed sessions and exited PIDs are removed |
| Geometry-Preserving Focus | Clicking a card raises its terminal without moving or resizing it |
| System Tray | Close minimizes to tray; tooltip shows live totals |
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
python -m py_compile python/terminal_manager.py python/terminal_manager_core.py python/session_panel_ui.py python/session_panel_layout.py python/session_monitor.py
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
