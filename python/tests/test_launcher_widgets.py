from __future__ import annotations

import os
import sys
import unittest

import _bootstrap  # noqa: F401

from launcher_background import blend_for_glow, glow_spec_for_mode
from launcher_branding import brand_visual_spec, glass_palette
from launcher_search_field import search_field_metrics
from launcher_theme import COLORS
from launcher_widgets import (
    SegmentedState,
    ToggleState,
    WidgetVisualState,
    resolve_button_colors,
    rounded_rectangle_points,
    scrollbar_should_show,
)


class LauncherWidgetHelperTests(unittest.TestCase):
    def test_rounded_rectangle_points_stay_inside_bounds(self):
        points = rounded_rectangle_points(0, 0, 100, 40, 12)
        xs = points[0::2]
        ys = points[1::2]
        self.assertGreaterEqual(min(xs), 0)
        self.assertLessEqual(max(xs), 100)
        self.assertGreaterEqual(min(ys), 0)
        self.assertLessEqual(max(ys), 40)

    def test_disabled_button_wins_over_hover(self):
        state = WidgetVisualState(
            hovered=True,
            pressed=False,
            focused=True,
            enabled=False,
        )
        colors = resolve_button_colors(
            state,
            normal="#111111",
            hover="#222222",
            pressed="#333333",
            disabled="#444444",
        )
        self.assertEqual("#444444", colors.background)

    def test_segmented_state_rejects_unknown_value(self):
        state = SegmentedState(("window", "tab"), "window")
        with self.assertRaises(ValueError):
            state.select("missing")

    def test_toggle_state_flips_and_emits(self):
        emitted = []
        state = ToggleState(False, emitted.append)
        state.toggle()
        self.assertTrue(state.value)
        self.assertEqual([True], emitted)

    def test_overlay_scrollbar_visibility_contract(self):
        self.assertFalse(scrollbar_should_show(0.0, 1.0))
        self.assertTrue(scrollbar_should_show(0.1, 0.6))
        self.assertTrue(scrollbar_should_show(0.0, 0.99))

    def test_brand_buttons_use_glass_style_and_official_marks(self):
        claude = brand_visual_spec("claude")
        hermes = brand_visual_spec("hermes")
        self.assertEqual("claude_burst", claude.icon_kind)
        self.assertEqual("nous_wordmark", hermes.icon_kind)
        self.assertGreaterEqual(claude.radius, 14)
        self.assertGreaterEqual(hermes.radius, 14)

        palette = glass_palette(COLORS, "claude")
        self.assertNotEqual(COLORS["claude"], palette.normal)
        self.assertNotEqual(palette.normal, palette.hover)
        self.assertEqual(COLORS["text_primary"], palette.text)

    def test_search_icon_is_large_and_uses_windows_search_glyph(self):
        metrics = search_field_metrics()
        self.assertEqual("\ue721", metrics.glyph)
        self.assertGreaterEqual(metrics.font_size, 16)
        self.assertGreater(metrics.text_x, metrics.icon_x)


class LauncherBackgroundTests(unittest.TestCase):
    def test_compact_mode_has_one_purple_glow(self):
        glows = glow_spec_for_mode(False, 380, 420)
        self.assertEqual(1, len(glows))
        self.assertEqual("purple", glows[0].role)
        self.assertLessEqual(glows[0].opacity, 0.14)

    def test_expanded_mode_adds_blue_project_glow(self):
        glows = glow_spec_for_mode(True, 820, 560)
        self.assertEqual(["purple", "blue"], [glow.role for glow in glows])
        self.assertLessEqual(glows[1].opacity, 0.10)

    def test_glow_blending_is_clamped(self):
        self.assertEqual("#090B12", blend_for_glow("#090B12", "#8B5CF6", -1))
        self.assertEqual("#8B5CF6", blend_for_glow("#090B12", "#8B5CF6", 2))


@unittest.skipUnless(os.environ.get("DISPLAY") or sys.platform == "win32", "Tk display required")
class LauncherWidgetTkTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk

        self.tk = tk
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_button_invoke_calls_command_once(self):
        from launcher_widgets import GhostButton

        calls = []
        button = GhostButton(
            self.root,
            text="Refresh",
            command=lambda: calls.append("called"),
            theme=COLORS,
            scale=lambda value: value,
        )
        button.invoke()
        self.assertEqual(["called"], calls)

    def test_programmatic_segment_change_does_not_emit(self):
        from launcher_widgets import SegmentedControl

        variable = self.tk.StringVar(value="window")
        emitted = []
        control = SegmentedControl(
            self.root,
            options=(("window", "New window"), ("tab", "New tab")),
            variable=variable,
            command=emitted.append,
            theme=COLORS,
            scale=lambda value: value,
        )
        control.set_value("tab", emit=False)
        self.assertEqual("tab", variable.get())
        self.assertEqual([], emitted)

    def test_programmatic_toggle_change_does_not_emit(self):
        from launcher_widgets import ToggleSwitch

        variable = self.tk.BooleanVar(value=False)
        emitted = []
        toggle = ToggleSwitch(
            self.root,
            variable=variable,
            command=emitted.append,
            theme=COLORS,
            scale=lambda value: value,
        )
        toggle.set_value(True, emit=False)
        self.assertTrue(variable.get())
        self.assertEqual([], emitted)


if __name__ == "__main__":
    unittest.main()
