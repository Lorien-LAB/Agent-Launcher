# Agent Launcher — Python Edition

## Architecture

```
terminal_manager.py              # Thin entry point and compatibility exports
terminal_manager_core.py         # Launcher, tray, terminal focus, base panel
session_panel_ui.py              # Compact SessionCard and animation overrides
session_monitor.py               # Three-second Claude session scanner
```

The split keeps launcher and Windows Terminal behavior stable while allowing the Session Monitor presentation to evolve independently.

## Session Monitor Data Flow

```
SessionMonitor.scan()
  → AggregateStats
  → session_panel_ui._filter_live_stats()
      ├── remove closed/terminated statuses
      └── remove sessions whose PID no longer exists
  → tray summary
  → TerminalManager._update_panel()
      ├── reconcile SessionCard objects by session_id
      └── schedule one coalesced panel resize
```

## Panel Layout

- Logical width: 380 px before DPI scaling (`SESSION_PANEL_WIDTH`).
- Borderless, always-on-top `Toplevel`, alpha 0.94.
- Two-row header with clock and aggregate counts.
- Mouse-wheel card viewport for short screens.
- Only the header initiates panel dragging.
- Up to 12 live sessions are displayed.

## Compact SessionCard

Collapsed height is 56 logical pixels, just enough for:

1. status star, session name, and RUNNING/DONE/IDLE;
2. Git branch, sub-agent count, and context percentage;
3. the context progress bar.

The state label uses the same 11-point bold Consolas size as the session name.

Hover expands the card to 80 logical pixels and shows only cumulative input/output tokens and estimated cost. Model, full path, and update age are intentionally not rendered.

## Progress Bar

The progress bar uses filled ovals plus a center rectangle, rather than pie arcs. This avoids the visible radial straight edges produced by Canvas arc sectors.

- Gradient remains green → yellow → orange → red.
- Idle and DONE states show the true context width.
- RUNNING restores the original whole-fill sawtooth animation: the entire gradient grows from left to right up to the true context percentage, then restarts.
- A subtle endpoint pulse remains above 95% context.

## Smooth Hover Animation

Card expansion uses an 180 ms cubic ease-out at roughly 60 FPS.

To avoid trails on the transparent top-level window:

- expansion reserves the final panel height once before the card animation;
- intermediate frames change only the card height and redraw only its border;
- the progress bar is not reset during height ticks;
- collapse shrinks the outer panel only after the card reaches its collapsed height;
- `SetWindowRgn` is therefore not recreated on every animation frame.

## DONE State

A `busy → idle` transition still:

1. displays a yellow DONE state for five seconds;
2. schedules matching terminal focus;
3. returns to IDLE unless the session becomes busy again.

A session disappears completely once its process exits or its metadata status becomes closed/terminated.

## Verification

```bash
python -m unittest discover -s python/tests -v
python -m py_compile \
  python/terminal_manager.py \
  python/terminal_manager_core.py \
  python/session_panel_ui.py \
  python/session_monitor.py
```

Final acceptance still requires Windows desktop checks for DPI rendering, Windows Terminal focus, tray shutdown, top/bottom docking, Unicode paths, and visual confirmation that hover animation leaves no trails.
