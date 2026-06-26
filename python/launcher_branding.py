from __future__ import annotations

from dataclasses import dataclass
import math
import tkinter as tk
import tkinter.font as tkfont

from launcher_theme import interpolate_hex
from launcher_widgets import WidgetVisualState, resolve_button_colors, rounded_rectangle_points


@dataclass(frozen=True)
class BrandVisualSpec:
    role: str
    icon_kind: str
    radius: int
    icon_width: int


@dataclass(frozen=True)
class GlassPalette:
    normal: str
    hover: str
    pressed: str
    disabled: str
    border: str
    highlight: str
    text: str
    icon: str
    shadow: str


def brand_visual_spec(role: str) -> BrandVisualSpec:
    if role == "claude":
        return BrandVisualSpec("claude", "claude_burst", 18, 24)
    if role == "hermes":
        return BrandVisualSpec("hermes", "nous_wordmark", 18, 34)
    raise ValueError(f"unknown brand button role: {role}")


def glass_palette(theme: dict, role: str) -> GlassPalette:
    spec = brand_visual_spec(role)
    accent = theme[spec.role]
    base = theme["surface_1"]
    return GlassPalette(
        normal=interpolate_hex(base, accent, 0.18),
        hover=interpolate_hex(base, accent, 0.28),
        pressed=interpolate_hex(base, accent, 0.38),
        disabled=theme["surface_0"],
        border=interpolate_hex(accent, theme["text_primary"], 0.18),
        highlight=interpolate_hex(base, theme["text_primary"], 0.12),
        text=theme["text_primary"],
        icon="#FFF5EC" if role == "claude" else "#FFF7E8",
        shadow=interpolate_hex(theme["window_bg"], "#000000", 0.42),
    )


