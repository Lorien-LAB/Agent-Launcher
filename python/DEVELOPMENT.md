# Agent Launcher — Python Edition

## Architecture

```text
terminal_manager.py              # Entry point and override composition
terminal_manager_core.py         # Launcher, tray, terminal integration, base panel
session_panel_ui.py              # Progress animation and live-session filtering
session_panel_layout.py          # 195px panel and two-line collapsed cards
terminal_focus.py                # PID-aware, 64-bit-safe terminal activation
session_monitor.py               # Three-second Claude session scanner
```

## Session Monitor Layout

The panel is 195 logical pixels wide before DPI scaling.

Collapsed cards are 36 logical pixels high and contain exactly two content rows:

1. session name;
2. context progress bar.

There is no status star, RUNNING/IDLE text, branch, agent count, percentage, token text, path, model, or update time in the collapsed state. Status is indicated only by the card border color.

Hover expands a card to 78 logical pixels and reveals:

- RUNNING / DONE / IDLE and context percentage;
- Git branch;
- sub-agent count;
- input/output tokens;
- estimated cost.

The details frame is removed from Tk geometry with `pack_forget()` after collapse. It is not merely hidden behind a short frame, preventing labels from leaking below the card border.

The card viewport starts 48 logical pixels below the header content instead of 64, removing the large gap above the first card at high DPI.

## Hover Animation

Card expansion uses an 180 ms cubic ease-out at approximately 60 FPS.

To reduce trails on the transparent top-level window:

- the panel reserves the final height once before expansion;
- intermediate frames change only card geometry;
- the progress bar is not reset during height ticks;
- details are removed only after collapse completes;
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

A card click passes the complete `SessionSnapshot`, including its PID, rather than only the working directory.

Terminal resolution proceeds in this order:

1. read the Windows process parent map using `CreateToolhelp32Snapshot`;
2. follow the Claude session PID through its ancestor chain;
3. enumerate 64-bit-safe Windows Terminal HWNDs and select the window whose process is in that chain;
4. fall back to the launch-time cwd-to-HWND cache;
5. finally fall back to case-insensitive terminal-title matching.

The activation path temporarily toggles the target through TOPMOST and NOTOPMOST with `SWP_NOMOVE | SWP_NOSIZE`. It then calls `BringWindowToTop` and `SetForegroundWindow`. The terminal's coordinates and dimensions are unchanged, and it is not left permanently always-on-top. A minimized terminal is restored to its saved placement first.

All HWND-related Win32 functions declare pointer-width-safe `ctypes.wintypes.HWND` signatures. This avoids truncating 64-bit window handles.

## Verification

```bash
python -m unittest discover -s python/tests -v
python -m py_compile \
  python/terminal_manager.py \
  python/terminal_manager_core.py \
  python/session_panel_ui.py \
  python/session_panel_layout.py \
  python/terminal_focus.py \
  python/session_monitor.py
```

Final Windows checks should cover:

- 195px layout at the active DPI scale;
- minimal space between the header divider and the first card;
- collapsed cards show only the name and progress bar;
- no metadata leaks outside collapsed borders;
- hover expansion and collapse without trails;
- each card raises its corresponding terminal after an Agent Launcher restart;
- terminal position and dimensions remain unchanged;
- minimized terminal restoration;
- top and bottom panel docking;
- tray shutdown and restart;
- Unicode directory names.
