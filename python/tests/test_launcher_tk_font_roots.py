from __future__ import annotations

import os
import sys
import unittest

import _bootstrap  # noqa: F401

from launcher_theme import COLORS


@unittest.skipUnless(os.environ.get("DISPLAY") or sys.platform == "win32", "Tk display required")
class LauncherTkFontRootTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk

        self.tk = tk
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_search_field_constructs_with_tk_root(self):
        from launcher_search_field import SearchField

        field = SearchField(
            self.root,
            variable=self.tk.StringVar(value=""),
            theme=COLORS,
            scale=lambda value: value,
            placeholder="Search",
        )
        self.assertTrue(field.winfo_exists())

    def test_directory_row_constructs_with_tk_root(self):
        from launcher_directory_row import DirectoryRowWidget
        from launcher_view_models import DirectoryRow

        row = DirectoryRowWidget(
            self.root,
            DirectoryRow("recent", r"C:\\Projects\\Agent-Launcher", False),
            theme=COLORS,
            scale=lambda value: value,
            is_available=lambda _path: True,
        )
        self.assertTrue(row.winfo_exists())


if __name__ == "__main__":
    unittest.main()
