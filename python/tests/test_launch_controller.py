import tempfile
import unittest

from launch_controller import LaunchController, LaunchResult
from launcher_state import LaunchOptions


class FakeStateStore:
    def __init__(self):
        self.recents = []

    def record_recent(self, path):
        self.recents.append(path)


class LaunchControllerTests(unittest.TestCase):
    def make_controller(self, launcher, state=None):
        return LaunchController(
            launcher=launcher,
            state_store=state or FakeStateStore(),
            claude_path="claude.exe",
            hermes_path="hermes.exe",
            claude_skip_args="--skip-checks",
        )

    def test_claude_launch_without_skip_permissions_passes_empty_args(self):
        calls = []
        controller = self.make_controller(lambda **kwargs: calls.append(kwargs) or True)
        with tempfile.TemporaryDirectory() as tmp:
            result = controller.launch("claude", tmp, LaunchOptions())
        self.assertEqual(result, LaunchResult(True, "claude", "window", ""))
        self.assertEqual(calls[0]["args"], "")

    def test_claude_launch_with_skip_permissions_passes_configured_flag(self):
        calls = []
        controller = self.make_controller(lambda **kwargs: calls.append(kwargs) or True)
        with tempfile.TemporaryDirectory() as tmp:
            controller.launch("claude", tmp, LaunchOptions(skip_permissions=True))
        self.assertEqual(calls[0]["args"], "--skip-checks")

    def test_tab_mode_is_forwarded_and_success_updates_recents(self):
        calls = []
        state = FakeStateStore()
        controller = self.make_controller(lambda **kwargs: calls.append(kwargs) or True, state)
        with tempfile.TemporaryDirectory() as tmp:
            result = controller.launch("hermes", tmp, LaunchOptions(terminal_mode="tab"))
            self.assertEqual(state.recents, [tmp])
        self.assertTrue(result.success)
        self.assertEqual(calls[0]["terminal_mode"], "tab")

    def test_failed_launch_does_not_update_recents(self):
        state = FakeStateStore()
        controller = self.make_controller(lambda **_kwargs: False, state)
        with tempfile.TemporaryDirectory() as tmp:
            result = controller.launch("claude", tmp, LaunchOptions())
        self.assertFalse(result.success)
        self.assertEqual(state.recents, [])

    def test_missing_directory_returns_actionable_error(self):
        controller = self.make_controller(lambda **_kwargs: True)
        result = controller.launch("claude", "missing-directory", LaunchOptions())
        self.assertFalse(result.success)
        self.assertEqual(result.error, "directory not found")

    def test_launcher_exception_is_returned_without_state_update(self):
        state = FakeStateStore()

        def fail(**_kwargs):
            raise OSError("terminal executable not found")

        controller = self.make_controller(fail, state)
        with tempfile.TemporaryDirectory() as tmp:
            result = controller.launch("claude", tmp, LaunchOptions())
        self.assertFalse(result.success)
        self.assertIn("terminal executable not found", result.error)
        self.assertEqual(state.recents, [])


if __name__ == "__main__":
    unittest.main()
