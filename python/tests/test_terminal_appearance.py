import unittest

from launcher_state import AppearanceSettings
from terminal_appearance import TerminalAppearanceController


class TerminalAppearanceTests(unittest.TestCase):
    def test_preview_writes_terminal_settings_without_persisting_launcher_state(self):
        writes = []
        persisted = []
        controller = TerminalAppearanceController(
            reader=lambda: AppearanceSettings("none", 100),
            writer=writes.append,
            persist=persisted.append,
        )
        controller.preview(AppearanceSettings("acrylic", 45))
        self.assertEqual(writes, [AppearanceSettings("acrylic", 45)])
        self.assertEqual(persisted, [])
        self.assertTrue(controller.is_dirty)

    def test_apply_persists_preview_and_clears_dirty_state(self):
        writes = []
        persisted = []
        controller = TerminalAppearanceController(
            reader=lambda: AppearanceSettings("none", 100),
            writer=writes.append,
            persist=persisted.append,
        )
        settings = AppearanceSettings("opacity", 70)
        controller.preview(settings)
        controller.apply()
        self.assertEqual(persisted, [settings])
        self.assertFalse(controller.is_dirty)

    def test_cancel_restores_last_applied_settings(self):
        writes = []
        controller = TerminalAppearanceController(
            reader=lambda: AppearanceSettings("none", 100),
            writer=writes.append,
            persist=lambda _settings: None,
        )
        controller.preview(AppearanceSettings("acrylic", 30))
        controller.cancel()
        self.assertEqual(writes[-1], AppearanceSettings("none", 100))
        self.assertFalse(controller.is_dirty)

    def test_failed_preview_keeps_previous_preview_state(self):
        applied = AppearanceSettings("none", 100)

        def fail(_settings):
            raise OSError("settings locked")

        controller = TerminalAppearanceController(
            reader=lambda: applied,
            writer=fail,
            persist=lambda _settings: None,
        )
        with self.assertRaisesRegex(OSError, "settings locked"):
            controller.preview(AppearanceSettings("opacity", 60))
        self.assertEqual(controller.preview_settings, applied)
        self.assertFalse(controller.is_dirty)


if __name__ == "__main__":
    unittest.main()
