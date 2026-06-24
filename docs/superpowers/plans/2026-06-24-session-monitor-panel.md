# Session Monitor Panel Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Replace rebuilt session rows with reusable futuristic `SessionCard` components that support complete in-place updates, hover details, fixed-width gradient progress bars with moving highlights, and reliable panel resizing.

**Architecture:** Keep `SessionMonitor` as the existing three-second data source. Add a `SessionCard` presentation component inside `python/terminal_manager.py`, and let `TerminalManager` reconcile cards by `session_id`, own temporary DONE state, update the two-row header, and resize the rounded floating window. Pure formatting and state helpers remain module-level so they can be tested without a Windows display.

**Tech Stack:** Python 3.14, tkinter/Canvas, ctypes Win32 APIs, unittest, pystray, Pillow.

---

## File map

- Modify: `python/terminal_manager.py` — panel helpers, `SessionCard`, header, keyed reconciliation, hover/animation, scrolling, and lifecycle cleanup.
- Create: `python/tests/test_session_panel_helpers.py` — display-independent tests for formatting, state, thresholds, and progress geometry.
- Modify: `README.md` — update panel appearance and interaction documentation.
- Modify: `python/DEVELOPMENT.md` — document architecture and verification.
- Add: `docs/superpowers/specs/2026-06-24-session-monitor-panel-design.md` — approved specification.
- Add: `docs/superpowers/plans/2026-06-24-session-monitor-panel.md` — this plan.

## Task 1: Add display-independent helper functions and tests

**Files:**
- Modify: `python/terminal_manager.py`
- Create: `python/tests/test_session_panel_helpers.py`

- [x] Write failing tests for percentage clamping, compact model names, update-age formatting, and progress fill width.
- [x] Run `python -m unittest discover -s python/tests -v` and confirm the helpers are initially absent.
- [x] Add `import time`, the new panel palette, and pure helper functions.
- [x] Run unit tests and `python -m py_compile python/terminal_manager.py python/session_monitor.py`.

Representative helper behavior:

```python
def _clamp_pct(value):
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _progress_fill_width(width, pct):
    return int(max(0, width) * _clamp_pct(pct) / 100.0)
```

## Task 2: Implement reusable SessionCard

**Files:**
- Modify: `python/terminal_manager.py`
- Modify: `python/tests/test_session_panel_helpers.py`

- [x] Add tests for status labels and context warning thresholds.
- [x] Add `SessionCard` after `NeonButton` with collapsed and expanded layouts.
- [x] Add status icon, name/state labels, model/branch/agent badges, percentage, progress Canvas, and detail area.
- [x] Bind enter, leave, click, and mouse-wheel events recursively.
- [x] Use an 80ms enter delay, 120ms leave delay, and cancellable 20ms height-animation ticks.
- [x] Use `winfo_containing()` so movement among descendants does not collapse the card.
- [x] Add a delayed full-path tooltip.
- [x] Draw a fixed true-width green→yellow→orange→red gradient and move only the running-state highlight.
- [x] Add a subtle endpoint pulse at 95% and above.
- [x] Cancel all owned `after()` callbacks in `destroy()`.

Public interface:

```python
card.update_snapshot(snapshot, display_state)
card.set_hovered(True or False)
card.animate(phase, now)
card.grid_at(row)
card.destroy()
```

## Task 3: Redesign the panel header and drag region

**Files:**
- Modify: `python/terminal_manager.py:_create_stats_panel`

- [x] Increase logical width to 430px.
- [x] Add a two-row header with title/clock and active/idle/token summaries.
- [x] Add a subtle scanning separator Canvas.
- [x] Restrict dragging to the header and descendants.
- [x] Preserve topmost behavior, alpha 0.94, DPI scaling, rounded clipping, and 40px snapping.
- [x] Add a Canvas viewport with an inner Frame for a scrollable card area.

## Task 4: Replace row rebuilds with keyed reconciliation

**Files:**
- Modify: `python/terminal_manager.py:TerminalManager.__init__`
- Modify: `python/terminal_manager.py:_update_panel`

- [x] Initialize `_session_cards`, `_done_until`, and `_expanded_session_id` before the initial monitor scan.
- [x] Preserve `busy → idle` terminal focus behavior and add a five-second DONE deadline.
- [x] Remove a DONE deadline immediately when the session becomes busy.
- [x] Reconcile visible cards by `session_id` instead of rebuilding all child widgets.
- [x] Update every field on every poll: name, status, model, branch, agents, tokens, cost, percentage, geometry, path, and age.
- [x] Enforce one expanded card at a time.
- [x] Reuse a single empty-state label.
- [x] Remove the old `_last_id_key`, `_bar_texts`, `_wave_labels`, `_wave_bars`, `_dot_canvases`, per-character waves, and sawtooth fill logic.

Reconciliation pattern:

```python
wanted = {snapshot.session_id for snapshot in visible}
for sid in set(cards) - wanted:
    cards.pop(sid).destroy()
for row, snapshot in enumerate(visible):
    card = cards.get(snapshot.session_id) or SessionCard(...)
    card.update_snapshot(snapshot, display_state)
    card.grid_at(row)
```

## Task 5: Update animation, sizing, scrolling, and shutdown

**Files:**
- Modify: `python/terminal_manager.py:_animate_loop`
- Modify: `python/terminal_manager.py:_resize_stats_panel`
- Modify: `python/terminal_manager.py:_quit_app`

- [x] Animate only the header scan and cards requiring active drawing.
- [x] Refresh the clock and update-age text once per second.
- [x] Expire DONE states using `time.monotonic()`.
- [x] Add `_schedule_panel_resize()` to coalesce rapid card-height changes.
- [x] Preserve top and bottom pinning during resize.
- [x] Cap panel height to the effective work area.
- [x] Keep the header fixed and make the card body mouse-wheel scrollable on shorter screens.
- [x] Stop the monitor, destroy cards, cancel animation/resize callbacks, stop the tray, and destroy tkinter safely.
- [x] Marshal tray-thread shutdown back to tkinter's main thread.

## Task 6: Documentation and verification

**Files:**
- Modify: `README.md`
- Modify: `python/DEVELOPMENT.md`
- Add: `docs/superpowers/specs/2026-06-24-session-monitor-panel-design.md`
- Add: `docs/superpowers/plans/2026-06-24-session-monitor-panel.md`

- [x] Document reusable cards, hover details, scrolling, true-width gradient behavior, and RUNNING/DONE/IDLE states.
- [x] Correct the documented launch flow to match the temporary PowerShell script implementation.
- [x] Run six helper unit tests.
- [x] Run `py_compile` and `compileall`.
- [x] Run headless tkinter smoke tests for card lifecycle and full manager reconciliation.
- [x] Run a 12-card short-screen scroll smoke test.
- [x] Review launcher, tray, terminal settings, HWND focus, and monitor polling for unintended changes.
- [x] Record remaining Windows desktop validation requirements.

## Verification evidence

Commands completed locally:

```bash
python -m unittest discover -s python/tests -v
python -m py_compile python/terminal_manager.py python/session_monitor.py
python -m compileall -q python
```

Results:

- 6 unit tests passed.
- Both Python modules compiled.
- `compileall` completed without errors.
- Headless `SessionCard` creation/update/hover/animation/destruction smoke test passed.
- Headless `TerminalManager` keyed reconciliation and DONE-state smoke test passed.
- Twelve-session short-work-area scrolling smoke test passed.

Windows desktop validation remains required for Windows Terminal launch/focus, top and bottom docking, DPI rendering, Unicode paths, tray shutdown, and completion auto-pop behavior.
