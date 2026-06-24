# Agent Launcher — C# WPF Edition

## Quick Context for a New Agent

This is the **C# 12 / .NET 8 WPF port** of Agent Launcher. It is functional but less battle-tested than the Python original.

### Files You Need to Know
```
csharp/AgentLauncher/
├── AgentLauncher.csproj              # .NET 8 WPF project — add packages/usings here
├── App.xaml / App.xaml.cs            # Application entry, Catppuccin Mocha brushes
├── MainWindow.xaml / MainWindow.xaml.cs  # Main window (220 lines XAML + 440 lines code-behind)
├── SessionPanel.xaml / SessionPanel.xaml.cs  # Floating monitor (55 lines XAML + 520 lines code-behind)
├── Models/SessionSnapshot.cs         # Data classes
├── Services/SessionMonitorService.cs # Background polling (~330 lines)
├── Services/TerminalSettingsService.cs  # WT settings.json read/write
├── Services/LauncherService.cs       # Process.Start("wt") + PID tracking
├── Helpers/NativeMethods.cs          # All P/Invoke (DWM, Shell_NotifyIcon, EnumWindows, etc.)
├── Converters/Converters.cs          # XAML value converters (unused inline currently)
├── Resources/icon.ico                # Tray icon
├── icon.png                          # Source PNG for tray icon
├── run.bat                           # dotnet run launcher
└── build.bat                         # dotnet publish → standalone .exe
```

### How to Run
```batch
cd csharp\AgentLauncher
run.bat   # dotnet run --project AgentLauncher.csproj
```

### Build Status
- **0 errors, 0 warnings** (as of 2026-06-10)
- Target: `net8.0-windows10.0.22621.0`
- Depends on `System.Drawing.Common 8.0.0` (for icon loading)
- No WinForms dependency (tray is pure P/Invoke `Shell_NotifyIcon`)

### Current State (2026-06-10)

**Working:**
- Main window renders with Catppuccin Mocha theme
- Directory tree with collapsible sections (click header toggles children)
- Background mode radio buttons (acrylic/opacity/none) + slider
- Save button writes Windows Terminal `settings.json`
- Claude Code / Hermes launch via Windows Terminal
- System tray icon with tooltip (updates every 3s with session stats)
- Session Monitor floating panel (borderless, topmost, 0.92 opacity)
- Session scanning (reads `~/.claude/sessions/*.json` + transcript JSONL)
- Context token calculation (abtop algorithm)
- Model badges, git branch, sub-agent count
- Height auto-resize per session count
- Live clock (`HH:mm:ss`) in panel header

**Working Animations:**
- Per-letter wave pulse on directory name and RUNNING status (busy sessions)
- Star polygon scale pulse + glow ring
- Progress bar sawtooth fill with HSL gradient

**Known Issues / Quirks:**
- **No rounded corners on the outer window edge** — `SetWindowRgn` was removed because it conflicts with `AllowsTransparency="True"`. The XAML `Border.CornerRadius="18"` only rounds the inner content. The transparent window edge shows a faint square outline against bright backgrounds. Options: (a) accept it, (b) try DWM corner preference on Win11, or (c) switch to `AllowsTransparency="False"` + opaque background + `SetWindowRgn`.
- **Tray context menu uses native `TrackPopupMenu`** — works but feels slightly inconsistent with modern Windows. WPF `ContextMenu` doesn't position correctly for tray notifications.
- **No "DONE" sparkle animation** — completed sessions get yellow star + static "DONE" text. The Python version has per-letter sparkle.
- **Slider width relies on Grid `*` column** — do NOT move it back into a `StackPanel` or it will collapse.
- **`ContentRendered` is the correct init hook** — `Loaded` fires too early (panel created before HWND ready). Do not switch back.
- **No emoji anywhere in XAML** — WPF renders colored emoji inconsistently. All button labels and radio buttons use plain text.

### Key Entry Points
- `MainWindow()` constructor → `ContentRendered` event → `PopulateDirectories()`, `CreateSessionPanel()`, start monitor
- `SessionPanel.Rebuild(AggregateStats)` → full UI reconstruction per scan
- `SessionPanel.PatchValues(AggregateStats)` → text-only update (anti-flicker)
- `CompositionTarget.Rendering` → animation loop @ 10fps (throttled by `_frameCount % 6`)
- `SessionMonitorService.Scan()` → reads sessions, updates `_sessionTotals` cache

### Configuration (change directly in `MainWindow.xaml.cs`)
```csharp
private static readonly string[] BaseDirs = { ... };  // Line 26
private static readonly string ClaudeArgs = "--dangerously-skip-permissions";  // LauncherService.cs
```

### Differences from Python Version
- **Tray**: P/Invoke `Shell_NotifyIcon` instead of `pystray` (no external dependency, no extra thread)
- **Panel border**: WPF `WindowStyle="None"` + `AllowsTransparency="True"` vs Python `overrideredirect(True)` + `SetWindowRgn`
- **Animations**: `CompositionTarget.Rendering` (60fps hardware) vs `root.after(100)` (100ms timer)
- **Anti-flicker**: Same algorithm — session-id tuple comparison + patch-only mode
- **DPI**: Handled by WPF natively (Python uses manual `get_dpi_scale()`)
- **Build output**: ~75KB DLL + ~5MB published .exe vs ~30MB PyInstaller bundle

### Development Tips
- Avoid `object` initializer for `using` declarations — `System.Drawing.Icon` and `Bitmap` need explicit `using` blocks or they leak GDI handles
- The `NOTIFYICONDATA.cbSize` must be `Marshal.SizeOf<NOTIFYICONDATA>()`, not a hardcoded number (struct size varies by Windows version)
- `TrackPopupMenu` **requires** `SetForegroundWindow(hwnd)` before calling, or the menu won't dismiss when clicking elsewhere
- To debug Session Panel positioning: check `SystemParameters.WorkArea` — this is the reliable replacement for the broken `SPI_GETWORKAREA` P/Invoke
- Progress bar segments are `Rectangle` elements added to a `Canvas` — background rect is index 0, gradient segments are added/removed at indices 1+
