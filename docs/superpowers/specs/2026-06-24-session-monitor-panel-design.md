# Session Monitor Panel Redesign Specification

**Date:** 2026-06-24  
**Project:** Agent Launcher — Python/tkinter edition  
**Status:** Approved and implemented on `feat/session-monitor-panel-redesign`

## 1. Objective

Redesign the floating Session Monitor panel in `terminal_manager.py` to improve visual quality, information hierarchy, interaction clarity, and refresh reliability while preserving the existing Windows-specific launcher, tray, monitoring, and terminal-focus behavior.

The selected direction is:

- Future-tech visual style
- Medium information density
- Comprehensive default information hierarchy
- Hover-to-expand session details
- Componentized `SessionCard` implementation
- Gradient context progress bars with fixed true width and animated highlight

The redesign must remain compatible with tkinter, the current `SessionMonitor` data model, Windows DPI scaling, the borderless topmost panel, rounded clipping, edge snapping, and terminal click-to-focus behavior.

## 2. Scope

### In scope

- Redesign the floating Session Monitor header and session rows.
- Introduce a reusable `SessionCard` component.
- Replace full-row rebuild behavior with keyed card creation, reuse, update, reordering, and removal.
- Add hover expansion for detailed session metrics.
- Improve visual status treatment for running, done, idle, and high-context sessions.
- Preserve the gradient context progress bar while correcting its animation semantics.
- Improve panel sizing behavior for top, bottom, and middle screen positions.
- Add safe timer cancellation and widget-lifecycle handling.
- Fix the missing `import time` needed by existing temporary-script cleanup and HWND tracking threads.

### Out of scope

- Changing how Claude session JSON or transcript JSONL files are discovered.
- Replacing tkinter with another GUI toolkit.
- Redesigning the main Agent Launcher window.
- Changing Windows Terminal launch semantics beyond the existing missing import fix.
- Changing token-pricing policy or context-window calculation in `session_monitor.py`.
- Introducing an unrelated large-scale file or architecture refactor.

## 3. Architecture

### 3.1 Existing data source

`SessionMonitor` remains responsible for producing `AggregateStats`, containing ordered `SessionSnapshot` objects. The monitoring thread continues to poll every three seconds and schedules GUI work onto tkinter's main thread.

### 3.2 New presentation components

Add a `SessionCard` class in `terminal_manager.py` for the first implementation. It owns all widgets, canvas items, hover state, animation state, and displayed values for one session.

Conceptual interface:

```python
class SessionCard:
    def update_snapshot(self, snapshot, display_state): ...
    def set_hovered(self, hovered): ...
    def animate(self, phase, now): ...
    def grid_at(self, index): ...
    def destroy(self): ...
```

`display_state` is one of `running`, `done`, or `idle`. The card receives callbacks rather than calling `TerminalManager` internals directly.

### 3.3 Card registry

`TerminalManager` maintains:

```python
self._session_cards: dict[str, SessionCard]
```

Each update performs keyed reconciliation:

- Existing session ID: update the card in place.
- New session ID: create one card.
- Missing session ID: destroy and remove one card.
- Order change: reposition existing cards without rebuilding their internals.

This replaces the current session-list/status tuple shortcut in which only percentage labels are patched while progress bars, model labels, branch labels, and other fields may remain stale.

### 3.4 Responsibilities

`TerminalManager` remains responsible for panel creation and clipping, header summaries, state-transition detection, card ordering, sizing, terminal-focus callbacks, and global animation scheduling.

`SessionCard` is responsible for card structure, status rendering, metadata, progress drawing, hover details, per-card animation, child-widget event binding, and safe cancellation of delayed callbacks.

## 4. Visual Design

### 4.1 Panel

Recommended logical width: approximately 430 pixels before DPI scaling.

Suggested palette:

```python
PANEL_BG = "#11131F"
CARD_BG = "#191C2B"
CARD_HOVER_BG = "#20243A"
BORDER_IDLE = "#343B59"
BORDER_BUSY = "#4D78B8"
BORDER_HOVER = "#7C8CFF"
TEXT_PRIMARY = "#F4F7FF"
TEXT_SECONDARY = "#AAB3D1"
TEXT_MUTED = "#68708D"
ACCENT_GREEN = "#68F0B0"
ACCENT_YELLOW = "#F6D06F"
ACCENT_RED = "#FF6878"
ACCENT_PURPLE = "#A58BFF"
```

The panel keeps the borderless `Toplevel`, topmost behavior, rounded `SetWindowRgn` clipping, transparency, dragging, and 40-pixel edge snapping. Only the header region initiates dragging.

### 4.2 Header

The header contains two rows:

- First row: `SESSION MONITOR` and the `HH:MM:SS` clock.
- Second row: active count, idle count, and aggregate token count.

A low-intensity blue-purple scanning separator sits below the summary.

### 4.3 Default session card

Each collapsed card uses approximately 58–68 logical pixels and shows:

1. Four-point status symbol, short directory name, and right-aligned status.
2. Model, Git branch, subagent count, and right-aligned context percentage.
3. Rounded gradient context progress bar.

Empty values do not create empty badges. `main` and `master` branch badges remain hidden.

### 4.4 Hover details

Hovering a card expands it by approximately 42–50 logical pixels and reveals cumulative input/output tokens, estimated cost, full working directory, and human-readable update age.

