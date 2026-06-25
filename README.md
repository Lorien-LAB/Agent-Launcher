# Agent Launcher

Python desktop launcher with a compact real-time Session Monitor.

## Session Monitor

- 195 logical pixels wide.
- Collapsed cards show only the session name and context progress bar.
- Hover reveals branch, agents, state, context percentage, token totals, and cost.
- Closed sessions and exited PIDs are removed.
- Clicking a card raises the matching Windows Terminal without moving or resizing it.

## Run

```batch
cd python
run.bat
```

## Checks

```bash
python -m unittest discover -s python/tests -v
python -m py_compile python/terminal_manager.py python/terminal_manager_core.py python/session_panel_ui.py python/session_panel_layout.py python/terminal_focus.py python/session_monitor.py
```
