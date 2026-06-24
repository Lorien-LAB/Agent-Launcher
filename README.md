# Agent Launcher

Desktop GUI for launching Claude Code / Hermes in working directories, with a real-time Session Monitor panel, animated progress bars, and Windows Terminal transparency customization.

---

## Project Structure

```
terminal-manager/
├── README.md                          # This file
│
├── python/                            # Python 3.14 + tkinter edition
│   ├── terminal_manager.py            # Main application
│   ├── session_monitor.py             # Monitoring engine
│   ├── run.bat                        # Double-click launcher
│   ├── .gitignore
│   └── DEVELOPMENT.md                 # Python dev docs
│
├── csharp/AgentLauncher/              # C# 12 / .NET 8 WPF edition
│   ├── AgentLauncher.csproj           # Project file
│   ├── App.xaml / .cs                 # Entry + global styles
│   ├── MainWindow.xaml / .cs          # Main window
│   ├── SessionPanel.xaml / .cs        # Floating Session Monitor
│   ├── Models/SessionSnapshot.cs      # Data models
│   ├── Services/                      # SessionMonitor, TerminalSettings, Launcher
│   ├── Helpers/NativeMethods.cs       # P/Invoke
│   ├── Converters/                    # XAML converters
│   ├── Resources/icon.ico             # Tray icon
│   ├── run.bat                        # dotnet run launcher
│   ├── build.bat                      # Publish standalone .exe
│   └── DEVELOPMENT.md                 # C# dev docs
│
├── icon.png                           # Tray icon (source PNG)
└── .gitignore
```

## Two Implementations

| | Python | C# WPF |
|------|--------|--------|
| **Language** | Python 3.14 | C# 12 / .NET 8 |
| **Framework** | tkinter (built-in) | WPF (Windows-native) |
| **Tray** | pystray | P/Invoke Shell_NotifyIcon |
| **Packaging** | PyInstaller | dotnet publish |
| **.exe size** | ~30 MB | ~5 MB |
| **Best for** | Quick iteration, no SDK needed | Native Win11 look, smaller footprint |

Both editions share identical features and monitor the same `~/.claude/sessions/` data.

## Features

| Feature | Description |
|---------|-------------|
| **Agent Launch** | Double-click a directory to launch Claude Code or Hermes in Windows Terminal |
| **Directory Tree** | Collapsible section headers group subdirectories |
| **Terminal Themes** | Acrylic (frosted glass), Opacity (transparent), or solid background |
| **Opacity Slider** | 0–100% transparency control |
| **Session Monitor** | Floating borderless panel, always on top, rounded corners |
| **Token Tracking** | `input + cache_read` context algorithm (abtop-compatible) |
| **Animated Progress Bar** | Sawtooth fill + HSL green→red gradient |
| **Per-letter Wave** | Directory name + RUNNING/DONE status letters individually pulse |
| **Star Indicators** | Four-pointed polygon: glowing busy, yellow completed, hollow idle |
| **Model & Git Badges** | DSv4 / Sonnet / Opus, git branch, sub-agent count |
| **System Tray** | Close → minimize to tray. Tooltip shows live stats |
| **Anti-flicker** | Text-only patch when only token values change |
| **Terminal Pop-to-Front** | Completed session → terminal window brought to foreground |
| **Edge Snapping** | Panel drag snaps to screen edges (40px) |
| **Taskbar Aware** | WorkArea-based positioning, auto-hide support |

## Quick Start

### Python
```batch
cd python
run.bat
```

### C# WPF
```batch
cd csharp\AgentLauncher
run.bat
```

## Key Bindings

| Input | Action |
|-------|--------|
| Double-click directory | Launch Claude Code |
| Click section header | Expand/collapse |
| Close button | Minimize to tray |
| Tray double-click | Restore window |
| Tray right-click → Exit | Quit |

## Configuration

### Python: `terminal_manager.py`
```python
BASE_DIRS = [
    r"D:\Quantitative Trading",
    r"D:\University\Kaggle",
    ...
]
CLAUDE_ARGS = "--dangerously-skip-permissions"
```

### C#: `MainWindow.xaml.cs`
```csharp
private static readonly string[] BaseDirs = { ... };
private static readonly string ClaudeArgs = "--dangerously-skip-permissions";
```
