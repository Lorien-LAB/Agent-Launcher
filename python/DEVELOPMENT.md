# Agent Launcher — Python Edition

## Architecture

```text
terminal_manager.py              # Entry point and geometry-preserving focus
terminal_manager_core.py         # Launcher, tray, terminal lookup, base panel
session_panel_ui.py              # Progress animation and session filtering
session_panel_layout.py          # 260px layout and hover-only metadata
session_monitor.py               # Three-second Claude session scanner
```

## Session Monitor Layout

The panel is 260 logical pixels wide before DPI scaling.

Collapsed cards are 44 logical pixels high and show only:

1. status indicator;
2. session name;
3. RUNNING / DONE / IDLE;
4. context progress bar.

Hover expands a card to 82 logical pixels and reveals:

- Git branch;
- sub-agent count;
- context percentage;
- input/output tokens;
- estimated cost.

Long branch names are truncated so the percentage remains visible. Model, working directory, and update age are not rendered.

## Hover Animation

Card expansion uses an 180 ms cubic ease-out at approximately 60 FPS.

To reduce trails on the transparent top-level window:

- the panel reserves the final height once before expansion;
- intermediate frames change only card geometry;
- the progress bar is not reset during height ticks;
- the panel shrinks only after collapse completes;
- rounded clipping is not recreated on every animation frame.

## Progress Bar

The context bar uses filled ovals and a center rectangle, avoiding radial straight edges from Canvas pie sectors.

- Gradient: green → yellow → orange → red.
- RUNNING: the whole filled gradient advances left-to-right and restarts.
- IDLE and DONE: the true context width is shown statically.
- Above 95%: the endpoint receives a warning pulse.

## Live Session Filtering

Sessions are omitted when:

- metadata status is closed, closing, terminated, exited, or dead; or
- the recorded process ID no longer exists.

## Card Click Behavior

Clicking a session card raises its matching Windows Terminal window.

The Win32 focus path uses `SetWindowPos` with `SWP_NOMOVE | SWP_NOSIZE`, followed by `BringWindowToTop` and `SetForegroundWindow`. This changes only Z order and activation. It does not change the terminal's coordinates or size. A minimized terminal is restored to its previous placement before being raised.

Terminal matching still uses the launch-time cwd-to-HWND cache, with a Windows Terminal title lookup fallback.

## Verification

```bash
python -m unittest discover -s python/tests -v
python -m py_compile \
  python/terminal_manager.py \
  python/terminal_manager_core.py \
  python/session_panel_ui.py \
  python/session_panel_layout.py \
  python/session_monitor.py
```

Final Windows checks should cover:

- 260px layout at the active DPI scale;
- hover expansion and collapse without trails;
- branch/agents/percentage visible only after expansion;
- card click raises the matching terminal without moving or resizing it;
- minimized terminal restoration;
- top and bottom panel docking;
- tray shutdown and restart;
- Unicode directory names.
