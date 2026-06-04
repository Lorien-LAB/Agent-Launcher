# Agent Launcher

A desktop GUI application for launching AI coding agents (Claude Code, Hermes) in specific working directories, with built-in Windows Terminal transparency customization.

---

## Features

| Feature | Description |
|---------|-------------|
| **Agent Launch** | Launch Claude Code or Hermes in any working directory with one double-click |
| **Directory Tree** | Collapsible section headers (`▸ Quantitative Trading`, `▸ Kaggle`) group subdirectories — click to expand/collapse |
| **Terminal Themes** | Switch between Acrylic (frosted glass), Opacity (pure transparent), or solid background for Windows Terminal |
| **Opacity Slider** | Fine-tune transparency level (0–100%) |
| **DPI Aware** | Auto-scales to any display resolution (96, 120, 144, 192 DPI) |
| **System Tray** | Click the close button → minimizes to tray instead of exiting. Right-click tray icon for Show/Exit |
| **Resizable** | Window can be freely resized; directory list fills available space |

---

## Tech Stack

- **Python 3.14** + **tkinter** (built into Python, zero external GUI dependencies)
- **pystray** — system tray icon
- **Pillow** — tray icon image
- **ttk (clam theme)** — dark UI styling
- **Windows Terminal settings.json** — direct JSON read/write for transparency config

---

## Project Structure

```
terminal-manager/
├── terminal_manager.py   # Main application (~570 lines)
├── run.bat               # Windows launcher (double-click to start)
├── icon.png              # Tray icon
└── README.md             # This file
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
                │  → opens in Windows Term  │
                └──────────────────────────┘
```

### Classes

- **`C`** — Color palette constants (Catppuccin Mocha)
- **`NeonButton(tk.Canvas)`** — Canvas-drawn rounded button with glow border and hover effects
- **`TerminalManager`** — Main application class

### Key Methods (TerminalManager)

| Method | Purpose |
|--------|---------|
| `__init__` | DPI scaling, window setup, tray creation, UI build |
| `build_ui()` | Construct all widgets (header, cards, listbox, buttons) |
| `_refresh_list()` | Rebuild listbox based on expand/collapse state |
| `_on_list_click()` | Toggle parent section expand/collapse |
| `on_launch()` | Launch Claude Code in selected directory |
| `on_launch_hermes()` | Launch Hermes in selected directory |
| `on_save_background()` | Write transparency settings to Windows Terminal config |

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
    --icon icon.png --add-data "icon.png;." terminal_manager.py
```

Output: `dist/AgentLauncher.exe` (~12 MB, no Python required)

---

## Key Bindings

| Input | Action |
|-------|--------|
| Double-click dir | Launch Claude Code |
| Enter | Launch Claude Code |
| Click section header | Expand/collapse |

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

---

## License

MIT
