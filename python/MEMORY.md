# Agent Launcher — Python Edition (tkinter)

## Quick Context for a New Agent

This is the **original Python implementation** of Agent Launcher. It is the mature, daily-driver version.

### Files You Need to Know
```
python/
├── terminal_manager.py   # Main app (~770 lines) — everything lives here
├── session_monitor.py    # Background polling engine (~330 lines)
├── run.bat               # Double-click launcher
├── icon.png              # Tray icon (source PNG)
└── *.md                  # Docs
```

### How to Run
```batch
cd python
run.bat   # launches "pythonw terminal_manager.py"
```

### Current State (2026-06-10)

**Fully working — daily-driver stable.**

**Panel:**
- Top-center default position
- `-alpha 0.94` + `SetWindowRgn` 18px rounded corners
- Real-time clock in header (HH:MM:SS, Consolas 13 bold)
- Pure white text (`fg="#FFFFFF"`), lighter sub-text (`#CCCCDD`)
- Drag with 40px edge snapping, auto-resize height
- No more emoji icon prefix on header title

**Animations:**
- Per-letter wave pulse on busy directory names (sin², dimmer base #D0D0EE)
- Star indicator: green pulsing (busy), yellow solid (newly completed), grey hollow (idle)
- Pill-shaped gradient progress bar (12-segment HSL green→red, rounded both ends)
- Sawtooth fill animation on busy bars

**Click-to-Jump:**
- Recursive `<Button-1>` binding on every row widget
- Matches terminal window by dir basename in title
- Only calls `SetForegroundWindow` — no position/size change

**Launch:**
- Dir basename embedded in `wt --title "Claude Code — dirname"`
- No temp .ps1 — uses `subprocess.Popen(["wt", ..., "-Command", cmd], cwd=dir_path)`
- Cleaner + no file-system temp artifacts

**Tray:**
- pystray with "Show" / "Exit" menu
- Tooltip: active/idle count, token totals, top sessions

**Completion auto-pop:**
- `busy→idle` transition → `SetForegroundWindow` on that session's terminal

### Configuration
```python
BASE_DIRS = [
    r"D:\Quantitative Trading",
    r"D:\University\Kaggle",
    r"D:\Obsidian_Lorien_Lab",
    r"D:\University\比赛\AFAC2026...",
    r"C:\Users\Lorien\terminal-manager",
]
CLAUDE_PATH = "C:/Users/Lorien/.local/bin/claude.exe"
CLAUDE_ARGS = "--dangerously-skip-permissions"  # intentional
HERMES_PATH = ".../hermes.exe"
```

### Key Entry Points
- `TerminalManager.__init__()` → tray, monitor, panel, animation loop
- `_create_stats_panel()` → borderless Toplevel + SetWindowRgn
- `_update_panel()` → rebuild (when session list changes) or patch-only (when only token values change)
- `_animate_loop()` → 100ms timer: wave labels, star dots, pill bars, clock
- `_bring_terminal_to_front(cwd)` → live EnumWindows, title-substring match
- `_draw_pill_bar()` → pill-shaped gradient bar with rounded caps
- `launch_in_terminal()` → cwd-based Popen, dir tag in title
- `SessionMonitor.scan()` → reads sessions/*.json + transcript JSONL

### Differences from C# Version
- Uses `overrideredirect(True)` + `SetWindowRgn` for borderless panel
- System tray via `pystray` library (extra thread)
- Animation via `root.after(100)` timer (not CompositionTarget.Rendering)
- `_wave_bars` tuple: `(bar, bw, fw_base, bh, pct)` — no fill_color stored
- Launch: cwd Popen + `-Command` (C# uses temp .ps1)

### Known Quirks / Gotchas
- `"▸ "` prefix for section headers is 3 bytes — index math uses `[4:]`
- Anti-flicker: session-id+status tuple comparison → patch-only vs rebuild
- Context token algorithm: `input + cache_read` (abtop-compatible)
- Chinese dir names in `~/.claude/projects/` → encoded with dashes
- `pystray` requires separate thread and PIL.Image icon
- Pill bars: `_draw_pill_bar` uses `create_arc` for both caps + 12-segment gradient body
- `-alpha` + `SetWindowRgn` compatible; DWM blur APIs NOT compatible with layered windows