class GlassBrandButton(tk.Canvas):
    """Glass-tinted brand button with vector Claude and Nous/Hermes marks."""

    def __init__(
        self,
        master,
        *,
        role: str,
        text: str,
        command,
        theme: dict,
        scale,
        width=145,
        height=36,
    ):
        self.theme = theme
        self.s = scale
        self.command = command
        self.role = role
        self.text = str(text)
        self.spec = brand_visual_spec(role)
        self.palette = glass_palette(theme, role)
        self._state = WidgetVisualState()
        self._label_font = tkfont.Font(family="Segoe UI Semibold", size=9)
        self._wordmark_font = tkfont.Font(family="Segoe UI Black", size=7)
        super().__init__(
            master,
            width=self.s(width),
            height=self.s(height),
            bg=self._master_bg(master),
            highlightthickness=0,
            bd=0,
            takefocus=1,
            cursor="hand2",
        )
        initial_width = self.s(width)
        initial_height = self.s(height)
        self._shadow = self.create_polygon(
            *rounded_rectangle_points(
                1,
                3,
                initial_width - 1,
                initial_height - 1,
                self.s(self.spec.radius),
            ),
            smooth=True,
            splinesteps=24,
            fill=self.palette.shadow,
            outline="",
        )
        self._shape = self.create_polygon(
            *rounded_rectangle_points(
                1,
                1,
                initial_width - 1,
                initial_height - 3,
                self.s(self.spec.radius),
            ),
            smooth=True,
            splinesteps=24,
            fill=self.palette.normal,
            outline=self.palette.border,
            width=self.s(1),
        )
        self._highlight = self.create_line(
            self.s(14),
            self.s(3),
            initial_width - self.s(14),
            self.s(3),
            fill=self.palette.highlight,
            width=self.s(1),
            capstyle=tk.ROUND,
        )
        self._label = self.create_text(
            initial_width // 2,
            initial_height // 2,
            text=self.text,
            fill=self.palette.text,
            font=self._label_font,
            anchor="w",
        )
        self._brand_items = self._create_brand_items()

        self.bind("<Configure>", self._on_configure)
        self.bind("<Enter>", lambda _event: self._set_state(hovered=True))
        self.bind("<Leave>", lambda _event: self._set_state(hovered=False, pressed=False))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<FocusIn>", lambda _event: self._set_state(focused=True))
        self.bind("<FocusOut>", lambda _event: self._set_state(focused=False, pressed=False))
        self.bind("<Return>", lambda _event: self.invoke())
        self.bind("<space>", lambda _event: self.invoke())
        self._render()

    def _master_bg(self, master):
        try:
            return master.cget("bg")
        except (AttributeError, tk.TclError):
            return self.theme["window_bg"]

    def _create_brand_items(self):
        if self.spec.icon_kind == "claude_burst":
            return [
                self.create_line(
                    0,
                    0,
                    0,
                    0,
                    fill=self.palette.icon,
                    width=self.s(2),
                    capstyle=tk.ROUND,
                )
                for _ in range(12)
            ]
        return [
            self.create_text(
                0,
                0,
                text="NOUS",
                fill=self.palette.icon,
                font=self._wordmark_font,
                anchor="center",
            )
        ]

    def _set_state(self, **changes):
        values = {
            "hovered": self._state.hovered,
            "pressed": self._state.pressed,
            "focused": self._state.focused,
            "enabled": self._state.enabled,
        }
        values.update(changes)
        self._state = WidgetVisualState(**values)
        self._render()

    def _press(self, _event):
        if not self._state.enabled:
            return "break"
        self.focus_set()
        self._set_state(pressed=True)
        return "break"

    def _release(self, event):
        was_pressed = self._state.pressed
        inside = (
            0 <= int(event.x) <= int(self.winfo_width())
            and 0 <= int(event.y) <= int(self.winfo_height())
        )
        self._set_state(pressed=False)
        if was_pressed and inside:
            self.invoke()
        return "break"

    def _on_configure(self, event):
        width = max(2, int(event.width))
        height = max(2, int(event.height))
        radius = min(self.s(self.spec.radius), max(1, height // 2 - 1))
        self.coords(
            self._shadow,
            *rounded_rectangle_points(
                1,
                self.s(3),
                width - 1,
                height - 1,
                radius,
            ),
        )
        self.coords(
            self._shape,
            *rounded_rectangle_points(
                1,
                1,
                width - 1,
                height - self.s(3),
                radius,
            ),
        )
        self.coords(
            self._highlight,
            self.s(14),
            self.s(3),
            width - self.s(14),
            self.s(3),
        )

        label_width = self._label_font.measure(self.text)
        icon_width = self.s(self.spec.icon_width)
        gap = self.s(8)
        group_width = icon_width + gap + label_width
        start_x = max(self.s(10), (width - group_width) // 2)
        icon_center_x = start_x + icon_width // 2
        center_y = max(1, (height - self.s(2)) // 2)
        self.coords(self._label, start_x + icon_width + gap, center_y)
        self._position_brand(icon_center_x, center_y)

    def _position_brand(self, center_x: int, center_y: int):
        if self.spec.icon_kind == "claude_burst":
            lengths = (9, 7, 10, 8, 9, 6, 10, 7, 9, 8, 10, 7)
            inner = self.s(2)
            for index, (item, length) in enumerate(zip(self._brand_items, lengths)):
                angle = math.radians(index * 30 - 90)
                x1 = center_x + math.cos(angle) * inner
                y1 = center_y + math.sin(angle) * inner
                outer = self.s(length)
                x2 = center_x + math.cos(angle) * outer
                y2 = center_y + math.sin(angle) * outer
                self.coords(item, x1, y1, x2, y2)
            return
        self.coords(self._brand_items[0], center_x, center_y)

    def _render(self):
        resolved = resolve_button_colors(
            self._state,
            normal=self.palette.normal,
            hover=self.palette.hover,
            pressed=self.palette.pressed,
            disabled=self.palette.disabled,
        )
        border = (
            self.theme["border_focus"]
            if self._state.focused
            else self.palette.border
        )
        text = self.palette.text if self._state.enabled else self.theme["text_disabled"]
        icon = self.palette.icon if self._state.enabled else self.theme["text_disabled"]
        self.itemconfigure(self._shape, fill=resolved.background, outline=border)
        self.itemconfigure(self._label, fill=text)
        for item in self._brand_items:
            self.itemconfigure(item, fill=icon)
        self.configure(cursor="hand2" if self._state.enabled else "arrow")

    def configure_state(self, enabled: bool):
        self._set_state(enabled=bool(enabled), pressed=False)

    def invoke(self):
        if not self._state.enabled:
            return None
        return self.command()