Long paths use single-line ellipsis, while a delayed tooltip exposes the full path. Only one card may remain expanded at a time.

## 5. Status Treatment

### Running

- Green/cyan four-point star
- Light border breathing
- `RUNNING` label
- Slow highlight motion over the fixed-width gradient progress bar
- No per-character directory or status-word wave animation

### Done

A `busy → idle` transition creates a temporary five-second `DONE` state with a yellow symbol and label. Existing terminal auto-focus behavior remains. A session returning to busy immediately shows `RUNNING`.

### Idle

- Small hollow gray-blue status symbol
- Static border
- Subdued `IDLE` label
- No continuous redraw unless hovered or data changes

### High context

- Below 70%: normal
- 70%–85%: yellow percentage emphasis
- 85%–95%: orange emphasis
- Above 95%: red endpoint/percentage pulse

The entire card does not turn red.

## 6. Gradient Progress Bar

The progress bar remains a pill-shaped green-to-yellow-to-orange-to-red gradient.

Required behavior:

- Filled width always equals the clamped context percentage.
- Low percentages reveal only the green portion.
- Higher percentages progressively reveal yellow, orange, and red.
- Running sessions show a moving highlight inside the already-filled region.
- The highlight moves; the filled width never resets from zero.
- Both ends remain rounded.
- Empty and very small values remain geometrically valid.

## 7. Interaction Design

### Hover timing

- Enter delay: approximately 80 ms
- Expansion duration: approximately 180 ms
- Leave delay: approximately 120 ms

Hover timers are cancellable. Pointer movement among descendants does not collapse the card, and entering another card collapses the previous one.

### Click behavior

Clicking a card calls:

```text
SessionCard → on_activate(cwd) → TerminalManager._bring_terminal_to_front(cwd)
```

Clicking does not toggle expansion.

### Panel dragging

Only the header and its children receive drag bindings. Cards remain dedicated to hover, scroll, and terminal activation.

## 8. Animation

The global timer runs every 100 ms and handles:

- clock refresh once per second;
- subtle header scan line;
- running status-star and border breathing;
- moving highlight over a fixed-width gradient bar;
- hover expansion;
- high-context endpoint pulse.

Idle collapsed cards avoid continuous redraw.

## 9. Panel Sizing and Positioning

The panel recalculates required height when cards are added, removed, expanded, or collapsed, and when the empty state changes.

- Top-attached panels grow downward.
- Bottom-attached panels grow upward while preserving the bottom edge.
- Middle-positioned panels keep their top position unless this would exceed the work area.
- The panel never extends below the effective work-area bottom.
- The session body becomes vertically scrollable when content exceeds the available height.
- Up to 12 sessions are shown.

## 10. Data Refresh and State Transitions

Every `AggregateStats` update:

1. derives current session IDs and statuses;
2. detects `busy → idle` and creates a five-second DONE deadline;
3. reconciles `self._session_cards`;
4. updates each complete snapshot, not only the percentage;
5. reorders cards to match monitor ordering;
6. updates header aggregates;
7. coalesces panel resizing.

A card update covers name, status, model, branch, subagent count, tokens, cost, context percentage and geometry, path, and update age.

## 11. Error Handling and Lifecycle

- Catch `tk.TclError` where delayed callbacks can race with destruction.
- Store and cancel card-owned `after()` callback IDs.
- Ignore animation work for destroyed widgets.
- Clamp displayed context percentage to 0–100.
- Hide unavailable optional badges.
- Terminal activation failure does not alter card state.
- Shutdown stops monitor polling, destroys cards, cancels panel timers, and stops the tray.
- `terminal_manager.py` imports `time` so temporary-script cleanup and HWND tracking threads work.

## 12. Compatibility Constraints

The implementation preserves Windows Terminal launching, temporary PowerShell scripts, tray behavior, terminal HWND focus, DPI scaling, Unicode paths, rounded clipping, topmost behavior, main-window functions, and settings editing. No new third-party GUI dependency is introduced.

## 13. Acceptance Criteria

1. Empty state renders correctly.
2. Sessions render in monitor-defined order.
3. Existing cards update all fields without recreation.
4. New and removed sessions create/destroy exactly one card.
5. `busy → idle` displays `DONE` for five seconds and invokes terminal focus.
6. Returning to busy immediately displays `RUNNING`.
7. Hover expansion does not flicker.
8. Movement among card descendants does not collapse the card.
9. Only one card is expanded.
10. Card clicks focus the terminal and never drag the panel.
11. Progress width reflects true percentage.
12. Running animation moves only a highlight.
13. High-context escalation follows defined thresholds.
14. Top/bottom docking resizes in the correct direction.
15. Large session counts stay inside the work area and remain scrollable.
16. Destroying cards with pending callbacks raises no exception.
17. High-DPI and Unicode names remain usable.
18. Tray, launcher, and terminal settings remain unchanged.
19. Unit tests and `py_compile` succeed.
20. Windows smoke testing verifies launch, hover, animation, drag, snapping, focus, and shutdown.

## 14. Implementation Boundary

The first implementation keeps `SessionCard` in `terminal_manager.py` to limit scope. Moving it to a dedicated module may be considered later after behavior is stable and covered by tests.
