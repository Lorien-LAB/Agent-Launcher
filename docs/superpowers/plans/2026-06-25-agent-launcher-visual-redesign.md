# Agent Launcher Visual Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current mixed native/Tk dark UI with a cohesive modern dark Agent Launcher featuring custom frameless chrome, purple-blue ambient glow, rounded cards, custom controls, dual-layer directory rows, and a polished compact/expanded layout without changing launch, index, appearance-transaction, tray, or Session Monitor semantics.

**Architecture:** Keep the current coordinator/state/index/launch separation intact. Add four focused visual modules—theme tokens, frameless chrome, reusable custom widgets, and background rendering—then rebuild `LauncherView`, `DirectoryList`, `DirectoryRowWidget`, and `LauncherSettingsPanel` on top of those modules. Platform-specific behavior is isolated behind pure geometry/state helpers plus a thin Win32/DWM adapter so logic remains unit-testable on non-Windows runners.

**Tech Stack:** Python 3.14, Tkinter/ttk, ctypes Win32/DWM calls, `unittest`, existing launcher state/coordinator/runtime modules.

---

## File structure and ownership

### New production files

- `python/launcher_theme.py`
  - Immutable color, typography, spacing, geometry, and animation tokens.
  - DPI scaling helpers.
  - Color interpolation and contrast-safe state helpers.
  - Icon font fallback selection.

- `python/launcher_chrome.py`
  - Pure frameless-window drag/maximize/restore geometry helpers.
  - `ChromeState` state machine.
  - Win32/DWM adapter for rounded corners and taskbar-safe frameless behavior.
  - `LauncherTitleBar` widget.

- `python/launcher_widgets.py`
  - Rounded rectangle drawing helper.
  - `RoundedCard`, `GhostButton`, `PrimaryButton`, `SearchField`.
  - `ToggleSwitch`, `SegmentedControl`, `ThemedSlider`, `OverlayScrollbar`.
  - Focus, hover, disabled, and pressed state handling.

- `python/launcher_background.py`
  - Background Canvas and cached glow layers.
  - Compact/expanded glow placement.
  - Resize debouncing.

### New test files

- `python/tests/test_launcher_theme.py`
- `python/tests/test_launcher_chrome.py`
- `python/tests/test_launcher_widgets.py`
- `python/tests/test_launcher_directory_row.py`
- `python/tests/test_launcher_settings_panel.py`

### Modified production files

- `python/launcher_view_models.py`
- `python/launcher_animation.py`
- `python/launcher_directory_row.py`
- `python/launcher_directory_list.py`
- `python/launcher_settings_panel.py`
- `python/launcher_view.py`
- `python/launcher_coordinator.py`
- `python/launcher_runtime.py`

### Modified test files

- `python/tests/test_launcher_animation.py`
- `python/tests/test_launcher_view.py`
- `python/tests/test_launcher_coordinator.py`

### Documentation and cleanup

- `README.md`
- `DEVELOPMENT.md`
- Delete redundant `python/tests/test_path_setup.py`; keep `python/tests/test_a_path_setup.py` as the discovery bootstrap.

---

## Task 1: Lock the verified baseline and remove redundant discovery setup

**Files:**
- Delete: `python/tests/test_path_setup.py`
- Verify: `python/tests/test_a_path_setup.py`

- [ ] **Step 1: Run the full current suite before visual work**

Run:

```powershell
python -m unittest discover -s python/tests -v
```

Expected:

```text
Ran 44 tests
OK
```

- [ ] **Step 2: Delete the redundant path test**

Run:

```powershell
Remove-Item python\tests\test_path_setup.py
```

Keep `python/tests/test_a_path_setup.py` unchanged because its alphabetical position ensures `python/` is added to `sys.path` before other discovered test modules are imported.

- [ ] **Step 3: Re-run discovery**

Run:

```powershell
python -m unittest discover -s python/tests -v
```

Expected:

```text
Ran 43 tests
OK
```

- [ ] **Step 4: Commit**

```powershell
git add -A python/tests/test_path_setup.py
git commit -m "test: remove redundant launcher path bootstrap"
```

---

## Task 2: Add immutable visual tokens, DPI helpers, and color interpolation

**Files:**
- Create: `python/launcher_theme.py`
- Create: `python/tests/test_launcher_theme.py`
- Modify: `python/launcher_view_models.py:10-11`

- [ ] **Step 1: Write the failing theme tests**

Create `python/tests/test_launcher_theme.py`:

```python
from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401

from launcher_theme import (
    COLORS,
    METRICS,
    compact_size,
    expanded_size,
    interpolate_hex,
    scaled,
)


class LauncherThemeTests(unittest.TestCase):
    def test_required_color_tokens_are_present(self):
        required = {
            "window_bg",
            "surface_0",
            "surface_1",
            "surface_2",
            "surface_hover",
            "surface_selected",
            "border",
            "border_hover",
            "border_focus",
            "text_primary",
            "text_secondary",
            "text_muted",
            "text_disabled",
            "purple",
            "purple_light",
            "blue",
            "blue_light",
            "claude",
            "claude_hover",
            "hermes",
            "hermes_hover",
            "favorite",
            "danger",
            "success",
            "warning",
        }
        self.assertEqual(required, set(COLORS))

    def test_scaled_rounds_logical_pixels(self):
        self.assertEqual(18, scaled(12, 1.5))
        self.assertEqual(1, scaled(1, 1.25))

    def test_target_sizes_match_visual_spec(self):
        self.assertEqual((380, 420), compact_size(1.0))
        self.assertEqual((820, 560), expanded_size(1.0))
        self.assertEqual((570, 630), compact_size(1.5))

    def test_color_interpolation_is_clamped(self):
        self.assertEqual("#000000", interpolate_hex("#000000", "#FFFFFF", -1.0))
        self.assertEqual("#808080", interpolate_hex("#000000", "#FFFFFF", 0.5))
        self.assertEqual("#FFFFFF", interpolate_hex("#000000", "#FFFFFF", 2.0))

    def test_metric_contract(self):
        self.assertEqual(38, METRICS.titlebar_height)
        self.assertEqual(44, METRICS.directory_row_height)
        self.assertEqual(12, METRICS.card_radius)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```powershell
python -m unittest python.tests.test_launcher_theme -v
```

Expected:

```text
ERROR: ModuleNotFoundError: No module named 'launcher_theme'
```

- [ ] **Step 3: Implement `launcher_theme.py`**

Create `python/launcher_theme.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


COLORS = {
    "window_bg": "#090B12",
    "surface_0": "#0D1019",
    "surface_1": "#121624",
    "surface_2": "#171C2C",
    "surface_hover": "#1C2234",
    "surface_selected": "#232A45",
    "border": "#252B3D",
    "border_hover": "#343C58",
    "border_focus": "#6D5DFB",
    "text_primary": "#F4F6FB",
    "text_secondary": "#AAB1C3",
    "text_muted": "#70788E",
    "text_disabled": "#4E5567",
    "purple": "#8B5CF6",
    "purple_light": "#A78BFA",
    "blue": "#4F7CFF",
    "blue_light": "#6EA0FF",
    "claude": "#46C878",
    "claude_hover": "#58D88A",
    "hermes": "#F2A45D",
    "hermes_hover": "#FFB671",
    "favorite": "#D8B45A",
    "danger": "#FF5D6C",
    "success": "#56D98A",
    "warning": "#F4BF62",
}


