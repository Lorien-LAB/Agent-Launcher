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
