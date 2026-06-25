import _bootstrap  # noqa: F401
import pathlib
import tempfile
import threading
import unittest

from directory_index import DirectoryIndex


class DirectoryIndexTests(unittest.TestCase):
    def test_scan_recurses_and_excludes_heavy_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "Alpha" / "Nested").mkdir(parents=True)
            (root / "node_modules" / "Hidden").mkdir(parents=True)
            index = DirectoryIndex([str(root)])
            snapshot, failures = index.scan_now()
            paths = {entry.path for entry in snapshot}
            self.assertIn(str(root / "Alpha"), paths)
            self.assertIn(str(root / "Alpha" / "Nested"), paths)
            self.assertNotIn(str(root / "node_modules"), paths)
            self.assertEqual(failures, ())

    def test_overlapping_roots_do_not_duplicate_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            child = root / "Project"
            (child / "src").mkdir(parents=True)
            index = DirectoryIndex([str(root), str(child)])
            snapshot, _failures = index.scan_now()
            normalized = [entry.normalized_path for entry in snapshot]
            self.assertEqual(len(normalized), len(set(normalized)))

    def test_search_ranks_exact_prefix_contains_then_relative_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for relative in ("alpha", "alphabet", "my-alpha-project", "group/other", "alpha-parent/child"):
                (root / relative).mkdir(parents=True)
            index = DirectoryIndex([str(root)])
            index.scan_now()
            results = index.search("alpha", {str(root / "alphabet"): 10.0})
            self.assertEqual(results[0].name, "alpha")
            self.assertEqual(results[1].name, "alphabet")
            self.assertEqual(results[2].name, "alpha-parent")
            self.assertEqual(results[3].name, "my-alpha-project")

    def test_relative_path_match_is_included(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            target = root / "group-name" / "other"
            target.mkdir(parents=True)
            index = DirectoryIndex([str(root)])
            index.scan_now()
            results = index.search("group-name")
            self.assertIn(str(target), [entry.path for entry in results])

    def test_async_refresh_marshals_completion_through_scheduler(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "Project").mkdir()
            scheduled = []
            completed = threading.Event()

            def scheduler(callback):
                scheduled.append(callback)

            index = DirectoryIndex([str(root)])
            index.refresh_async(scheduler=scheduler, on_complete=lambda snapshot, failures: completed.set())
            index.wait(timeout=2.0)
            self.assertEqual(len(scheduled), 1)
            self.assertFalse(completed.is_set())
            scheduled[0]()
            self.assertTrue(completed.is_set())


if __name__ == "__main__":
    unittest.main()