@dataclass(frozen=True)
class ThemeMetrics:
    outer_padding: int = 12
    card_gap: int = 10
    card_padding: int = 12
    titlebar_height: int = 38
    search_height: int = 40
    directory_row_height: int = 44
    primary_button_height: int = 40
    secondary_button_height: int = 32
    card_radius: int = 12
    button_radius: int = 8
    input_radius: int = 10
    row_radius: int = 8
    border_width: int = 1
    selected_bar_width: int = 2


METRICS = ThemeMetrics()
COMPACT_LOGICAL_SIZE = (380, 420)
EXPANDED_LOGICAL_SIZE = (820, 560)


def scaled(value: int | float, dpi_scale: float) -> int:
    return max(1, int(round(float(value) * float(dpi_scale))))


def compact_size(dpi_scale: float) -> tuple[int, int]:
    return tuple(scaled(value, dpi_scale) for value in COMPACT_LOGICAL_SIZE)


def expanded_size(dpi_scale: float) -> tuple[int, int]:
    return tuple(scaled(value, dpi_scale) for value in EXPANDED_LOGICAL_SIZE)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    stripped = value.lstrip("#")
    if len(stripped) != 6:
        raise ValueError(f"expected #RRGGBB color, got {value!r}")
    return tuple(int(stripped[index:index + 2], 16) for index in (0, 2, 4))


def interpolate_hex(start: str, end: str, progress: float) -> str:
    t = max(0.0, min(1.0, float(progress)))
    start_rgb = _hex_to_rgb(start)
    end_rgb = _hex_to_rgb(end)
    channels = [round(a + (b - a) * t) for a, b in zip(start_rgb, end_rgb)]
    return "#" + "".join(f"{channel:02X}" for channel in channels)
```

- [ ] **Step 4: Replace the old size constants**

Modify `python/launcher_view_models.py`:

```python
from launcher_theme import COMPACT_LOGICAL_SIZE, EXPANDED_LOGICAL_SIZE

COMPACT_SIZE = COMPACT_LOGICAL_SIZE
EXPANDED_SIZE = EXPANDED_LOGICAL_SIZE
```

Remove the old literal `(360, 320)` and `(720, 520)` assignments.

- [ ] **Step 5: Run focused and full tests**

```powershell
python -m unittest python.tests.test_launcher_theme python.tests.test_launcher_view -v
python -m unittest discover -s python/tests -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add python/launcher_theme.py python/launcher_view_models.py python/tests/test_launcher_theme.py
git commit -m "feat: add Agent Launcher visual theme tokens"
```

---

## Task 3: Add pure frameless-window geometry and state logic

**Files:**
- Create: `python/launcher_chrome.py`
- Create: `python/tests/test_launcher_chrome.py`

- [ ] **Step 1: Write failing geometry/state tests**

Create `python/tests/test_launcher_chrome.py`:

```python
from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401

from launcher_chrome import (
    ChromeState,
    DragAnchor,
    WindowBounds,
    calculate_drag_position,
    restore_for_drag,
)


class LauncherChromeTests(unittest.TestCase):
    def test_drag_position_preserves_pointer_offset(self):
        anchor = DragAnchor(pointer_x=110, pointer_y=220, window_x=80, window_y=180)
        self.assertEqual((130, 250), calculate_drag_position(anchor, 160, 290))

    def test_restore_for_drag_keeps_pointer_ratio(self):
        maximized = WindowBounds(0, 0, 1920, 1040)
        restored = WindowBounds(100, 100, 820, 560)
        result = restore_for_drag(
            pointer_x=1440,
            pointer_y=10,
            maximized=maximized,
            restored=restored,
        )
        self.assertEqual(825, result.x)
        self.assertEqual(10, result.y)
        self.assertEqual(820, result.width)
        self.assertEqual(560, result.height)

    def test_chrome_state_transitions(self):
        state = ChromeState()
        state.mark_maximized(WindowBounds(20, 30, 820, 560))
        self.assertTrue(state.maximized)
        self.assertEqual(WindowBounds(20, 30, 820, 560), state.restore_bounds)
        state.mark_restored()
        self.assertFalse(state.maximized)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run and verify failure**

```powershell
python -m unittest python.tests.test_launcher_chrome -v
```

Expected: `ModuleNotFoundError: launcher_chrome`.

- [ ] **Step 3: Implement the pure helpers and state object**

Create the top half of `python/launcher_chrome.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WindowBounds:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class DragAnchor:
    pointer_x: int
    pointer_y: int
    window_x: int
    window_y: int


class ChromeState:
    def __init__(self) -> None:
        self.maximized = False
        self.restore_bounds: WindowBounds | None = None

    def mark_maximized(self, restore_bounds: WindowBounds) -> None:
        self.restore_bounds = restore_bounds
        self.maximized = True

    def mark_restored(self) -> None:
        self.maximized = False


def calculate_drag_position(
    anchor: DragAnchor,
    pointer_x: int,
    pointer_y: int,
) -> tuple[int, int]:
    return (
        anchor.window_x + int(pointer_x) - anchor.pointer_x,
        anchor.window_y + int(pointer_y) - anchor.pointer_y,
    )


def restore_for_drag(
    pointer_x: int,
    pointer_y: int,
    maximized: WindowBounds,
    restored: WindowBounds,
) -> WindowBounds:
    ratio = max(0.0, min(1.0, (pointer_x - maximized.x) / max(1, maximized.width)))
    x = round(pointer_x - restored.width * ratio)
    return WindowBounds(x=x, y=pointer_y, width=restored.width, height=restored.height)
```

- [ ] **Step 4: Run focused tests**

```powershell
python -m unittest python.tests.test_launcher_chrome -v
```

Expected: all three tests pass.

- [ ] **Step 5: Commit**

```powershell
git add python/launcher_chrome.py python/tests/test_launcher_chrome.py
git commit -m "feat: add frameless launcher geometry state"
```

---

## Task 4: Add the Win32/DWM adapter and custom title bar

**Files:**
- Modify: `python/launcher_chrome.py`
- Modify: `python/tests/test_launcher_chrome.py`

- [ ] **Step 1: Add failing adapter/title-bar tests with fakes**

Append to `python/tests/test_launcher_chrome.py`:

```python
class FakeRoot:
    def __init__(self):
        self.calls = []
        self.geometry_value = "820x560+100+100"

    def overrideredirect(self, value):
        self.calls.append(("overrideredirect", value))

    def attributes(self, *args):
        self.calls.append(("attributes", args))

    def geometry(self, value=None):
        if value is not None:
            self.geometry_value = value
        return self.geometry_value

    def winfo_id(self):
        return 123


class FakePlatform:
    def __init__(self):
        self.rounded = []

    def apply_rounded_corners(self, hwnd, enabled=True):
        self.rounded.append((hwnd, enabled))
        return True


class LauncherChromeAdapterTests(unittest.TestCase):
    def test_apply_frameless_enables_override_and_rounding(self):
        from launcher_chrome import LauncherChromeController

        root = FakeRoot()
        platform = FakePlatform()
        controller = LauncherChromeController(root, platform=platform)
        controller.apply_frameless()

        self.assertIn(("overrideredirect", True), root.calls)
        self.assertEqual([(123, True)], platform.rounded)
```

