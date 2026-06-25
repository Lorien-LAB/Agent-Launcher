# Agent Launcher

Desktop GUI for launching Claude Code or Hermes in working directories, with a real-time Session Monitor panel and Windows Terminal background customization.

## Project Structure

```text
Agent-Launcher/
├── README.md
├── python/
│   ├── terminal_manager.py
│   ├── terminal_manager_core.py
│   ├── session_panel_ui.py
│   ├── session_panel_layout.py
│   ├── terminal_focus.py
│   ├── session_monitor.py
│   ├── tests/
│   ├── run.bat
│   └── DEVELOPMENT.md
├── icon.png
└── .gitignore
```

## Current Session Monitor

- 195 logical pixels wide before DPI scaling.
- Collapsed cards show only the session name and context progress bar.
- Branch, agents, state, percentage, token totals, and cost appear only after hover expansion.
- Closed sessions and exited PIDs are removed.
- Clicking a card resolves the matching Windows Terminal from the session PID and raises it without moving or resizing the window.

## Quick Start

```batch
cd python
run.bat
```

## Development Checks

```bash
python -m unittest discover -s python/tests -v
python -m py_compile python/terminal_manager.py python/terminal_manager_core.py python/session_panel_ui.py python/session_panel_layout.py python/terminal_focus.py python/session_monitor.py
```
