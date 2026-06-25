from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

import _bootstrap  # noqa: F401

from launcher_state import AppearanceSettings, LaunchOptions
from launcher_visual_coordinator import VisualLauncherCoordinator


class LauncherVisualCoordinatorTests(unittest.TestCase):
    def build(self):
        root = MagicMock()
        root.winfo_screenwidth.return_value = 1920
        root.winfo_screenheight.return_value = 1080
        root.winfo_x.return_value = 20
        root.winfo_y.return_value = 30

        state_store = MagicMock()
        state_store.state = SimpleNamespace(
            favorites=[],
            recent_directories=[],
            launch_options=LaunchOptions(),
        )
        state_store.recovered_corrupt_file = False

        animator = MagicMock()
        animator.running = False

        def animate(*_args, **kwargs):
            kwargs["on_progress"](1.0)
            kwargs["on_complete"]()
            return True

        animator.animate_to.side_effect = animate

        appearance = MagicMock()
        appearance.applied_settings = AppearanceSettings("none", 100)
        appearance.is_dirty = False

        coordinator = VisualLauncherCoordinator(
            root=root,
            state_store=state_store,
            directory_index=MagicMock(),
            window_animator=animator,
            appearance_controller=appearance,
            launch_controller=MagicMock(),
        )
        view = MagicMock()
        view.reduced_motion_enabled.return_value = False
        coordinator.view = view
        return coordinator, view, appearance, animator

    def test_preview_marks_appearance_dirty(self):
        coordinator, view, appearance, _animator = self.build()
        settings = AppearanceSettings("acrylic", 70)
        coordinator.preview_appearance(settings)
        appearance.preview.assert_called_once_with(settings)
        view.set_appearance_dirty.assert_called_with(True, False)

    def test_apply_marks_appearance_clean_and_applied(self):
        coordinator, view, appearance, _animator = self.build()
        coordinator.apply_appearance()
        appearance.apply.assert_called_once_with()
        view.set_appearance_dirty.assert_called_with(False, True)

    def test_toggle_mode_drives_view_transition(self):
        coordinator, view, _appearance, animator = self.build()
        coordinator.toggle_mode()
        view.prepare_mode_transition.assert_called_once_with(True)
        view.update_mode_transition.assert_called_with(True, 1.0)
        view.finish_mode_transition.assert_called_with(True)
        self.assertIn("on_progress", animator.animate_to.call_args.kwargs)
        self.assertFalse(animator.animate_to.call_args.kwargs["reduced_motion"])


if __name__ == "__main__":
    unittest.main()
