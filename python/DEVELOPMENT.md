# Agent Launcher — Python Edition

## Architecture

```
terminal_manager.py
  ├── C                       # Launcher and Session Monitor palettes
  ├── NeonButton              # Main-window Canvas button
  ├── SessionCard             # Reusable monitor card with hover/animation
  ├── TerminalManager         # Main window, tray, card registry, panel sizing
  └── main()

session_monitor.py
  ├── SessionMonitor          # Background polling every 3 seconds
  ├── SessionSnapshot         # One session's metrics
  └── AggregateStats          # Cross-session totals
```

`SessionMonitor` remains a data source. All tkinter work is marshalled onto the main thread through `root.after()`.

## Monitor Data Flow

```
SessionMonitor.scan()
  → read ~/.claude/sessions/*.json
  → locate ~/.claude/projects/<encoded-path>/<session>.jsonl
  → collect model, tokens, context %, branch, subagents and update time
  → AggregateStats callback
  → TerminalManager._update_tray(stats)
  → TerminalManager._update_panel(stats)
      ├── update two-row header summary
      ├── detect busy → idle and create 5-second DONE state
      ├── create/update/remove SessionCard by session_id
      └── schedule one coalesced panel resize
```

## SessionCard

Each card owns its widgets and delayed callbacks. Its public presentation interface is:

```python
card.update_snapshot(snapshot, display_state)
card.set_hovered(True or False)
card.animate(phase, now)
card.grid_at(row)
card.destroy()
```

The manager stores cards in:

```python
self._session_cards: dict[str, SessionCard]
```

Normal polling updates all displayed values in place. Widgets are created only for new sessions and destroyed only when sessions disappear.

## Panel Layout

- Logical width: 380 px before DPI scaling, defined by `SESSION_PANEL_WIDTH`.
- Borderless, topmost `Toplevel`, alpha 0.94.
- Native rounded clipping through `SetWindowRgn`.
- Header row 1: title and clock.
- Header row 2: active, idle, and total-token summaries.
- Only the header starts dragging; cards remain clickable.
- Card viewport scrolls with the mouse wheel when content exceeds the work area.
- Resizing preserves top or bottom pinning and reuses the same width constant.

## Card Layout

Collapsed cards show:

1. Status star, directory, and RUNNING/DONE/IDLE.
2. Model, branch, sub-agent count, and context percentage.
3. Fixed-width gradient context bar.

Hover expands one card at a time and reveals:

- cumulative input/output tokens;
- estimated cost;
- working directory;
- human-readable update age.

Hover entry waits 80 ms and leave waits 120 ms. Card destruction cancels all pending `after()` callbacks.

## Animation

The global loop runs every 100 ms and performs only lightweight drawing:

- clock refresh once per second;
- subtle header scan line;
- running status-star and border breathing;
- moving highlight over a fixed-width gradient bar;
- warning endpoint pulse above 95% context.

Idle, non-hovered cards avoid continuous redraw. The progress fill width always equals the true context percentage and never resets to zero.

## DONE State

A `busy → idle` transition:

1. stores `time.monotonic() + 5` in `_done_until`;
2. displays a yellow DONE card state;
3. schedules terminal focus after 500 ms;
4. returns to IDLE after the deadline;
5. immediately returns to RUNNING if the session becomes busy again.

## Launch Flow

```
select directory
  → launch_in_terminal()
  → create temporary PowerShell script
  → wt -w new -d <path> --title "Claude Code — <dir>" pwsh -NoExit -File <script>
  → remove temporary script after 5 seconds
  → snapshot-diff Windows Terminal HWNDs for click-to-focus
```

`terminal_manager.py` must import `time`; both temporary-file cleanup and HWND tracking use `time.sleep()`.

## Verification

Automated checks:

```bash
python -m unittest discover -s python/tests -v
python -m py_compile python/terminal_manager.py python/session_monitor.py
```

A headless Xvfb smoke run can validate tkinter card creation and reconciliation on Linux, but final acceptance still requires Windows testing for:

- Windows Terminal launch/focus;
- top and bottom panel pinning;
- high-DPI rendering;
- Chinese paths;
- tray shutdown;
- DONE auto-pop behavior.
