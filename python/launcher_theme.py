from __future__ import annotations

from dataclasses import dataclass


COLORS = {
    "window_bg": "#090B12",
    "surface_0": "#0B0E17",
    "surface_1": "#111522",
    "surface_2": "#161B2A",
    "surface_hover": "#1B2233",
    "surface_selected": "#202844",
    "border": "#202638",
    "border_hover": "#323B56",
    "border_focus": "#7567F8",
    "text_primary": "#F5F7FB",
    "text_secondary": "#B4BAC9",
    "text_muted": "#7E879D",
    "text_disabled": "#50586B",
    "purple": "#8367F4",
    "purple_light": "#A58BFA",
    "blue": "#527EF5",
    "blue_light": "#72A0F7",
    "claude": "#D97757",
    "claude_hover": "#E58969",
    "hermes": "#D9A441",
    "hermes_hover": "#E9B95A",
    "favorite": "#F2C45F",
    "danger": "#F05B68",
    "success": "#4BD681",
    "warning": "#F0BB5A",
}


@dataclass(frozen=True)
class ThemeMetrics:
    outer_padding: int = 12
    card_gap: int = 10
    card_padding: int = 12
    titlebar_height: int = 38
    search_height: int = 40
    directory_row_height: int = 44
    primary_button_height: int = 40
    secondary_button_height: int = 32
    card_radius: int = 12
    button_radius: int = 8
    input_radius: int = 10
    row_radius: int = 8
    border_width: int = 1
    selected_bar_width: int = 2


METRICS = ThemeMetrics()
COMPACT_LOGICAL_SIZE = (380, 420)
EXPANDED_LOGICAL_SIZE = (820, 560)


def scaled(value: int | float, dpi_scale: float) -> int:
    """Scale a logical pixel value while keeping visible dimensions non-zero."""
    return max(1, int(round(float(value) * float(dpi_scale))))


def compact_size(dpi_scale: float) -> tuple[int, int]:
    return tuple(scaled(value, dpi_scale) for value in COMPACT_LOGICAL_SIZE)


def expanded_size(dpi_scale: float) -> tuple[int, int]:
    return tuple(scaled(value, dpi_scale) for value in EXPANDED_LOGICAL_SIZE)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    stripped = value.lstrip("#")
    if len(stripped) != 6:
        raise ValueError(f"expected #RRGGBB color, got {value!r}")
    try:
        return tuple(int(stripped[index : index + 2], 16) for index in (0, 2, 4))
    except ValueError as exc:
        raise ValueError(f"expected #RRGGBB color, got {value!r}") from exc


def interpolate_hex(start: str, end: str, progress: float) -> str:
    """Linearly blend two RGB colors, clamping progress to the 0..1 range."""
    t = max(0.0, min(1.0, float(progress)))
    start_rgb = _hex_to_rgb(start)
    end_rgb = _hex_to_rgb(end)
    channels = [round(a + (b - a) * t) for a, b in zip(start_rgb, end_rgb)]
    return "#" + "".join(f"{channel:02X}" for channel in channels)


def preferred_font_family(available_families: set[str], *candidates: str) -> str:
    """Choose the first installed font and provide a deterministic fallback."""
    normalized = {family.casefold(): family for family in available_families}
    for candidate in candidates:
        installed = normalized.get(candidate.casefold())
        if installed:
            return installed
    return candidates[-1] if candidates else "Segoe UI"
