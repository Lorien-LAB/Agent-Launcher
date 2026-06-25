from __future__ import annotations

from dataclasses import dataclass

from launcher_theme import preferred_font_family


@dataclass(frozen=True)
class CaptionGlyphs:
    minimize: str
    maximize: str
    restore: str
    close: str


def caption_glyphs() -> CaptionGlyphs:
    """Return the Windows caption glyphs shared by Fluent and MDL2 fonts."""
    return CaptionGlyphs(
        minimize="\ue921",
        maximize="\ue922",
        restore="\ue923",
        close="\ue8bb",
    )


def windows_icon_font(available_families: set[str]) -> str:
    return preferred_font_family(
        available_families,
        "Segoe Fluent Icons",
        "Segoe MDL2 Assets",
        "Segoe UI Symbol",
    )


SEARCH_GLYPH = "\ue721"
CLEAR_GLYPH = "\ue711"
