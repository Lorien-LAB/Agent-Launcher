# Agent Launcher — C# WPF Edition

## Architecture

```
AgentLauncher.csproj       # .NET 8 WPF project
App.xaml / .cs             # Application entry + Catppuccin Mocha global styles
MainWindow.xaml / .cs      # Main window: dir tree, background settings, launch, tray
SessionPanel.xaml / .cs    # Floating borderless Session Monitor with animations

Models/
  SessionSnapshot.cs         # Data classes: SessionSnapshot, AggregateStats

Services/
  SessionMonitorService.cs   # Background thread: ~/.claude/sessions/ + transcript parsing
  TerminalSettingsService.cs # Windows Terminal settings.json read/write
  LauncherService.cs         # wt.exe launching + PID tracking

Helpers/
  NativeMethods.cs           # P/Invoke: DWM, Shell_NotifyIcon, EnumWindows, SetWindowRgn

Converters/
  Converters.cs              # XAML IValueConverter implementations (currently unused inline)
```

## Data Flow

```
ContentRendered event (once, after first paint)
  → PopulateDirectories()
    → BASE_DIRS + Directory.GetDirectories()
    → Populate ListBox with DirItem objects (DisplayMemberPath="DisplayLabel")
    → Header click → toggle _expanded[parentName] → RefreshListDisplay()

SessionMonitorService (Thread, 3s poll)
  → Directory.GetFiles(SESSIONS_DIR, "*.json")
  → Parse PID JSON: sessionId, status, cwd, pid, updatedAt
  → FindTranscript() → projects/<encoded-path>/<uuid>.jsonl
  → ReadMaxContextTokens() → full scan, peak input+cache_read
  → ReadLastModelAndOutput() → tail 64KB
  → ReadGitBranch() → tail 4KB
  → CountSubagents() → subagents/*.meta.json
  → OnUpdate event → MainWindow.OnStatsUpdate()
    → UpdateTrayTooltip()
    → UpdateSessionPanel()
      → PatchValues (same session list → text-only update)
      → Rebuild (different session list → full UI rebuild)

CompositionTarget.Rendering @ 10fps
  → Per-letter wave via Foreground = new SolidColorBrush(PulseColor(...))
  → Star polygon scale pulse (0.85 + 0.15 * sin(phase))
  → Progress bar sawtooth fill (t = (phase * 0.5) % 1)
  → ClockLabel: DateTime.Now every 60 frames
```

## Key Algorithms

### Context Window (abtop-compatible)
```csharp
// For each "assistant" line in transcript JSONL:
int ctx = input_tokens + (cache_read == 0 && cache_creation > 0
    ? cache_creation : cache_read);
maxVal = Math.Max(maxVal, ctx);

// Percentage:
contextPct = Math.Round(inputTokens / (double)modelMaxContext * 100, 1);
```

### Progress Bar Gradient (HSL → RGB)
```csharp
double tVal = i / (nSeg - 1) * Math.Min(pct / 100.0, 1.0);
double hue = (1.0 - tVal) * 0.33;   // 0.33=green → 0.0=red
var (r, g, b) = HsvToRgb(hue, 0.9, 0.95);
brush = new SolidColorBrush(Color.FromRgb((byte)(r*255), (byte)(g*255), (byte)(b*255)));
```

### Wave Animation (per-letter pulse, sin²)
```csharp
double intensity = Math.Pow(Math.Sin(phase), 2);
byte boost = (byte)(170 * intensity);
// Add boost to each RGB channel, clamped to 255
```

## Launch Flow
```
User double-clicks directory
  → Generate temp .ps1: cd '<dir>'; & '<exe>' <args>
  → Process.Start("wt", "--title <title> pwsh -NoExit -File <ps1_path>")
  → PID added to LauncherService.LaunchedPids (ConcurrentDictionary)
  → Task.Run cleanup deletes .ps1 after 3s
```

## Terminal Integration
Reads/writes `%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_*\LocalState\settings.json`
via `System.Text.Json.Nodes.JsonNode` — same JSON structure as Python version.

## System Tray (P/Invoke, no WinForms dependency)
```csharp
Shell_NotifyIcon(NIM_ADD, ref nid)    // Create
Shell_NotifyIcon(NIM_MODIFY, ref nid)  // Update tooltip
Shell_NotifyIcon(NIM_DELETE, ref nid)  // Remove

WndProc handles WM_TRAYICON:
  0x0203 → left double-click → ShowFromTray()
  0x0205 → right-click      → TrackPopupMenu() native context menu
```

## Anti-Flicker Strategy
```csharp
var idKey = string.Join("|", sessions.Select(s => $"{s.SessionId}:{s.Status}"));
bool same = _lastPanelIdKey == idKey;
if (same)
    _sessionPanel.PatchValues(stats);  // Only update TextBlock.Text on percentages
else
    _sessionPanel.Rebuild(stats);      // Full UI reconstruction
```

## Height Calculation (dynamic resize)
```csharp
const double rowHeight = 48; // star(16) + text(~20) + bar(~8) + padding(~4)
neededH = 28 + 1 + 14 + rowHeight * sessionCount + 8;
neededH = Math.Max(80, neededH);
```

## Packaging
```batch
build.bat
# → dotnet publish -c Release -r win-x64 --self-contained false -p:PublishSingleFile=true
# Output: publish/AgentLauncher.exe (~5 MB, requires .NET 8 runtime)
```

## Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| .NET SDK | 8.0 | Build + runtime |
| WPF | built-in | UI framework |
| System.Drawing.Common | 8.0 | Icon loading (PNG→HICON) |
| P/Invoke | built-in | Windows API (DWM, Shell_NotifyIcon, EnumWindows, SetWindowRgn) |

## XAML Theming
All colors defined as `SolidColorBrush` resources in `App.xaml`. Catppuccin Mocha palette:
- `BaseColor` #1E1E2E (window background)
- `CardColor` #181825 (card surfaces)
- `ListBgColor` #313244 (listbox background)
- `TextColor` #CDD6F4 (primary text)
- `MauveColor` #CBA6F7 (accents, separators)

GlowButton style uses `VisualStateManager` for hover/press animations (DropShadowEffect blur + opacity transitions).
