from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401

from launcher_chrome import (
    ChromeState,
    DragAnchor,
    LauncherChromeController,
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


class FakeRoot:
    def __init__(self):
        self.calls = []
        self.geometry_value = "820x560+100+100"

    def overrideredirect(self, value):
        self.calls.append(("overrideredirect", value))

    def update_idletasks(self):
        self.calls.append(("update_idletasks", None))

    def winfo_id(self):
        return 123

    def winfo_x(self):
        return 100

    def winfo_y(self):
        return 100

    def winfo_width(self):
        return 820

    def winfo_height(self):
        return 560

    def geometry(self, value=None):
        if value is not None:
            self.geometry_value = value
            self.calls.append(("geometry", value))
        return self.geometry_value


class FakePlatform:
    def __init__(self):
        self.rounded = []
        self.taskbar = []
        self.minimized = []

    def resolve_toplevel(self, hwnd):
        return hwnd + 1000

    def apply_rounded_corners(self, hwnd, enabled=True):
        self.rounded.append((hwnd, enabled))
        return True

    def ensure_taskbar_presence(self, hwnd):
        self.taskbar.append(hwnd)
        return True

    def minimize_window(self, hwnd):
        self.minimized.append(hwnd)
        return True


class LauncherChromeAdapterTests(unittest.TestCase):
    def test_apply_frameless_enables_override_rounding_and_taskbar_style(self):
        root = FakeRoot()
        platform = FakePlatform()
        controller = LauncherChromeController(root, platform=platform)

        controller.apply_frameless()

        self.assertIn(("overrideredirect", True), root.calls)
        self.assertEqual([1123], platform.taskbar)
        self.assertEqual([(1123, True)], platform.rounded)

    def test_native_minimize_keeps_override_enabled(self):
        root = FakeRoot()
        platform = FakePlatform()
        controller = LauncherChromeController(root, platform=platform)

        self.assertTrue(controller.minimize_native())

        self.assertEqual([1123], platform.minimized)
        self.assertNotIn(("overrideredirect", False), root.calls)

    def test_drag_uses_pointer_offset(self):
        root = FakeRoot()
        controller = LauncherChromeController(root, platform=FakePlatform())
        begin = type("Event", (), {"x_root": 120, "y_root": 130})()
        move = type("Event", (), {"x_root": 150, "y_root": 180})()

        controller.begin_drag(begin)
        controller.drag(move)

        self.assertEqual("820x560+130+150", root.geometry_value)


if __name__ == "__main__":
    unittest.main()
