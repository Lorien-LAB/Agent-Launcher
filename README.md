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
