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


if __name__ == "__main__":
    unittest.main()
