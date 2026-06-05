# Agent Launcher

A desktop GUI for launching AI coding agents (Claude Code, Hermes) in specific working directories, with a real-time Session Monitor panel, animated progress bars, and Windows Terminal transparency customization.

---

## Features

| Feature | Description |
|---------|-------------|
| **Agent Launch** | Launch Claude Code or Hermes in any directory with one double-click |
| **Directory Tree** | Collapsible section headers group subdirectories — click to expand/collapse |
| **Terminal Themes** | Switch between Acrylic (frosted glass), Opacity (pure transparent), or solid background |
| **Opacity Slider** | Fine-tune transparency level (0–100%) |
| **Session Monitor** | Floating rounded-corner panel tracking all active Claude Code sessions in real-time |
| **Token Tracking** | Per-session `input + cache_read` context algorithm (abtop-compatible) |
| **Animated Progress Bar** | Sawtooth fill animation (0→peak→instant reset) with HSL green-to-red gradient |
| **Per-letter Wave** | Directory name + `RUNNING` status letters individually pulse for busy sessions |
| **Star Indicators** | Four-pointed star icons — glowing/expanding for busy, solid for completed, hollow for idle |
| **Model & Git Badges** | Shows active model (`DSv4`/`Sonnet`/`Opus`), git branch, and sub-agent count |
| **DPI Aware** | Auto-scales to any display resolution (96–192 DPI) |
| **System Tray** | Close → minimize to tray. Tooltip shows live token stats |
| **Anti-flicker** | Panel patches text in-place when only values change; full rebuild only on session list changes |
| **Rounded Corners** | Floating panel uses `SetWindowRgn` for smooth rounded edges; buttons use Canvas arcs |

---

## Tech Stack

- **Python 3.14** + **tkinter** (built into Python)
- **pystray** — system tray icon
- **Pillow** — tray icon image
- **ctypes** — Windows `SetWindowRgn` for rounded panel corners, DPI detection
- **colorsys** — HSL gradient progress bars
- **Windows Terminal settings.json** — direct read/write

---

## Project Structure

```
terminal-manager/
├── terminal_manager.py   # Main application (~670 lines)
├── session_monitor.py    # Monitoring engine (~320 lines)
├── run.bat               # Double-click launcher
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
             │  → _update_tray() (tooltip)
             │  → _update_panel() (floating)
             │
             │  _animate_loop() ← 100ms
             │  → wave labels: per-letter color pulse
             │  → star dots: scale pulse + glow ring
             │  → progress bar: sawtooth fill + gradient
             └── no widget destruction
```

### Classes

| Class | File | Purpose |
|-------|------|---------|
| `C` | `terminal_manager.py` | Color palette (Catppuccin Mocha) |
| `NeonButton(tk.Canvas)` | `terminal_manager.py` | Rounded button with hover glow |
| `TerminalManager` | `terminal_manager.py` | Main app — GUI, tray, panel, animation |
| `SessionMonitor` | `session_monitor.py` | Background thread parsing transcripts |
| `SessionSnapshot` | `session_monitor.py` | Dataclass: one session's stats |
| `AggregateStats` | `session_monitor.py` | Dataclass: totals across sessions |

### Key Methods

| Method | Class | Purpose |
|--------|-------|---------|
| `_create_stats_panel()` | TerminalManager | Floating rounded panel with `SetWindowRgn` |
| `_update_panel()` | TerminalManager | Rebuild or patch session rows |
| `_animate_loop()` | TerminalManager | 100ms loop — wave labels, star dots, bar sawtooth |
| `_pulse_color()` | TerminalManager | `sin^2` color boost for glow effects |
| `scan()` | SessionMonitor | Read `sessions/` + `projects/`, extract stats |
| `_read_max_context_tokens()` | SessionMonitor | Full-file scan: peak `input + cache_read` |
| `_read_git_branch()` | SessionMonitor | Tail read for git branch |
| `_count_subagents()` | SessionMonitor | Count `subagents/*.meta.json` |

---

## Context Window Algorithm (abtop-compatible)

```
For each assistant turn in transcript:
    context_tokens = input_tokens + cache_read_input_tokens
    (if cache_read == 0 and cache_creation > 0: use cache_creation)

context_percent = max(context_tokens) / model_max_context × 100%
```

| Model | Context Window |
|-------|---------------|
| `deepseek-v4-pro` / `[1m]` | 1,000,000 tokens |
| Claude Opus / Sonnet / Haiku | 200,000 tokens |

---

## Animations

| Element | Busy | Completed | Idle |
|---------|------|-----------|------|
| Star icon | Glowing green, scale ±15% | Yellow solid | Hollow gray |
| Directory name | Per-letter wave pulse | Static bold | Static bold |
| Status word | `RUNNING` per-letter wave | `DONE` sparkle | — |
| Progress bar | Sawtooth 0→peak→reset, HSL gradient | — | Static gradient |

---

## How to Package (Standalone .exe)

```powershell
cd terminal-manager
pip install pyinstaller pystray Pillow
python -m PyInstaller --onefile --windowed --name "AgentLauncher" `
    --add-data "icon.png;." --add-data "session_monitor.py;." terminal_manager.py
```

Output: `dist/AgentLauncher.exe` (~30 MB, no Python required)

---

## Key Bindings

| Input | Action |
|-------|--------|
| Double-click dir / Enter | Launch Claude Code |
| Click section header | Expand/collapse |
| Close button | Minimize to tray |
| Right-click tray → Show | Restore window |
| Right-click tray → Exit | Quit application |

---

## Configuration

### Base Directories (`terminal_manager.py`)

```python
BASE_DIRS = [
    r"D:\Quantitative Trading",
    r"D:\University\Kaggle",
]
```

### Agent Paths

```python
CLAUDE_PATH = "C:/Users/Lorien/.local/bin/claude.exe"
CLAUDE_ARGS = "--dangerously-skip-permissions"
HERMES_PATH = "C:/Users/Lorien/AppData/Local/hermes/hermes-agent/venv/Scripts/hermes.exe"
```

### Model Context Windows (`session_monitor.py`)

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
