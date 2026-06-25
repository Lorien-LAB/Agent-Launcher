from __future__ import annotations

from dataclasses import dataclass
import os
import tkinter as tk
import tkinter.font as tkfont

from launcher_theme import COLORS, METRICS
from launcher_view_models import truncate_middle
from launcher_widgets import rounded_rectangle_points


@dataclass(frozen=True)
class DirectoryRowPresentation:
    name: str
    path_text: str
    unavailable: bool


def build_row_presentation(
    path: str,
    available: bool,
    path_limit: int,
) -> DirectoryRowPresentation:
    name = os.path.basename(path.rstrip("\\/")) or path
    path_text = truncate_middle(path, path_limit)
    if not available:
        path_text = f"{path_text} · Unavailable"
    return DirectoryRowPresentation(name, path_text, not available)


def _middle_elide(value: str, limit: int) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    if limit <= 1:
        return "…"[:limit]
    content = limit - 1
    head = (content + 1) // 2
    tail = content - head
    return f"{text[:head]}…{text[-tail:]}" if tail else f"{text[:head]}…"


def fit_text_to_width(value: str, max_width: int, measure) -> str:
    """Middle-elide text until the rendered width fits the reserved area."""
    text = str(value)
    available = max(0, int(max_width))
    if measure(text) <= available:
        return text
    ellipsis = "…"
    if available <= 0 or measure(ellipsis) > available:
        return ""

    low = 1
    high = max(1, len(text))
    best = ellipsis
    while low <= high:
        keep = (low + high) // 2
        candidate = _middle_elide(text, keep)
        if measure(candidate) <= available:
            best = candidate
            low = keep + 1
        else:
            high = keep - 1
    return best


def _resolved_theme(theme=None, colors=None):
    provided = theme if theme is not None else colors or {}
    resolved = dict(COLORS)
    legacy = {
        "card": "surface_1",
        "selected": "surface_selected",
        "text": "text_primary",
        "sub": "text_secondary",
        "muted": "text_muted",
        "accent": "purple",
        "border": "border",
    }
    for key, value in provided.items():
        if key in resolved:
            resolved[key] = value
    for old, new in legacy.items():
        if old in provided and new not in provided:
            resolved[new] = provided[old]
    return resolved


