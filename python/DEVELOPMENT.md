# Agent Launcher — Python Edition

## Architecture

```
terminal_manager.py          # Main GUI (~770 lines)
  ├── C (Color palette)      # Catppuccin Mocha theme (text: #FFFFFF pure white)
  ├── NeonButton             # tk.Canvas rounded button with hover glow
  ├── TerminalManager        # Root class: window, tray, panel, animations
  └── main()                 # Entry point

session_monitor.py           # Monitoring engine (~330 lines)
  ├── SessionMonitor         # Background polling (3s interval)
  ├── SessionSnapshot        # Per-session dataclass
  └── AggregateStats         # Cross-session totals
```

## Data Flow

```
scan_directories()
  → BASE_DIRS + os.listdir()
  → Populate tk.Listbox with section headers + child entries
  → Double-click or Enter → launch_in_terminal()
    → Embed dir basename in window title: "Claude Code — myproject"
    → subprocess.Popen(["wt", "--title", full_title, ...], cwd=dir_path)
    → No temp .ps1 file — uses PowerShell -Command directly

SessionMonitor._loop() (3s poll)
  → os.listdir(~/.claude/sessions/)  → PID JSON files
  → _find_transcript()               → ~/.claude/projects/<encoded-path>/<uuid>.jsonl
  → _read_max_context_tokens()       → full scan, peak input+cache_read
  → _read_last_model_and_output()    → tail 64KB
  → _read_git_branch()               → tail 4KB
  → _count_subagents()               → count subagents/*.meta.json
  → on_update callback               → stats → _update_tray() + _update_panel()

Animation loop @ 100ms via root.after():
  _animate_loop()
    → Per-letter wave (sin² pulse on foreground color)
    → Star polygon scale pulse + glow ring
    → Progress bar sawtooth fill (pill-shaped gradient)
    → Clock update (once/second)
```

## Session Monitor Panel

```
Floating borderless window (overrideredirect):
  - Top-center placement by default
  - -alpha 0.94 (subtle transparency)
  - SetWindowRgn for 18px rounded corners
  - Drag to move, edge snapping (40px)
  - Auto-resize height based on session count

Header:
  - "Session Monitor" title (Segoe UI 12 bold)
  - Real-time clock HH:MM:SS (Consolas 13 bold, right-aligned)

Body rows (max 12):
  - ★ Star indicator: green pulsing (busy), yellow solid (newly completed),
    grey hollow (idle)
  - Directory name: per-letter wave animation when busy
  - Model badge [DSv4/Sonnet/Opus], git branch, sub-agent count
  - Pill-shaped gradient progress bar (green→yellow→red, rounded ends)
  - Percentage label with patch-only anti-flicker update

Click to jump:
  - Click any row → SetForegroundWindow on matching terminal
  - Matches by directory basename embedded in terminal window title
```

## Key Algorithms

### Context Window (abtop-compatible)
```
For each assistant turn in transcript JSONL:
  context = input_tokens + (cache_creation if cache_read==0 else cache_read)
peak = max(context) across all turns
context_pct = peak / model_max_context × 100%
```

### Progress Bar
```python
# Pill shape: two arc semi-circles (left + right caps) + rectangle body
# 12-segment HSL gradient: green(0.33) → yellow → red(0.0)
hue = (1.0 - t_val) * 0.33
hsv_to_rgb(hue, 0.88, 0.94)
# Sawtooth animation: t = (phase * 0.5) % 1, fill width ramps 0→peak
```

### Wave Animation (per-letter pulse)
```python
intensity = math.sin(phase - i * offset) ** 2
boost = int(170 * intensity)
# Add boost to each RGB channel, clamped to 255
```

### Anti-Flicker
```python
id_key = tuple((s.session_id, s.status) for s in stats.sessions)
if same: patch-only (update percentage text labels)
else: full rebuild (destroy and recreate all child widgets)
```

## Launch Flow
```
User double-clicks directory (or presses Enter)
  → Build full_title = "Claude Code — {dir_basename}" (or "Hermes — {dir_basename}")
  → subprocess.Popen(["wt", "--title", full_title, "pwsh", "-NoExit",
      "-Command", f"& '{exe_path}' {args}"], cwd=dir_path)
  → No temp .ps1 — uses cwd parameter (anti-injection)
  → Window title carries dir basename for click-to-jump matching
```

## Terminal Pop-to-Front
```
_LAUNCHED_HWNDS: {cwd: [hwnd]} — tracked by snapshot-diff on launch
_bring_terminal_to_front(cwd=None):
  - cwd given (click): enumerate windows, match dir_tag in title
  - cwd=None (auto-pop): match any Claude/Hermes window
  - Only calls SetForegroundWindow (no ShowWindow/SW_RESTORE)
  - Does NOT change window position or size
```

## Terminal Integration
Reads/writes `%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_*\LocalState\settings.json`
- `profiles.defaults.useAcrylic` + `acrylicOpacity` (0.0–1.0)
- `profiles.defaults.opacity` (0–100)

## Packaging
```powershell
pyinstaller --onefile --windowed --name "AgentLauncher" `
    --add-data "icon.png;." --add-data "session_monitor.py;." terminal_manager.py
# Output: dist/AgentLauncher.exe (~30 MB)
```

## Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| Python | 3.14 | Runtime |
| tkinter | built-in | GUI |
| pystray | latest | System tray |
| Pillow | latest | Tray icon (PNG→ICO) |
| ctypes | built-in | Windows API (SetWindowRgn, EnumWindows, DPI) |
| colorsys | built-in | HSL gradient for progress bars |
