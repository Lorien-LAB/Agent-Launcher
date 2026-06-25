import unittest

from launcher_view import DirectoryRow, compose_home_rows, truncate_middle


class LauncherViewHelperTests(unittest.TestCase):
    def test_home_rows_show_favorites_first_without_duplicates(self):
        rows = compose_home_rows(
            favorites=[r"D:\Alpha", r"D:\Beta"],
            recents=[r"D:\Beta", r"D:\Gamma"],
        )
        self.assertEqual(
            rows,
            [
                DirectoryRow("favorite", r"D:\Alpha", True),
                DirectoryRow("favorite", r"D:\Beta", True),
                DirectoryRow("recent", r"D:\Gamma", False),
            ],
        )

    def test_middle_truncation_preserves_path_end(self):
        value = r"D:\University\Long Folder Name\Project"
        result = truncate_middle(value, 24)
        self.assertLessEqual(len(result), 24)
        self.assertTrue(result.endswith("Project"))
        self.assertIn("…", result)


if __name__ == "__main__":
    unittest.main()
