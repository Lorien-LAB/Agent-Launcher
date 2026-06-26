from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401

from launcher_quiet_branding import quiet_brand_palette
from launcher_theme import COLORS, interpolate_hex


class QuietBrandingTests(unittest.TestCase):
    def test_quiet_palette_uses_subtle_accent_mix(self):
        palette = quiet_brand_palette(COLORS, "claude")
        self.assertEqual(
            interpolate_hex(COLORS["surface_1"], COLORS["claude"], 0.10),
            palette.normal,
        )
        self.assertEqual(
            interpolate_hex(COLORS["surface_1"], COLORS["claude"], 0.18),
            palette.hover,
        )
        self.assertEqual(COLORS["glass_border"], palette.border)


if __name__ == "__main__":
    unittest.main()
