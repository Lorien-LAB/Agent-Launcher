import importlib.util
import os
import pathlib
import sys
import types
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
os.environ.setdefault("LOCALAPPDATA", str(ROOT / ".localappdata"))

# Keep the helper tests independent of optional desktop-only dependencies.
sys.modules.setdefault("pystray", types.SimpleNamespace())
if "PIL" not in sys.modules:
    pil = types.ModuleType("PIL")
    pil.Image = types.SimpleNamespace()
    sys.modules["PIL"] = pil
sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location("terminal_manager_under_test", ROOT / "terminal_manager.py")
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class SessionPanelHelperTests(unittest.TestCase):
    def test_clamp_pct(self):
        self.assertEqual(module._clamp_pct(-1), 0.0)
        self.assertEqual(module._clamp_pct(42.5), 42.5)
        self.assertEqual(module._clamp_pct(120), 100.0)
        self.assertEqual(module._clamp_pct("bad"), 0.0)

    def test_short_model_name(self):
        self.assertEqual(module._short_model_name("deepseek-v4-pro"), "DSv4")
        self.assertEqual(
            module._short_model_name("claude-sonnet-4-20250514"),
            "sonnet-4-20250514",
        )
        self.assertEqual(module._short_model_name("?"), "")
        self.assertEqual(module._short_model_name(""), "")

    def test_updated_age(self):
        self.assertEqual(module._format_updated_age(97.0, now=100.0), "Updated 3s ago")
        self.assertEqual(module._format_updated_age(1.0, now=100.0), "Updated 1m ago")
        self.assertEqual(module._format_updated_age(0.0, now=100.0), "Updated —")

    def test_progress_fill_width(self):
        self.assertEqual(module._progress_fill_width(200, 0), 0)
        self.assertEqual(module._progress_fill_width(200, 50), 100)
        self.assertEqual(module._progress_fill_width(200, 150), 200)

    def test_status_style(self):
        self.assertEqual(module._status_style("running")[0], "RUNNING")
        self.assertEqual(module._status_style("done")[0], "DONE")
        self.assertEqual(module._status_style("idle")[0], "IDLE")

    def test_context_text_color_thresholds(self):
        self.assertEqual(module._context_text_color(69.9), module.C.panel_sub)
        self.assertEqual(module._context_text_color(70), module.C.yellow)
        self.assertEqual(module._context_text_color(85), module.C.orange)
        self.assertEqual(module._context_text_color(95), module.C.red)


if __name__ == "__main__":
    unittest.main()
