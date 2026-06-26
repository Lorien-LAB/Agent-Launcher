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
        self.assertEqual(50, METRICS.directory_row_height)
        self.assertGreaterEqual(METRICS.card_radius, 18)
        self.assertGreaterEqual(METRICS.button_radius, 14)
        self.assertGreaterEqual(METRICS.input_radius, 16)
        self.assertGreaterEqual(METRICS.row_radius, 14)


if __name__ == "__main__":
    unittest.main()
