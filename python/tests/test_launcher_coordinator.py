import types
import unittest

from launch_controller import LaunchResult
from launcher_coordinator import LauncherCoordinator
from launcher_state import AppearanceSettings, LaunchOptions


class FakeRoot:
    def __init__(self):
        self.withdrawn = False

    def after(self, _delay, callback):
        callback()
        return "after-1"

    def withdraw(self):
        self.withdrawn = True

    def winfo_screenwidth(self):
        return 1920

    def winfo_screenheight(self):
        return 1080

    def winfo_x(self):
        return 20

    def winfo_y(self):
        return 30

    def clipboard_clear(self):
        pass

    def clipboard_append(self, _value):
        pass


class FakeStateStore:
    def __init__(self):
        self.state = types.SimpleNamespace(
            favorites=[],
            recent_directories=[],
            launch_options=LaunchOptions(hide_after_launch=True),
        )
        self.recovered_corrupt_file = False

    def update_launch_options(self, options):
        self.state.launch_options = options

    def toggle_favorite(self, _path):
        return True

    def update_window_position(self, _x, _y):
        pass

    def save(self):
        pass


class FakeView:
    def __init__(self):
        self.statuses = []
        self.search_var = types.SimpleNamespace(get=lambda: "")
        self.expanded = False
        self.appearance = None

    def set_launch_options(self, _options):
        pass

    def set_appearance(self, settings):
        self.appearance = settings

    def render_home(self, _favorites, _recents):
        pass

    def set_indexing(self, _active):
        pass

    def set_status(self, message, error=False):
        self.statuses.append((message, error))

    def set_selected_path(self, _path):
        pass

    def set_expanded(self, expanded):
        self.expanded = expanded

    def destroy(self):
        pass


class FakeIndex:
    snapshot = ()

    def refresh_async(self, scheduler, on_complete):
        scheduler(lambda: on_complete((), ()))
        return True

    def search(self, *_args):
        return []

    def stop(self):
        pass


class FakeAnimator:
    running = False

    def __init__(self):
        self.calls = []

    def animate_to(self, *args):
        self.calls.append(args)
        return True

    def cancel(self):
        pass


class FakeAppearance:
    def __init__(self):
        self.applied_settings = AppearanceSettings("none", 100)
        self.is_dirty = False
        self.cancelled = False

    def cancel(self):
        self.cancelled = True
        self.is_dirty = False
        return self.applied_settings


class FakeLauncher:
    def launch(self, agent, directory, options):
        return LaunchResult(True, agent, options.terminal_mode)


class LauncherCoordinatorTests(unittest.TestCase):
    def build(self):
        root = FakeRoot()
        appearance = FakeAppearance()
        coordinator = LauncherCoordinator(
            root=root,
            state_store=FakeStateStore(),
            directory_index=FakeIndex(),
            window_animator=FakeAnimator(),
            appearance_controller=appearance,
            launch_controller=FakeLauncher(),
        )
        view = FakeView()
        coordinator.view = view
        return coordinator, root, view, appearance

    def test_successful_launch_hides_launcher_when_enabled(self):
        coordinator, root, _view, _appearance = self.build()
        coordinator.selected_directory = "."
        coordinator.launch_selected("claude")
        self.assertTrue(root.withdrawn)

    def test_collapse_rolls_back_dirty_appearance(self):
        coordinator, _root, view, appearance = self.build()
        coordinator.expanded = True
        appearance.is_dirty = True
        coordinator.toggle_mode()
        self.assertTrue(appearance.cancelled)
        self.assertFalse(view.expanded)


if __name__ == "__main__":
    unittest.main()
