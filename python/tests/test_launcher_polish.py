from __future__ import annotations

import pathlib
import tempfile
import unittest

import _bootstrap  # noqa: F401

from launcher_background import GlowSpec
from launcher_directory_row import action_kind_for_section
from launcher_dynamic_background import animate_glow
from launcher_geometry import stable_rounded_rectangle_points
from launcher_scrollbar import thumb_geometry
from launcher_state import LauncherStateStore


class LauncherPolishTests(unittest.TestCase):
    def test_stable_rounding_never_extends_past_bounds(self):
        points = stable_rounded_rectangle_points(2, 3, 102, 43, 18)
        xs = points[0::2]
        ys = points[1::2]
        self.assertGreaterEqual(min(xs), 2)
        self.assertLessEqual(max(xs), 102)
        self.assertGreaterEqual(min(ys), 3)
        self.assertLessEqual(max(ys), 43)
        self.assertGreaterEqual(len(points), 40)

    def test_recent_rows_use_remove_action(self):
        self.assertEqual("remove", action_kind_for_section("recent"))
        self.assertEqual("favorite", action_kind_for_section("favorite"))
        self.assertEqual("favorite", action_kind_for_section("search"))

    def test_remove_recent_only_changes_launcher_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            first = root / "first"
            second = root / "second"
            first.mkdir()
            second.mkdir()
            store = LauncherStateStore(root / "launcher-state.json")
            store.load()
            store.record_recent(str(first))
            store.record_recent(str(second))

            self.assertTrue(store.remove_recent(str(first)))
            self.assertEqual([str(second)], store.state.recent_directories)
            self.assertTrue(first.is_dir())
            self.assertFalse(store.remove_recent(str(first)))

    def test_dynamic_glow_moves_and_strengthens_background(self):
        base = GlowSpec("purple", 80, 60, 220, 0.32)
        start = animate_glow(base, 0.0)
        moved = animate_glow(base, 1.2)
        self.assertNotEqual((start.center_x, start.center_y), (moved.center_x, moved.center_y))
        self.assertGreater(moved.radius, base.radius)
        self.assertGreaterEqual(moved.opacity, base.opacity * 1.08)
        self.assertLessEqual(moved.opacity, base.opacity * 1.24)

    def test_scrollbar_thumb_is_inset_and_has_minimum_height(self):
        top, bottom = thumb_geometry(0.2, 0.3, height=300, min_height=34, inset=3)
        self.assertGreaterEqual(top, 3)
        self.assertLessEqual(bottom, 297)
        self.assertGreaterEqual(bottom - top, 34)


if __name__ == "__main__":
    unittest.main()
