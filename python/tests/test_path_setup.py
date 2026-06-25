import pathlib
import sys
import unittest


PYTHON_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))


class PathSetupTests(unittest.TestCase):
    def test_python_directory_is_importable(self):
        self.assertIn(str(PYTHON_DIR), sys.path)


if __name__ == "__main__":
    unittest.main()
