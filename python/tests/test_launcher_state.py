import json
import pathlib
import tempfile
import unittest

from launcher_state import (
    AppearanceSettings,
    LaunchOptions,
    LauncherStateStore,
)


class LauncherStateStoreTests(unittest.TestCase):
    def test_defaults_are_compact_window_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LauncherStateStore(pathlib.Path(tmp) / "launcher-state.json")
            state = store.load()
            self.assertEqual(state.window_x, 120)
            self.assertEqual(state.window_y, 80)
            self.assertEqual(state.favorites, [])
            self.assertEqual(state.recent_directories, [])
            self.assertEqual(state.launch_options, LaunchOptions())
            self.assertEqual(state.appearance, AppearanceSettings())

    def test_favorites_are_normalized_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            project = root / "Project"
            project.mkdir()
            store = LauncherStateStore(root / "launcher-state.json")
            store.load()
            store.toggle_favorite(str(project))
            store.toggle_favorite(str(project).upper())
            self.assertEqual(store.state.favorites, [])
            store.toggle_favorite(str(project))
            self.assertEqual(len(store.state.favorites), 1)

    def test_recent_directories_are_deduplicated_and_limited_to_eight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            store = LauncherStateStore(root / "launcher-state.json")
            store.load()
            projects = []
            for index in range(10):
                project = root / f"p{index}"
                project.mkdir()
                projects.append(project)
                store.record_recent(str(project))
            store.record_recent(str(projects[5]))
            self.assertEqual(len(store.state.recent_directories), 8)
            self.assertEqual(store.state.recent_directories[0], str(projects[5]))

    def test_corrupt_file_is_backed_up_and_defaults_are_returned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            path = root / "launcher-state.json"
            path.write_text("{not-json", encoding="utf-8")
            store = LauncherStateStore(path)
            state = store.load()
            self.assertEqual(state.favorites, [])
            backups = list(root.glob("launcher-state.corrupt-*.json"))
            self.assertEqual(len(backups), 1)
            self.assertTrue(store.recovered_corrupt_file)

    def test_save_writes_valid_json_without_leaving_tmp_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            path = root / "launcher-state.json"
            store = LauncherStateStore(path)
            store.load()
            store.update_window_position(42, 84)
            store.update_launch_options(
                LaunchOptions(
                    terminal_mode="tab",
                    skip_permissions=True,
                    hide_after_launch=True,
                )
            )
            store.save()
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["window"], {"x": 42, "y": 84})
            self.assertEqual(payload["launch_options"]["terminal_mode"], "tab")
            self.assertFalse(path.with_suffix(".json.tmp").exists())

    def test_unsupported_values_fall_back_to_corrupt_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "launcher-state.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "window": {"x": 0, "y": 0},
                        "favorites": [],
                        "recent_directories": [],
                        "launch_options": {"terminal_mode": "bad"},
                        "appearance": {"mode": "none", "opacity": 50},
                    }
                ),
                encoding="utf-8",
            )
            store = LauncherStateStore(path)
            state = store.load()
            self.assertEqual(state.launch_options, LaunchOptions())
            self.assertTrue(store.recovered_corrupt_file)


if __name__ == "__main__":
    unittest.main()
