from __future__ import annotations

import pathlib
import tempfile
import unittest

import _bootstrap  # noqa: F401

from launcher_background import GlowSpec
from launcher_directory_row import action_kind_for_section
from launcher_dynamic_background import animate_glow, sample_glow_color
from launcher_geometry import stable_rounded_rectangle_points
from launcher_scrollbar import thumb_geometry
from launcher_state import LauncherStateStore
from launcher_surfaces import glass_content_inset, glass_layer_spec


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

    def test_glass_content_stays_clear_of_rounded_corners(self):
        self.assertEqual(13, glass_content_inset(22, 7))
        self.assertEqual(14, glass_content_inset(18, 14))

    def test_glass_surface_has_shadow_rim_and_sheen(self):
        spec = glass_layer_spec(320, 180, 22)
        self.assertEqual((2, 4, 318, 179), spec.shadow_bounds)
        self.assertEqual((2, 2, 318, 177), spec.panel_bounds)
        self.assertGreater(spec.sheen_end_x, spec.sheen_start_x)
        self.assertLess(spec.inner_radius, spec.outer_radius)

    def test_sampled_backdrop_matches_glow_position(self):
        theme = {"purple": "#8367F4", "blue": "#527EF5"}
        glow = GlowSpec("purple", 100, 80, 120, 0.30)
        near = sample_glow_color("#090B12", theme, [glow], 100, 80)
        far = sample_glow_color("#090B12", theme, [glow], 400, 400)
        self.assertNotEqual("#090B12", near)
        self.assertEqual("#090B12", far)

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