class DirectoryRowWidget(tk.Canvas):
    def __init__(
        self,
        master,
        row,
        colors=None,
        on_select=None,
        on_launch=None,
        on_favorite=None,
        *,
        theme=None,
        scale=lambda value: value,
        is_available=os.path.isdir,
    ):
        self.row = row
        self.theme = _resolved_theme(theme, colors)
        self.s = scale
        self.on_select = on_select or (lambda _path: None)
        self.on_launch = on_launch or (lambda _agent: None)
        self.on_favorite = on_favorite or (lambda _path: None)
        self.available = bool(is_available(row.path))
        self.selected = False
        self.hovered = False
        self.favorite = bool(row.favorite)
        self.presentation = build_row_presentation(
            row.path,
            self.available,
            path_limit=72,
        )
        self._name_font = tkfont.Font(
            family="Segoe UI Semibold",
            size=9,
        )
        self._path_font = tkfont.Font(
            family="Cascadia Code",
            size=8,
        )
        self._symbol_font = tkfont.Font(
            family="Segoe UI Symbol",
            size=10,
        )
        super().__init__(
            master,
            height=self.s(METRICS.directory_row_height),
            bg=self.theme["surface_1"],
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=1,
        )
        self._build_items()
        self.bind("<Configure>", self._redraw)
        self.bind("<Enter>", lambda _event: self.set_hovered(True))
        self.bind("<Leave>", lambda _event: self.set_hovered(False))
        self.bind("<Button-1>", self._select)
        self.bind("<Double-Button-1>", self._launch)
        self.bind("<Return>", self._launch)
        self.bind("<space>", self._select)
        self.tag_bind("favorite", "<Button-1>", self._toggle_favorite)
        self.tag_bind(
            "favorite",
            "<Enter>",
            lambda _event: self.configure(cursor="hand2"),
        )
        self._redraw()

    def _build_items(self):
        self._background = self.create_polygon(
            *rounded_rectangle_points(1, 1, 2, 2, 1),
            smooth=True,
            splinesteps=20,
            fill=self.theme["surface_1"],
            outline="",
        )
        self._selected_bar = self.create_rectangle(
            0,
            0,
            0,
            0,
            fill=self.theme["purple"],
            outline="",
            state="hidden",
        )
        self._folder = self.create_polygon(
            0,
            0,
            0,
            0,
            fill=self.theme["blue_light"],
            outline="",
        )
        self._name = self.create_text(
            0,
            0,
            text=self.presentation.name,
            fill=self.theme["text_primary"],
            font=self._name_font,
            anchor="w",
        )
        self._path = self.create_text(
            0,
            0,
            text=self.presentation.path_text,
            fill=self.theme["text_muted"],
            font=self._path_font,
            anchor="w",
        )
        self._star_hit = self.create_oval(
            0,
            0,
            0,
            0,
            fill="",
            outline="",
            tags=("favorite",),
        )
        self._star = self.create_text(
            0,
            0,
            text="★" if self.favorite else "☆",
            fill=(
                self.theme["favorite"]
                if self.favorite
                else self.theme["text_muted"]
            ),
            font=self._symbol_font,
            tags=("favorite",),
        )

    def _redraw(self, _event=None):
        width = max(self.s(120), int(self.winfo_width()))
        height = max(
            self.s(METRICS.directory_row_height),
            int(self.winfo_height()),
        )
        self.coords(
            self._background,
            *rounded_rectangle_points(
                1,
                1,
                width - 1,
                height - 1,
                self.s(METRICS.row_radius),
            ),
        )
        self.coords(
            self._selected_bar,
            1,
            self.s(6),
            self.s(METRICS.selected_bar_width) + 1,
            height - self.s(6),
        )
        icon_x = self.s(13)
        icon_y = height // 2 - self.s(6)
        icon_w = self.s(16)
        icon_h = self.s(12)
        self.coords(
            self._folder,
            icon_x,
            icon_y + self.s(3),
            icon_x + self.s(5),
            icon_y + self.s(3),
            icon_x + self.s(7),
            icon_y,
            icon_x + icon_w,
            icon_y,
            icon_x + icon_w,
            icon_y + icon_h,
            icon_x,
            icon_y + icon_h,
        )

        text_x = self.s(38)
        star_x = width - self.s(20)
        favorite_radius = self.s(14)
        text_width = max(
            self.s(24),
            star_x - text_x - self.s(22),
        )
        display_name = fit_text_to_width(
            self.presentation.name,
            text_width,
            self._name_font.measure,
        )
        display_path = fit_text_to_width(
            self.presentation.path_text,
            text_width,
            self._path_font.measure,
        )
        self.itemconfigure(self._name, text=display_name)
        self.itemconfigure(self._path, text=display_path)
        self.coords(self._name, text_x, self.s(14))
        self.coords(self._path, text_x, self.s(30))
        self.coords(
            self._star_hit,
            star_x - favorite_radius,
            height // 2 - favorite_radius,
            star_x + favorite_radius,
            height // 2 + favorite_radius,
        )
        self.coords(self._star, star_x, height // 2)
        self._render_state()

    def _render_state(self):
        if self.selected:
            background = self.theme["surface_selected"]
        elif self.hovered:
            background = self.theme["surface_hover"]
        else:
            background = self.theme["surface_1"]
        self.itemconfigure(self._background, fill=background)
        self.itemconfigure(
            self._selected_bar,
            state="normal" if self.selected else "hidden",
        )
        self.itemconfigure(
            self._name,
            fill=(
                self.theme["text_disabled"]
                if self.presentation.unavailable
                else self.theme["text_primary"]
            ),
        )
        self.itemconfigure(
            self._path,
            fill=(
                self.theme["text_secondary"]
                if self.selected and not self.presentation.unavailable
                else self.theme["text_muted"]
            ),
        )
        self.itemconfigure(
            self._star,
            text="★" if self.favorite else "☆",
            fill=(
                self.theme["favorite"]
                if self.favorite or self.hovered
                else self.theme["text_muted"]
            ),
        )

    def _select(self, _event=None):
        self.focus_set()
        self.on_select(self.row.path)
        return "break"

    def _launch(self, _event=None):
        if self.presentation.unavailable:
            return "break"
        self.on_select(self.row.path)
        self.on_launch("claude")
        return "break"

    def _toggle_favorite(self, _event=None):
        self.on_favorite(self.row.path)
        return "break"

    def set_selected(self, selected: bool) -> None:
        self.selected = bool(selected)
        self._render_state()

    def set_hovered(self, hovered: bool) -> None:
        self.hovered = bool(hovered)
        self._render_state()

    def set_favorite(self, favorite: bool) -> None:
        self.favorite = bool(favorite)
        self._render_state()
