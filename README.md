# Agent Launcher

A desktop GUI application for launching AI coding agents (Claude Code, Hermes) in specific working directories, with real-time session monitoring and Windows Terminal transparency customization.

---

## Features

| Feature | Description |
|---------|-------------|
| **Agent Launch** | Launch Claude Code or Hermes in any working directory with one double-click |
| **Directory Tree** | Collapsible section headers (`▸ Quantitative Trading`, `▸ Kaggle`) group subdirectories — click to expand/collapse |
| **Terminal Themes** | Switch between Acrylic (frosted glass), Opacity (pure transparent), or solid background for Windows Terminal |
| **Opacity Slider** | Fine-tune transparency level (0–100%) |
| **Session Monitor** | Floating desktop panel showing all active Claude Code sessions in real-time |
| **Token Tracking** | Per-session input/output token counts with `input + cache_read` context algorithm (abtop-compatible) |
| **Context Progress Bar** | HSL gradient bar — green → yellow → orange → red as context fills |
| **Status Animation** | Per-letter wave highlight for busy sessions (`RUNNING`), sparkle for just-completed (`DONE`) |
| **Model & Git Badges** | Shows active model (DSv4/Opus/Sonnet), git branch, and sub-agent count per session |
| **DPI Aware** | Auto-scales to any display resolution (96, 120, 144, 192 DPI) |
| **System Tray** | Click the close button → minimizes to tray instead of exiting. Right-click tray icon for Show/Exit. Tray tooltip shows aggregate token stats |
| **Resizable** | Window can be freely resized; directory list fills available space |
| **Anti-flicker** | Panel patches text in-place when only numeric values change; rebuilds widgets only on session list changes |

---

## Tech Stack

- **Python 3.14** + **tkinter** (built into Python, zero external GUI dependencies)
- **pystray** — system tray icon
- **Pillow** — tray icon image
- **ttk (clam theme)** — dark UI styling
- **colorsys** — HSL gradient progress bars
- **Windows Terminal settings.json** — direct JSON read/write for transparency config

---

## Project Structure

```
terminal-manager/
├── terminal_manager.py   # Main application (~580 lines, GUI + tray + panel)
├── session_monitor.py    # Monitoring engine (~330 lines, transcript parsing)
├── run.bat               # Windows launcher (double-click to start)
├── icon.png              # Tray icon
├── .gitignore
└── README.md
```

---

## Architecture

### Data Flow

```
                ┌──────────────────────────┐
                │     scan_directories()    │
                │  → D:\Quantitative Trading│
                │  → D:\University\Kaggle   │
                └──────────┬───────────────┘
                           │
                           ▼
                ┌──────────────────────────┐
                │      Listbox (dir_list)   │
                │  ▸ section headers        │
                │    📁 subdirectory items   │
                └──────────┬───────────────┘
                           │ double-click / Enter
                ┌──────────▼───────────────┐
                │    launch_in_terminal()   │
                │  → write temp .ps1 script │
                │  → wt.exe -File script    │
                └──────────────────────────┘

                ┌──────────────────────────┐
                │    SessionMonitor.scan()  │  ← every 3s
                │  → ~/.claude/sessions/    │
                │  → ~/.claude/projects/    │
                └──────────┬───────────────┘
                           │
                           ▼
                ┌──────────────────────────┐
             ┌─ │  _on_stats_update()       │
             │  └──────────────────────────┘
             │  → _update_tray()  (tooltip)
             │  → _update_panel() (floating)
             │
             │  _animate_loop()  ← 120ms
             │  → _pulse_color() on existing labels
             └── no widget destruction
```

### Classes

| Class | File | Purpose |
|-------|------|---------|
| `C` | `terminal_manager.py` | Color palette constants (Catppuccin Mocha) |
| `NeonButton(tk.Canvas)` | `terminal_manager.py` | Canvas-drawn rounded button with glow border and hover effects |
| `TerminalManager` | `terminal_manager.py` | Main application — GUI, tray, panel, animation |
| `SessionMonitor` | `session_monitor.py` | Background thread polling `~/.claude/sessions/` and parsing transcript JSONL |
| `SessionSnapshot` | `session_monitor.py` | Dataclass for one session's stats |
| `AggregateStats` | `session_monitor.py` | Dataclass for totals across all sessions |

