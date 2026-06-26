from __future__ import annotations

import os
import unittest

import _bootstrap  # noqa: F401

from launcher_directory_row import (
    build_row_presentation,
    directory_row_geometry,
    fit_text_to_width,
)


class LauncherDirectoryRowTests(unittest.TestCase):
    def test_presentation_uses_basename_and_middle_truncated_path(self):
        path = os.path.join("C:\\", "Users", "Lorien", "projects", "agent-launcher")
        presentation = build_row_presentation(path, available=True, path_limit=24)
        self.assertEqual("agent-launcher", presentation.name)
        self.assertLessEqual(len(presentation.path_text), 24)
        self.assertFalse(presentation.unavailable)

    def test_unavailable_path_gets_status_suffix(self):
        presentation = build_row_presentation(
            "C:\\missing\\project",
            available=False,
            path_limit=40,
        )
        self.assertTrue(presentation.unavailable)
        self.assertIn("Unavailable", presentation.path_text)

    def test_root_path_keeps_meaningful_name(self):
        presentation = build_row_presentation("C:\\", available=True, path_limit=12)
        self.assertEqual("C:\\", presentation.name)

    def test_width_aware_truncation_reserves_space_for_favorite_control(self):
        value = "AFAC2026挑战组-赛题一：市场参与者交易行为识别与资金流向分析"

        def measure(text):
            return sum(14 if ord(character) > 127 else 7 for character in text)

        result = fit_text_to_width(value, 245, measure)
        self.assertLessEqual(measure(result), 245)
        self.assertIn("…", result)
        self.assertTrue(result.startswith("AFAC2026"))
        self.assertTrue(result.endswith("分析"))

    def test_width_aware_truncation_leaves_short_names_unchanged(self):
        self.assertEqual(
            "futures_analysis",
            fit_text_to_width("futures_analysis", 200, lambda text: len(text) * 7),
        )

    def test_geometry_removes_folder_icon_and_enlarges_favorite(self):
        geometry = directory_row_geometry(320, scale=1.0)
        self.assertLessEqual(geometry.text_x, 16)
        self.assertGreaterEqual(geometry.name_font_size, 11)
        self.assertGreaterEqual(geometry.favorite_font_size, 14)
        self.assertGreaterEqual(geometry.favorite_hit_radius, 16)
        self.assertGreater(geometry.text_width, 240)


if __name__ == "__main__":
    unittest.main()
