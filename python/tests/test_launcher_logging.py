import logging
import pathlib
import tempfile
import unittest

from launcher_logging import configure_launcher_logger


class LauncherLoggingTests(unittest.TestCase):
    def test_logger_creates_rotating_file_handler(self):
        with tempfile.TemporaryDirectory() as tmp:
            logger = configure_launcher_logger(pathlib.Path(tmp) / "agent-launcher.log")
            logger.info("indexed %s directories", 12)
            for handler in logger.handlers:
                handler.flush()

            log_path = pathlib.Path(tmp) / "agent-launcher.log"
            self.assertTrue(log_path.exists())
            self.assertIn("indexed 12 directories", log_path.read_text(encoding="utf-8"))

    def test_reconfiguration_does_not_duplicate_handlers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "agent-launcher.log"
            first = configure_launcher_logger(path)
            second = configure_launcher_logger(path)
            self.assertIs(first, second)
            self.assertEqual(len(second.handlers), 1)
            self.assertIsInstance(second.handlers[0], logging.Handler)


if __name__ == "__main__":
    unittest.main()