### Key Methods (TerminalManager)

| Method | Purpose |
|--------|---------|
| `__init__` | DPI scaling, window setup, tray creation, monitor start, UI build |
| `build_ui()` | Construct all widgets (header, cards, listbox, buttons) |
| `_refresh_list()` | Rebuild listbox based on expand/collapse state |
| `on_launch()` | Launch Claude Code in selected directory |
| `on_launch_hermes()` | Launch Hermes in selected directory |
| `on_save_background()` | Write transparency settings to Windows Terminal config |
| `_create_stats_panel()` | Create borderless floating stats panel (bottom-right) |
| `_update_panel()` | Rebuild or patch session stats rows |
| `_animate_loop()` | 120ms loop: pulse wave labels and dot colors in-place |
| `_update_tray()` | Update tray tooltip with aggregate token stats |

### Key Functions (session_monitor.py)

| Function | Purpose |
|----------|---------|
| `scan()` | Read all `sessions/<pid>.json`, find transcripts, extract stats |
| `_read_max_context_tokens()` | Full-file scan: peak `input_tokens + cache_read_input_tokens` per abtop algorithm |
| `_read_last_model_and_output()` | Tail 64KB read for model name and latest output tokens |
| `_read_git_branch()` | Tail 4KB read for git branch field |
| `_count_subagents()` | Count `subagents/*.meta.json` files per session |
| `_project_path()` | Encode filesystem path to `.claude/projects/` subdirectory name |

### Context Window Calculation (abtop algorithm)

```
For each assistant turn in transcript:
    context_tokens = input_tokens + cache_read_input_tokens
    (if cache_read == 0 and cache_creation > 0: use cache_creation instead)

context_percent = max(context_tokens) / model_max_context × 100%
```

DeepSeek V4 models are detected as 1,000,000 token context window. Other models default to 200,000.

---

### Windows Terminal Integration

Reads/writes `%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_*\LocalState\settings.json`:

```json
{
  "profiles": {
    "defaults": {
      "useAcrylic": true,
      "acrylicOpacity": 0.33
    }
  }
}
```

---

## How to Package (Standalone .exe)

```powershell
cd terminal-manager
pip install pyinstaller pystray Pillow
pyinstaller --onefile --windowed --name "AgentLauncher" `
    --icon icon.png --add-data "icon.png;." --add-data "session_monitor.py;." terminal_manager.py
```

Output: `dist/AgentLauncher.exe` (~30 MB, no Python required)

---

## Key Bindings

| Input | Action |
|-------|--------|
| Double-click dir | Launch Claude Code |
| Enter | Launch Claude Code |
| Click section header | Expand/collapse |
| Close button | Minimize to tray |
| Right-click tray → Show | Restore window |
| Right-click tray → Exit | Quit application |

---

## Configuration

### Adding/Removing Base Directories

Edit `BASE_DIRS` in `terminal_manager.py`:

```python
BASE_DIRS = [
    r"D:\Quantitative Trading",
    r"D:\University\Kaggle",
]
```

### Changing Agent Paths

```python
CLAUDE_PATH = "C:/Users/Lorien/.local/bin/claude.exe"
CLAUDE_ARGS = "--dangerously-skip-permissions"
HERMES_PATH = "C:/Users/Lorien/AppData/Local/hermes/hermes-agent/venv/Scripts/hermes.exe"
```

### Model Context Windows

Edit `MODEL_CONTEXT` in `session_monitor.py` to add new models:

```python
MODEL_CONTEXT = {
    "deepseek-v4-pro": 1_000_000,
    "claude-sonnet-4-20250514": 200_000,
    ...
}
```

---

## License

MIT
