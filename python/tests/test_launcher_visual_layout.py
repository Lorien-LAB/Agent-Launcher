from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401

from launcher_runtime import launcher_window_sizes
from launcher_view_models import layout_spec


class LauncherVisualLayoutTests(unittest.TestCase):
    def test_compact_layout_is_search_first(self):
        spec = layout_spec(False)
        self.assertEqual(
            (
                "titlebar",
                "search",
                "directory_list",
                "compact_footer",
                "status",
            ),
            spec.sections,
        )
        self.assertFalse(spec.show_settings)

    def test_expanded_layout_uses_equal_columns(self):
        spec = layout_spec(True)
        self.assertEqual((1, 1), spec.column_weights)
        self.assertTrue(spec.show_settings)

    def test_runtime_sizes_follow_theme(self):
        self.assertEqual(
            ((380, 420), (820, 560)),
            launcher_window_sizes(1.0),
        )


if __name__ == "__main__":
    unittest.main()