- [ ] **Step 2: Verify the new test fails**

```powershell
python -m unittest python.tests.test_launcher_chrome.LauncherChromeAdapterTests -v
```

Expected: import failure for `LauncherChromeController`.

- [ ] **Step 3: Add the thin platform adapter and controller**

Append to `python/launcher_chrome.py`:

```python
import ctypes
import sys


class WindowsChromePlatform:
    DWMWA_WINDOW_CORNER_PREFERENCE = 33
    DWMWCP_DEFAULT = 0
    DWMWCP_ROUND = 2

    def apply_rounded_corners(self, hwnd: int, enabled: bool = True) -> bool:
        if sys.platform != "win32":
            return False
        preference = ctypes.c_int(self.DWMWCP_ROUND if enabled else self.DWMWCP_DEFAULT)
        try:
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                ctypes.c_uint(self.DWMWA_WINDOW_CORNER_PREFERENCE),
                ctypes.byref(preference),
                ctypes.sizeof(preference),
            )
        except (AttributeError, OSError):
            return False
        return result == 0


class LauncherChromeController:
    def __init__(self, root, platform=None) -> None:
        self.root = root
        self.platform = platform or WindowsChromePlatform()
        self.state = ChromeState()

    def apply_frameless(self) -> None:
        self.root.overrideredirect(True)
        try:
            self.platform.apply_rounded_corners(self.root.winfo_id(), True)
        except Exception:
            pass

    def reapply_after_restore(self) -> None:
        self.root.after_idle(self.apply_frameless)
```

- [ ] **Step 4: Add `LauncherTitleBar`**

Append a `LauncherTitleBar` class that accepts explicit callbacks and does not own tray or process shutdown semantics:

```python
class LauncherTitleBar(tk.Frame):
    def __init__(
        self,
        master,
        *,
        theme,
        scale,
        on_minimize,
        on_toggle_maximize,
        on_close,
        on_toggle_expanded,
        drag_controller,
    ):
        super().__init__(master, bg=theme["surface_0"], height=scale(38))
        self.pack_propagate(False)
        self._drag_controller = drag_controller
        self._build_controls(
            theme,
            scale,
            on_minimize,
            on_toggle_maximize,
            on_close,
            on_toggle_expanded,
        )
        for widget in (self, self._brand, self._title):
            widget.bind("<ButtonPress-1>", self._drag_controller.begin_drag)
            widget.bind("<B1-Motion>", self._drag_controller.drag)
            widget.bind("<Double-Button-1>", lambda _event: on_toggle_maximize())
```

Use `Segoe UI Semibold` for the title and icon-font fallbacks from `launcher_theme.py`. Use explicit `—`, `□`, and `×` text fallbacks when Fluent icon glyphs cannot be resolved.

- [ ] **Step 5: Run focused and full tests**

```powershell
python -m unittest python.tests.test_launcher_chrome -v
python -m unittest discover -s python/tests -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add python/launcher_chrome.py python/tests/test_launcher_chrome.py
git commit -m "feat: add custom frameless launcher chrome"
```

---

## Task 5: Build reusable rounded cards, buttons, and the search field

**Files:**
- Create: `python/launcher_widgets.py`
- Create: `python/tests/test_launcher_widgets.py`

- [ ] **Step 1: Write failing pure widget-helper tests**

Create `python/tests/test_launcher_widgets.py`:

```python
from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401

from launcher_widgets import (
    WidgetVisualState,
    rounded_rectangle_points,
    resolve_button_colors,
)


class LauncherWidgetHelperTests(unittest.TestCase):
    def test_rounded_rectangle_points_stay_inside_bounds(self):
        points = rounded_rectangle_points(0, 0, 100, 40, 12)
        xs = points[0::2]
        ys = points[1::2]
        self.assertGreaterEqual(min(xs), 0)
        self.assertLessEqual(max(xs), 100)
        self.assertGreaterEqual(min(ys), 0)
        self.assertLessEqual(max(ys), 40)

    def test_disabled_button_wins_over_hover(self):
        state = WidgetVisualState(hovered=True, pressed=False, focused=True, enabled=False)
        colors = resolve_button_colors(
            state,
            normal="#111111",
            hover="#222222",
            pressed="#333333",
            disabled="#444444",
        )
        self.assertEqual("#444444", colors.background)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Verify failure**

```powershell
python -m unittest python.tests.test_launcher_widgets -v
```

Expected: `ModuleNotFoundError: launcher_widgets`.

- [ ] **Step 3: Implement helper contracts**

Create the helper layer in `python/launcher_widgets.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk


@dataclass(frozen=True)
class WidgetVisualState:
    hovered: bool = False
    pressed: bool = False
    focused: bool = False
    enabled: bool = True


@dataclass(frozen=True)
class ResolvedButtonColors:
    background: str


