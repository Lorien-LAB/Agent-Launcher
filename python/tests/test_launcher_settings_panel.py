from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401

from launcher_settings_panel import appearance_status_text, project_summary


class LauncherSettingsPanelHelperTests(unittest.TestCase):
    def test_project_summary_handles_empty_selection(self):
        summary = project_summary(None)
        self.assertEqual("No project selected", summary.name)
        self.assertEqual("Choose a project from the list", summary.path)
        self.assertFalse(summary.actions_enabled)

    def test_project_summary_uses_directory_name(self):
        summary = project_summary(r"C:\Users\Lorien\Agent-Launcher")
        self.assertEqual("Agent-Launcher", summary.name)
        self.assertTrue(summary.actions_enabled)

    def test_appearance_status_text(self):
        self.assertEqual("Previewing", appearance_status_text(True, False))
        self.assertEqual("Applied", appearance_status_text(False, True))
        self.assertEqual("No changes", appearance_status_text(False, False))


if __name__ == "__main__":
    unittest.main()