def rounded_rectangle_points(x1, y1, x2, y2, radius):
    radius = max(0, min(int(radius), (x2 - x1) // 2, (y2 - y1) // 2))
    return [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]


def resolve_button_colors(state, *, normal, hover, pressed, disabled):
    if not state.enabled:
        return ResolvedButtonColors(disabled)
    if state.pressed:
        return ResolvedButtonColors(pressed)
    if state.hovered:
        return ResolvedButtonColors(hover)
    return ResolvedButtonColors(normal)
```

- [ ] **Step 4: Add reusable Canvas-based controls**

Implement these classes in the same file:

```python
class RoundedCard(tk.Canvas):
    def __init__(self, master, *, theme, scale, radius=12, padding=12): ...
    @property
    def content(self) -> tk.Frame: ...
    def set_interactive_state(self, *, hovered=False, focused=False): ...

class ThemedButton(tk.Canvas):
    def __init__(self, master, *, text, command, theme, scale, kind="ghost", icon=None): ...
    def configure_state(self, enabled: bool): ...
    def invoke(self): ...

class GhostButton(ThemedButton):
    def __init__(self, master, **kwargs):
        super().__init__(master, kind="ghost", **kwargs)

class PrimaryButton(ThemedButton):
    def __init__(self, master, *, role, **kwargs):
        super().__init__(master, kind=role, **kwargs)

class SearchField(tk.Canvas):
    def __init__(self, master, *, variable, theme, scale, placeholder, on_submit=None): ...
    @property
    def entry(self) -> tk.Entry: ...
    def focus(self): ...
    def clear(self): ...
```

Implementation rules:

- Reuse Canvas item IDs during hover/focus changes.
- Use `tk.Entry` with `relief="flat"`, dark insertion cursor, dark selection background, and no native white border.
- Bind `FocusIn`, `FocusOut`, `Enter`, `Leave`, `ButtonPress-1`, `ButtonRelease-1`, `Return`, and `space` explicitly.
- Expose deterministic state methods for tests.

- [ ] **Step 5: Extend tests with fake-state invocation**

Add tests that instantiate `ThemedButton` only when Tk is available:

```python
@unittest.skipUnless(__import__("os").environ.get("DISPLAY") or __import__("sys").platform == "win32", "Tk display required")
def test_button_invoke_calls_command_once(self):
    import tkinter as tk
    from launcher_theme import COLORS
    from launcher_widgets import GhostButton

    root = tk.Tk()
    root.withdraw()
    calls = []
    button = GhostButton(root, text="Refresh", command=lambda: calls.append("called"), theme=COLORS, scale=lambda value: value)
    button.invoke()
    root.destroy()
    self.assertEqual(["called"], calls)
```

- [ ] **Step 6: Run tests**

```powershell
python -m unittest python.tests.test_launcher_widgets -v
python -m unittest discover -s python/tests -v
```

Expected: all tests pass; GUI-only tests run on Windows and skip on headless runners.

- [ ] **Step 7: Commit**

```powershell
git add python/launcher_widgets.py python/tests/test_launcher_widgets.py
git commit -m "feat: add reusable dark launcher widgets"
```

---

## Task 6: Add custom segmented controls, toggles, slider, and overlay scrollbar

**Files:**
- Modify: `python/launcher_widgets.py`
- Modify: `python/tests/test_launcher_widgets.py`

- [ ] **Step 1: Add failing state-transition tests**

Append to `python/tests/test_launcher_widgets.py`:

```python
from launcher_widgets import SegmentedState, ToggleState


class LauncherControlStateTests(unittest.TestCase):
    def test_segmented_state_rejects_unknown_value(self):
        state = SegmentedState(("window", "tab"), "window")
        with self.assertRaises(ValueError):
            state.select("missing")

    def test_toggle_state_flips_and_emits(self):
        emitted = []
        state = ToggleState(False, emitted.append)
        state.toggle()
        self.assertTrue(state.value)
        self.assertEqual([True], emitted)
```

- [ ] **Step 2: Run and verify failure**

```powershell
python -m unittest python.tests.test_launcher_widgets.LauncherControlStateTests -v
```

Expected: import failure for `SegmentedState` and `ToggleState`.

- [ ] **Step 3: Implement state objects and widgets**

Add to `python/launcher_widgets.py`:

```python
class SegmentedState:
    def __init__(self, values, selected):
        self.values = tuple(values)
        if selected not in self.values:
            raise ValueError(selected)
        self.selected = selected

    def select(self, value):
        if value not in self.values:
            raise ValueError(value)
        self.selected = value
        return value


class ToggleState:
    def __init__(self, value, on_change):
        self.value = bool(value)
        self.on_change = on_change

    def set(self, value, *, emit=True):
        self.value = bool(value)
        if emit:
            self.on_change(self.value)

    def toggle(self):
        self.set(not self.value)
```

Add Canvas-based UI wrappers:

```python
class SegmentedControl(tk.Canvas):
    def __init__(self, master, *, options, variable, command, theme, scale): ...
    def set_value(self, value, *, emit=False): ...

class ToggleSwitch(tk.Canvas):
    def __init__(self, master, *, variable, command, theme, scale): ...
    def set_value(self, value, *, emit=False): ...

class ThemedSlider(tk.Canvas):
    def __init__(self, master, *, variable, command, theme, scale, from_=0, to=100): ...
    def set_enabled(self, enabled): ...

class OverlayScrollbar(tk.Canvas):
    def __init__(self, master, *, command, theme, scale): ...
    def set(self, first, last): ...
    def visible(self) -> bool: ...
```

Control contracts:

- `SegmentedControl.set_value(..., emit=False)` is used by view synchronization and must not call state persistence callbacks.
- `ToggleSwitch.set_value(..., emit=False)` follows the same rule.
- `ThemedSlider` calls its command only for user motion, not programmatic synchronization.
- `OverlayScrollbar.set(0.0, 1.0)` hides the thumb; partial ranges show it.

- [ ] **Step 4: Add deterministic scrollbar tests**

```python
def test_overlay_scrollbar_visibility_contract(self):
    from launcher_widgets import scrollbar_should_show
    self.assertFalse(scrollbar_should_show(0.0, 1.0))
    self.assertTrue(scrollbar_should_show(0.1, 0.6))
```

Implement:

```python
def scrollbar_should_show(first, last):
    return float(first) > 0.0 or float(last) < 1.0
```

- [ ] **Step 5: Run tests and commit**

```powershell
python -m unittest python.tests.test_launcher_widgets -v
python -m unittest discover -s python/tests -v
git add python/launcher_widgets.py python/tests/test_launcher_widgets.py
git commit -m "feat: add custom launcher selection controls"
```

---

## Task 7: Add cached purple-blue background glow rendering

**Files:**
- Create: `python/launcher_background.py`
- Modify: `python/tests/test_launcher_widgets.py`

- [ ] **Step 1: Add failing glow-spec tests**

Append to `python/tests/test_launcher_widgets.py`:

```python
from launcher_background import glow_spec_for_mode


class LauncherBackgroundTests(unittest.TestCase):
    def test_compact_mode_has_one_purple_glow(self):
        glows = glow_spec_for_mode(False, 380, 420)
        self.assertEqual(1, len(glows))
        self.assertEqual("purple", glows[0].role)

    def test_expanded_mode_adds_blue_project_glow(self):
        glows = glow_spec_for_mode(True, 820, 560)
        self.assertEqual(["purple", "blue"], [glow.role for glow in glows])
```

- [ ] **Step 2: Verify failure**

```powershell
python -m unittest python.tests.test_launcher_widgets.LauncherBackgroundTests -v
```

Expected: `ModuleNotFoundError: launcher_background`.

- [ ] **Step 3: Implement the background contract**

Create `python/launcher_background.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk


@dataclass(frozen=True)
class GlowSpec:
    role: str
    center_x: int
    center_y: int
    radius: int
    opacity: float


def glow_spec_for_mode(expanded: bool, width: int, height: int) -> list[GlowSpec]:
    glows = [GlowSpec("purple", 70, 50, min(180, max(140, width // 3)), 0.14)]
    if expanded:
        glows.append(GlowSpec("blue", round(width * 0.72), round(height * 0.28), 150, 0.10))
    return glows


class LauncherBackground(tk.Canvas):
    def __init__(self, master, *, theme, scale):
        super().__init__(master, bg=theme["window_bg"], highlightthickness=0, bd=0)
        self.theme = theme
        self.scale = scale
        self.expanded = False
        self._redraw_after = None
        self.bind("<Configure>", self._schedule_redraw)

    def set_expanded(self, expanded: bool) -> None:
        self.expanded = bool(expanded)
        self.redraw()

    def _schedule_redraw(self, _event=None) -> None:
        if self._redraw_after is not None:
            self.after_cancel(self._redraw_after)
        self._redraw_after = self.after(80, self.redraw)

    def redraw(self) -> None:
        self._redraw_after = None
        self.delete("glow")
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        for glow in glow_spec_for_mode(self.expanded, width, height):
            self._draw_glow(glow)

    def _draw_glow(self, spec: GlowSpec) -> None:
        base = self.theme[spec.role]
        background = self.theme["window_bg"]
        rings = 18
        for index in range(rings, 0, -1):
            fraction = index / rings
            radius = round(spec.radius * fraction)
            color = _blend_for_glow(background, base, spec.opacity * (1.0 - fraction * 0.82))
            self.create_oval(
                spec.center_x - radius,
                spec.center_y - radius,
                spec.center_x + radius,
                spec.center_y + radius,
                fill=color,
                outline="",
                tags="glow",
            )
```

Use `launcher_theme.interpolate_hex` inside `_blend_for_glow`.

- [ ] **Step 4: Run tests and commit**

```powershell
python -m unittest python.tests.test_launcher_widgets -v
python -m unittest discover -s python/tests -v
git add python/launcher_background.py python/tests/test_launcher_widgets.py
git commit -m "feat: add ambient launcher background glow"
```

---

## Task 8: Rebuild the directory row as a dual-layer interactive item

**Files:**
- Modify: `python/launcher_directory_row.py`
- Create: `python/tests/test_launcher_directory_row.py`

- [ ] **Step 1: Write failing row presentation tests**

Create `python/tests/test_launcher_directory_row.py`:

```python
from __future__ import annotations

import os
import unittest

import _bootstrap  # noqa: F401

from launcher_directory_row import build_row_presentation


class LauncherDirectoryRowTests(unittest.TestCase):
    def test_presentation_uses_basename_and_middle_truncated_path(self):
        path = os.path.join("C:\\", "Users", "Lorien", "projects", "agent-launcher")
        presentation = build_row_presentation(path, available=True, path_limit=24)
        self.assertEqual("agent-launcher", presentation.name)
        self.assertLessEqual(len(presentation.path_text), 24)
        self.assertFalse(presentation.unavailable)

    def test_unavailable_path_gets_status_suffix(self):
        presentation = build_row_presentation("C:\\missing\\project", available=False, path_limit=40)
        self.assertTrue(presentation.unavailable)
        self.assertIn("Unavailable", presentation.path_text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Verify failure**

```powershell
python -m unittest python.tests.test_launcher_directory_row -v
```

Expected: import failure for `build_row_presentation`.

- [ ] **Step 3: Implement pure presentation logic**

Add to `python/launcher_directory_row.py`:

```python
from dataclasses import dataclass

from launcher_view_models import truncate_middle


@dataclass(frozen=True)
class DirectoryRowPresentation:
    name: str
    path_text: str
    unavailable: bool


def build_row_presentation(path: str, available: bool, path_limit: int) -> DirectoryRowPresentation:
    name = os.path.basename(path.rstrip("\\/")) or path
    path_text = truncate_middle(path, path_limit)
    if not available:
        path_text = f"{path_text} · Unavailable"
    return DirectoryRowPresentation(name, path_text, not available)
```

- [ ] **Step 4: Replace the old one-line `tk.Frame` row**

Rebuild `DirectoryRowWidget` with:

- root Canvas or `RoundedCard`-style row container;
- left 2 px selected gradient bar;
- 18 px folder icon;
- first-line name label using `Segoe UI Semibold 10`;
- second-line path label using `Cascadia Code 8`;
- persistent star hit target at the right;
- hover state on row body without affecting star click;
- double-click launch remains Claude;
- `set_selected`, `set_hovered`, and `set_favorite` methods update existing items without destroying widgets.

Constructor contract:

```python
class DirectoryRowWidget(tk.Canvas):
    def __init__(
        self,
        master,
        row,
        *,
        theme,
        scale,
        on_select,
        on_launch,
        on_favorite,
        is_available=os.path.isdir,
    ): ...
```

- [ ] **Step 5: Run focused and full tests**

```powershell
python -m unittest python.tests.test_launcher_directory_row -v
python -m unittest discover -s python/tests -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add python/launcher_directory_row.py python/tests/test_launcher_directory_row.py
git commit -m "feat: redesign launcher directory rows"
```

---

## Task 9: Rebuild the directory list card and custom scrollbar

**Files:**
- Modify: `python/launcher_directory_list.py`
- Modify: `python/tests/test_launcher_view.py`

- [ ] **Step 1: Add failing section-label tests**

Append to `python/tests/test_launcher_view.py`:

```python
from launcher_directory_list import section_title


def test_directory_section_titles_are_uppercase(self):
    self.assertEqual("FAVORITES", section_title("favorite"))
    self.assertEqual("RECENT", section_title("recent"))
    self.assertEqual("SEARCH RESULTS", section_title("search"))
```

- [ ] **Step 2: Verify failure**

```powershell
python -m unittest python.tests.test_launcher_view.LauncherViewHelperTests.test_directory_section_titles_are_uppercase -v
```

Expected: import failure for `section_title`.

- [ ] **Step 3: Implement list card structure**

Add:

```python
def section_title(section: str) -> str:
    return {
        "favorite": "FAVORITES",
        "recent": "RECENT",
        "search": "SEARCH RESULTS",
    }.get(section, section.upper())
```

Refactor `DirectoryList`:

```python
class DirectoryList(RoundedCard):
    def __init__(self, master, *, theme, scale, on_select, on_launch, on_favorite): ...
```

Required changes:

- Replace `tk.Scrollbar` with `OverlayScrollbar`.
- Use `theme["surface_1"]` throughout.
- Set Canvas `yscrollincrement` to scaled 44.
- Hide scrollbar when list fits.
- Render group headings with uppercase 8 pt text and no heavy divider.
- Render `DirectoryRowWidget` with 4 px horizontal inset and 2 px vertical gap.
- Preserve scroll fraction and selected item across renders.
- Bind wheel events on the Canvas, body, row widgets, and labels so scrolling works regardless of pointer target.

- [ ] **Step 4: Add a regression test for scroll preservation**

Use a fake Canvas in `test_launcher_view.py` or preserve the existing `scroll_fraction` contract; assert `render()` captures and restores the same fraction after rebuilding rows.

- [ ] **Step 5: Run tests and commit**

```powershell
python -m unittest python.tests.test_launcher_view -v
python -m unittest discover -s python/tests -v
git add python/launcher_directory_list.py python/tests/test_launcher_view.py
git commit -m "feat: redesign launcher directory list"
```

---

## Task 10: Split the settings panel into three themed cards

**Files:**
- Modify: `python/launcher_settings_panel.py`
- Create: `python/tests/test_launcher_settings_panel.py`

- [ ] **Step 1: Write failing settings synchronization tests**

Create `python/tests/test_launcher_settings_panel.py`:

```python
from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401

from launcher_settings_panel import appearance_status_text, project_summary


class LauncherSettingsPanelHelperTests(unittest.TestCase):
    def test_project_summary_handles_empty_selection(self):
        summary = project_summary(None)
        self.assertEqual("No project selected", summary.name)
        self.assertEqual("Choose a project from the list", summary.path)
        self.assertFalse(summary.actions_enabled)

    def test_appearance_status_text(self):
        self.assertEqual("Previewing", appearance_status_text(True, False))
        self.assertEqual("Applied", appearance_status_text(False, True))
        self.assertEqual("No changes", appearance_status_text(False, False))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Verify failure**

```powershell
python -m unittest python.tests.test_launcher_settings_panel -v
```

Expected: import failure for the new helpers.

- [ ] **Step 3: Implement helper models**

Add:

```python
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ProjectSummary:
    name: str
    path: str
    actions_enabled: bool


def project_summary(path):
    if not path:
        return ProjectSummary(
            "No project selected",
            "Choose a project from the list",
            False,
        )
    return ProjectSummary(os.path.basename(path) or path, path, True)


def appearance_status_text(dirty: bool, applied_now: bool) -> str:
    if dirty:
        return "Previewing"
    if applied_now:
        return "Applied"
    return "No changes"
```

- [ ] **Step 4: Rebuild the panel using three `RoundedCard` components**

Structure:

```python
class LauncherSettingsPanel(tk.Frame):
    def _build(self):
        self.current_project_card = self._build_current_project_card()
        self.launch_options_card = self._build_launch_options_card()
        self.appearance_card = self._build_appearance_card()
```

Current Project card:

- heading `CURRENT PROJECT`;
- icon, project name, two-line middle-truncated path;
- `Open Explorer` and `Copy Path` GhostButtons;
- both buttons disabled when no selection.

Launch Options card:

- `SegmentedControl` for `window`/`tab`;
- tab limitation text only visible when `tab` is selected;
- `ToggleSwitch` for skip permissions;
- `ToggleSwitch` for hide after launch;
- Claude and Hermes `PrimaryButton`s at card bottom.

Terminal Appearance card:

- `SegmentedControl` for acrylic/opacity/none;
- `ThemedSlider` plus percentage label;
- status label;
- Cancel Preview GhostButton;
- Apply purple-blue PrimaryButton disabled while controller is clean.

- [ ] **Step 5: Add explicit dirty-state API**

Add:

```python
def set_appearance_dirty(self, dirty: bool, applied_now: bool = False) -> None:
    self.appearance_dirty = bool(dirty)
    self.appearance_status_var.set(appearance_status_text(dirty, applied_now))
    self.apply_button.configure_state(dirty)
    self.cancel_button.configure_state(dirty)
```

Programmatic calls to `set_launch_options` and `set_appearance` must update custom controls with `emit=False`.

- [ ] **Step 6: Run tests and commit**

```powershell
python -m unittest python.tests.test_launcher_settings_panel -v
python -m unittest discover -s python/tests -v
git add python/launcher_settings_panel.py python/tests/test_launcher_settings_panel.py
git commit -m "feat: redesign launcher settings cards"
```

---

## Task 11: Rebuild compact and expanded main layouts

**Files:**
- Modify: `python/launcher_view.py`
- Modify: `python/launcher_view_models.py`
- Modify: `python/tests/test_launcher_view.py`

- [ ] **Step 1: Add failing layout-spec tests**

Append to `python/tests/test_launcher_view.py`:

```python
from launcher_view_models import layout_spec


def test_compact_layout_is_search_first(self):
    spec = layout_spec(False)
    self.assertEqual(("titlebar", "search", "directory_list", "compact_footer", "status"), spec.sections)
    self.assertFalse(spec.show_settings)


def test_expanded_layout_uses_45_55_columns(self):
    spec = layout_spec(True)
    self.assertEqual((45, 55), spec.column_weights)
    self.assertTrue(spec.show_settings)
```

- [ ] **Step 2: Verify failure**

```powershell
python -m unittest python.tests.test_launcher_view.LauncherViewHelperTests.test_compact_layout_is_search_first python.tests.test_launcher_view.LauncherViewHelperTests.test_expanded_layout_uses_45_55_columns -v
```

Expected: import failure for `layout_spec`.

- [ ] **Step 3: Implement the pure layout specification**

Add to `python/launcher_view_models.py`:

```python
@dataclass(frozen=True)
class LayoutSpec:
    sections: tuple[str, ...]
    column_weights: tuple[int, int]
    show_settings: bool


def layout_spec(expanded: bool) -> LayoutSpec:
    return LayoutSpec(
        sections=("titlebar", "search", "directory_list", "settings", "status")
        if expanded
        else ("titlebar", "search", "directory_list", "compact_footer", "status"),
        column_weights=(45, 55),
        show_settings=bool(expanded),
    )
```

- [ ] **Step 4: Rebuild `LauncherView._build`**

New hierarchy:

```python
self.background = LauncherBackground(self.root, theme=COLORS, scale=self.s)
self.background.pack(fill="both", expand=True)

self.content = tk.Frame(self.background, bg=COLORS["window_bg"])
self.content_window = self.background.create_window(
    0,
    0,
    anchor="nw",
    window=self.content,
)
```

Inside `content`:

1. `LauncherTitleBar` spans both columns.
2. Search row spans both columns and contains `SearchField` plus refresh GhostButton.
3. Main content row has directory list in column 0 and settings panel in column 1.
4. Compact footer is a dedicated `RoundedCard` with selected project and Claude/Hermes buttons.
5. Status row spans both columns.

Use `grid_columnconfigure(0, weight=45)` and `grid_columnconfigure(1, weight=55)` only in expanded mode. In compact mode, column 1 has weight 0 and settings remains hidden.

- [ ] **Step 5: Remove native white controls**

The following objects must no longer exist in `launcher_view.py`:

```text
ttk.Entry
tk.Button for refresh
tk.Button for expand/collapse
tk.Button for Claude
tk.Button for Hermes
```

Replace them with `SearchField`, `GhostButton`, and `PrimaryButton`.

- [ ] **Step 6: Preserve public coordinator-facing methods**

Keep these exact methods and semantics:

```python
render_home
render_search_results
set_selected_path
set_status
set_indexing
set_expanded
set_launch_options
set_appearance
get_scroll_fraction
restore_scroll_fraction
destroy
```

Add:

```python
def set_appearance_dirty(self, dirty: bool, applied_now: bool = False):
    self.settings_panel.set_appearance_dirty(dirty, applied_now)
```

- [ ] **Step 7: Run tests and commit**

```powershell
python -m unittest python.tests.test_launcher_view -v
python -m unittest discover -s python/tests -v
git add python/launcher_view.py python/launcher_view_models.py python/tests/test_launcher_view.py
git commit -m "feat: rebuild compact and expanded launcher layouts"
```

---

## Task 12: Add reduced-motion timing and content fade contracts

**Files:**
- Modify: `python/launcher_animation.py`
- Modify: `python/tests/test_launcher_animation.py`

- [ ] **Step 1: Add failing timing tests**

Append to `python/tests/test_launcher_animation.py`:

```python
from launcher_animation import animation_duration, content_opacity


def test_reduced_motion_uses_zero_duration(self):
    self.assertEqual(0.0, animation_duration(True))
    self.assertEqual(0.22, animation_duration(False))


def test_content_opacity_delays_expanded_panel(self):
    self.assertEqual(0.0, content_opacity(0.25, expanding=True))
    self.assertGreater(content_opacity(0.75, expanding=True), 0.0)
    self.assertEqual(1.0, content_opacity(1.0, expanding=True))
```

- [ ] **Step 2: Verify failure**

```powershell
python -m unittest python.tests.test_launcher_animation -v
```

Expected: import failure for the new functions.

- [ ] **Step 3: Implement timing helpers**

Add:

```python
def animation_duration(reduced_motion: bool) -> float:
    return 0.0 if reduced_motion else ANIMATION_SECONDS


def content_opacity(progress: float, *, expanding: bool) -> float:
    value = max(0.0, min(1.0, float(progress)))
    if expanding:
        return max(0.0, min(1.0, (value - 0.45) / 0.55))
    return max(0.0, min(1.0, value / 0.45))
```

- [ ] **Step 4: Extend `WindowAnimator.animate_to`**

New signature:

```python
def animate_to(
    self,
    target_width,
    target_height,
    work_width,
    work_height,
    on_progress=None,
    on_complete=None,
    reduced_motion=False,
): ...
```

Behavior:

- With reduced motion, set final geometry once, call `on_progress(1.0)`, then `on_complete()`.
- Otherwise call `on_progress(progress)` on every frame.
- Preserve duplicate-start rejection and top-left anchoring.

- [ ] **Step 5: Run tests and commit**

```powershell
python -m unittest python.tests.test_launcher_animation -v
python -m unittest discover -s python/tests -v
git add python/launcher_animation.py python/tests/test_launcher_animation.py
git commit -m "feat: add polished launcher transition timing"
```

---

## Task 13: Integrate appearance dirty state, animated mode switching, and status semantics

**Files:**
- Modify: `python/launcher_coordinator.py`
- Modify: `python/tests/test_launcher_coordinator.py`

- [ ] **Step 1: Add failing coordinator tests**

Append tests using the existing fakes:

```python
def test_preview_marks_view_dirty(self):
    coordinator, view, appearance = self.make_coordinator()
    coordinator.attach_view(view)
    coordinator.preview_appearance(AppearanceSettings("acrylic", 70))
    self.assertEqual([(True, False)], view.appearance_dirty_calls)


def test_apply_marks_view_clean_and_applied(self):
    coordinator, view, appearance = self.make_coordinator()
    coordinator.attach_view(view)
    coordinator.apply_appearance()
    self.assertEqual((False, True), view.appearance_dirty_calls[-1])
```

- [ ] **Step 2: Verify failure**

```powershell
python -m unittest python.tests.test_launcher_coordinator -v
```

Expected: fake view lacks calls or coordinator does not invoke them.

- [ ] **Step 3: Update appearance methods**

Modify:

```python
def preview_appearance(self, settings):
    try:
        self.appearance_controller.preview(settings)
    except OSError as exc:
        self._set_error(f"Appearance preview failed: {exc}")
        return
    self.view.set_appearance_dirty(True, False)


def apply_appearance(self):
    try:
        self.appearance_controller.apply()
    except OSError as exc:
        self._set_error(f"Appearance apply failed: {exc}")
        return
    self.view.set_appearance_dirty(False, True)
    self.view.set_status("Terminal appearance applied", level="success")
```

Update cancel/collapse/hide rollback paths to call `set_appearance_dirty(False, False)` after restoring settings.

- [ ] **Step 4: Update status contract**

Change `LauncherView.set_status` and coordinator calls from boolean `error` to:

```python
level: str = "normal"
```

Allowed values:

```text
normal
success
warning
error
```

Map them to theme tokens in the view. Maintain backward compatibility during the transition by accepting `error=True` until all call sites are converted, then remove the boolean path before committing.

- [ ] **Step 5: Integrate animation progress**

Modify `toggle_mode`:

```python
self.view.prepare_mode_transition(expanding)
started = self.window_animator.animate_to(
    target[0],
    target[1],
    available_width,
    available_height,
    on_progress=lambda progress: self.view.update_mode_transition(expanding, progress),
    on_complete=lambda: self.view.finish_mode_transition(expanding),
    reduced_motion=self.view.reduced_motion_enabled(),
)
if not started:
    self.view.finish_mode_transition(self.expanded)
```

The view methods may use immediate visibility changes when Tk alpha-per-widget is unavailable; they must not repeatedly destroy/recreate the settings panel.

- [ ] **Step 6: Run tests and commit**

```powershell
python -m unittest python.tests.test_launcher_coordinator -v
python -m unittest discover -s python/tests -v
git add python/launcher_coordinator.py python/tests/test_launcher_coordinator.py python/launcher_view.py
git commit -m "feat: integrate launcher visual state transitions"
```

---

## Task 14: Install custom chrome and theme in runtime without affecting Session Monitor

**Files:**
- Modify: `python/launcher_runtime.py`
- Modify: `python/terminal_manager.py`
- Modify: `python/tests/test_launcher_view.py`

- [ ] **Step 1: Add a runtime dependency-construction helper test**

Add a pure helper in `launcher_runtime.py`:

```python
def launcher_window_sizes(scale):
    return compact_size(scale), expanded_size(scale)
```

Test in `test_launcher_view.py`:

```python
def test_runtime_sizes_follow_theme(self):
    from launcher_runtime import launcher_window_sizes
    self.assertEqual(((380, 420), (820, 560)), launcher_window_sizes(1.0))
```

- [ ] **Step 2: Verify failure**

```powershell
python -m unittest python.tests.test_launcher_view.LauncherViewHelperTests.test_runtime_sizes_follow_theme -v
```

Expected: import failure for `launcher_window_sizes`.

- [ ] **Step 3: Replace legacy runtime colors and dimensions**

In `launcher_runtime.py`:

```python
from launcher_chrome import LauncherChromeController
from launcher_theme import COLORS, compact_size, expanded_size
```

Use:

```python
self.compact_size, self.expanded_size = launcher_window_sizes(self.scale)
self.w, self.h = self.compact_size
self.root.configure(bg=COLORS["window_bg"])
```

Delete `_launcher_colors`; pass `theme=COLORS` into `LauncherView`.

Do not call both theme scaling helpers and `WindowAnimator.scale` for the same target. Keep coordinator targets in logical pixels and let `WindowAnimator` scale them once.

- [ ] **Step 4: Install frameless chrome**

After initial geometry and `update_idletasks()`:

```python
self.chrome_controller = LauncherChromeController(self.root)
self.chrome_controller.apply_frameless()
```

Pass title-bar callbacks into `LauncherView`:

```python
on_minimize=lambda: self.root.iconify(),
on_toggle_maximize=self._toggle_launcher_maximize,
on_close=self._hide_to_tray,
chrome_controller=self.chrome_controller,
```

Implement `_toggle_launcher_maximize` using the current-monitor work area rather than `winfo_screenwidth()` when Win32 monitor APIs are available. Fall back to Tk screen dimensions on adapter failure.

- [ ] **Step 5: Preserve tray and Session Monitor semantics**

Keep these runtime actions unchanged:

```python
self._create_stats_panel()
self._monitor = core.SessionMonitor()
self._monitor.on_update(self._on_stats_update)
self._monitor.scan()
self._monitor.start()
```

Keep override installation order in `python/terminal_manager.py` unchanged:

```text
session_panel_ui
session_panel_layout
terminal_focus
session_panel_chrome
session_panel_details
launcher_runtime
```

- [ ] **Step 6: Reapply chrome after tray restore**

Override or wrap the existing show action so the root calls:

```python
self.root.deiconify()
self.chrome_controller.reapply_after_restore()
self.root.lift()
self.root.focus_force()
```

Do not use permanent `-topmost`.

- [ ] **Step 7: Run automated checks**

```powershell
python -m unittest discover -s python/tests -v
python -m py_compile `
  python\terminal_manager.py `
  python\launcher_runtime.py `
  python\launcher_chrome.py `
  python\launcher_theme.py `
  python\launcher_widgets.py `
  python\launcher_background.py `
  python\launcher_view.py `
  python\launcher_settings_panel.py `
  python\launcher_directory_list.py `
  python\launcher_directory_row.py `
  python\launcher_animation.py `
  python\launcher_coordinator.py
```

Expected: all tests pass and `py_compile` exits with no output.

- [ ] **Step 8: Commit**

```powershell
git add python/launcher_runtime.py python/terminal_manager.py python/tests/test_launcher_view.py
git commit -m "feat: install modern frameless Agent Launcher"
```

---

## Task 15: Update documentation and add a visual acceptance checklist

**Files:**
- Modify: `README.md`
- Modify: `DEVELOPMENT.md`

- [ ] **Step 1: Update README feature description**

Add a concise Agent Launcher section containing:

```markdown
## Agent Launcher

Agent Launcher starts in a compact, search-first mode and expands into a full control workspace. It includes favorites, recent projects, recursive background indexing, Claude Code and Hermes launch actions, new-window/new-tab modes, and transactional Windows Terminal appearance preview.

The Windows UI uses a custom frameless title bar, dark rounded controls, purple-blue ambient accents, and a separate Session Monitor panel. Closing the Launcher hides it to the system tray; use the tray Exit action to terminate the process.
```

- [ ] **Step 2: Update DEVELOPMENT architecture notes**

Document module ownership exactly:

```markdown
- `launcher_theme.py`: visual tokens, scaling, color math
- `launcher_chrome.py`: frameless window behavior and DWM integration
- `launcher_widgets.py`: reusable custom Tk controls
- `launcher_background.py`: cached ambient glow background
- `launcher_view.py`: compact/expanded composition only
- `launcher_coordinator.py`: user-action orchestration only
```

Also document that Session Monitor overrides must remain installed before `launcher_runtime`.

- [ ] **Step 3: Add manual acceptance commands**

```powershell
cd C:\Users\Lorien\terminal-manager\python
python terminal_manager.py
```

Acceptance checklist:

1. No native white title bar, input, radio, checkbox, slider, button, or scrollbar appears.
2. Title bar drag, double-click maximize/restore, minimize, and close-to-tray work.
3. Tray restore reapplies frameless styling and rounded corners.
4. Compact mode is approximately 380×420 logical px and search-first.
5. Expanded mode is approximately 820×560 logical px with a 45:55 split.
6. Directory rows show name, shortened path, star, hover, and selected light bar.
7. Current Project, Launch Options, and Terminal Appearance are three distinct cards.
8. Claude and Hermes buttons remain functionally correct.
9. Appearance preview rolls back on cancel, collapse, hide, and close.
10. New-window Session Monitor cards still focus exact HWNDs for duplicate working directories.
11. New-tab mode only promises Terminal window focus.
12. Multi-monitor drag and maximize respect the active work area.
13. 125%, 150%, and 200% DPI do not clip text or controls.
14. Session Monitor layout and scanline remain unchanged.

- [ ] **Step 4: Run the final automated suite**

```powershell
python -m unittest discover -s python/tests -v
python -m py_compile python\*.py
```

Expected: all tests pass; compile exits with no output.

- [ ] **Step 5: Commit**

```powershell
git add README.md DEVELOPMENT.md
git commit -m "docs: document modern Agent Launcher interface"
```

---

## Task 16: Perform final Windows acceptance and record evidence

**Files:**
- No production-file changes unless acceptance reveals a defect.
- Optional evidence: screenshots stored outside the repository or attached to the eventual pull request.

- [ ] **Step 1: Start the application from a visible console**

```powershell
cd C:\Users\Lorien\terminal-manager\python
python terminal_manager.py
```

Expected: Launcher and Session Monitor appear; no traceback is printed.

- [ ] **Step 2: Verify compact-mode interactions**

Perform:

```text
Focus search with the mouse
Type a partial project name
Use Up/Down to move selection
Press Enter to launch Claude
Press Ctrl+Enter to launch Hermes
Toggle a favorite star
Clear search
```

Expected: list and selection update without white native controls or layout jumps.

- [ ] **Step 3: Verify chrome and tray behavior**

Perform:

```text
Drag title bar across monitors
Double-click to maximize
Double-click to restore
Click minimize
Restore from taskbar
Click close
Restore from tray
```

Expected: window state remains valid, custom chrome returns, and close hides rather than exits.

- [ ] **Step 4: Verify expanded workspace**

Perform:

```text
Expand
Change window/tab mode
Toggle skip permission confirmation
Toggle hide after launch
Preview Acrylic
Adjust opacity
Cancel preview
Preview again
Apply
Collapse
```

Expected: 45:55 layout, three cards, correct enabled states, and appearance transaction semantics.

- [ ] **Step 5: Verify Session Monitor regressions**

Launch two new-window sessions with the same working directory and click each Session Monitor card.

Expected: each card focuses its exact mapped Windows Terminal HWND. Session Monitor dimensions, animation, and scanline are unchanged.

- [ ] **Step 6: Re-run tests after acceptance**

```powershell
python -m unittest discover -s python/tests -v
```

Expected: all tests pass.

- [ ] **Step 7: Record the validated commit**

```powershell
git status --short
git log -1 --oneline
```

Expected: clean working tree and a visible final commit SHA. Do not merge or open a new pull request without explicit user approval.

---

## Self-review against the specification

- Custom frameless title bar: Tasks 3, 4, 14, 16.
- Purple-blue ambient glow: Task 7.
- Unified dark tokens and typography: Task 2.
- Rounded cards and custom dark controls: Tasks 5, 6, 10, 11.
- Dual-layer directory rows: Tasks 8 and 9.
- Compact search-first layout: Task 11.
- Expanded 45:55 layout with three cards: Tasks 10 and 11.
- Claude/Hermes role colors: Tasks 5, 10, 11.
- Appearance preview/apply/rollback semantics: Tasks 10 and 13.
- Reduced motion and lightweight transitions: Task 12.
- DPI, monitor, tray, and DWM behavior: Tasks 3, 4, 14, 16.
- Session Monitor and exact HWND behavior preserved: Tasks 14 and 16.
- Existing automated suite protected: every task includes focused and full regression runs.
- Documentation and cleanup: Tasks 1 and 15.
