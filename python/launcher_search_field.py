from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
import tkinter.font as tkfont

from launcher_geometry import stable_rounded_rectangle_points
from launcher_theme import METRICS
from launcher_windows_icons import CLEAR_GLYPH, SEARCH_GLYPH, windows_icon_font


@dataclass(frozen=True)
class SearchFieldMetrics:
    glyph: str
    font_size: int
    icon_x: int
    text_x: int
    clear_x_margin: int


def search_field_metrics() -> SearchFieldMetrics:
    return SearchFieldMetrics(
        glyph=SEARCH_GLYPH,
        font_size=17,
        icon_x=21,
        text_x=46,
        clear_x_margin=19,
    )


class SearchField(tk.Canvas):
    def __init__(
        self,
        master,
        *,
        variable,
        theme,
        scale,
        placeholder,
        on_submit=None,
    ):
        self.theme = theme
        self.s = scale
        self.variable = variable
        self.placeholder = placeholder
        self.on_submit = on_submit
        self.metrics = search_field_metrics()
        self._focused = False
        self._hovered = False
        family = windows_icon_font(set(tkfont.families(master)))
        self._icon_font = tkfont.Font(root=master, family=family, size=self.metrics.font_size)
        self._clear_font = tkfont.Font(root=master, family=family, size=12)
        super().__init__(
            master,
            height=self.s(METRICS.search_height),
            bg=self._master_bg(master),
            highlightthickness=0,
            bd=0,
        )
        self._shadow = self.create_polygon(
            *stable_rounded_rectangle_points(2, 3, 100, self.s(METRICS.search_height) - 1, self.s(METRICS.input_radius)),
            smooth=True,
            splinesteps=24,
            fill=theme["glass_shadow"],
            outline="",
        )
        self._shape = self.create_polygon(
            *stable_rounded_rectangle_points(1, 1, 100, self.s(METRICS.search_height) - 3, self.s(METRICS.input_radius)),
            smooth=True,
            splinesteps=24,
            fill=theme["glass_fill"],
            outline=theme["glass_border"],
            width=self.s(1),
        )
        self._inner_rim = self.create_polygon(
            *stable_rounded_rectangle_points(4, 4, 96, self.s(METRICS.search_height) - 6, max(1, self.s(METRICS.input_radius - 4))),
            smooth=True,
            splinesteps=24,
            fill="",
            outline=theme["glass_highlight"],
            width=self.s(1),
        )
        self._top_sheen = self.create_line(
            self.s(18),
            self.s(4),
            self.s(70),
            self.s(4),
            fill=theme["glass_highlight"],
            width=self.s(1),
            capstyle=tk.ROUND,
        )
        self._search_icon = self.create_text(
            self.s(self.metrics.icon_x),
            self.s(METRICS.search_height) // 2,
            text=self.metrics.glyph,
            fill=theme["text_secondary"],
            font=self._icon_font,
        )
        self.entry = tk.Entry(
            self,
            textvariable=variable,
            relief="flat",
            bd=0,
            highlightthickness=0,
            bg=theme["glass_content"],
            fg=theme["text_primary"],
            insertbackground=theme["purple_light"],
            selectbackground=theme["surface_selected"],
            selectforeground=theme["text_primary"],
            font=("Segoe UI", 10),
        )
        self._entry_window = self.create_window(
            self.s(self.metrics.text_x),
            self.s(METRICS.search_height) // 2,
            anchor="w",
            window=self.entry,
        )
        self._placeholder = self.create_text(
            self.s(self.metrics.text_x + 2),
            self.s(METRICS.search_height) // 2,
            anchor="w",
            text=placeholder,
            fill=theme["text_muted"],
            font=("Segoe UI", 10),
        )
        self._clear = self.create_text(
            1,
            self.s(METRICS.search_height) // 2,
            text=CLEAR_GLYPH,
            fill=theme["text_muted"],
            font=self._clear_font,
            state="hidden",
            tags=("clear",),
        )
        self.bind("<Configure>", self._on_configure)
        self.bind("<Enter>", lambda _event: self._set_hovered(True))
        self.bind("<Leave>", lambda _event: self._set_hovered(False))
        self.entry.bind("<FocusIn>", lambda _event: self._set_focused(True))
        self.entry.bind("<FocusOut>", lambda _event: self._set_focused(False))
        self.entry.bind("<Return>", self._submit)
        self.tag_bind("clear", "<Button-1>", lambda _event: self.clear())
        self._trace_id = self.variable.trace_add("write", self._value_changed)
        self._value_changed()

    def _master_bg(self, master):
        try:
            return master.cget("bg")
        except (AttributeError, tk.TclError):
            return self.theme["window_bg"]

    def _on_configure(self, event):
        width = max(4, int(event.width))
        height = max(8, int(event.height))
        radius = min(self.s(METRICS.input_radius), height // 2 - 1)
        self.coords(
            self._shadow,
            *stable_rounded_rectangle_points(2, 3, width - 2, height - 1, radius),
        )
        self.coords(
            self._shape,
            *stable_rounded_rectangle_points(1, 1, width - 1, height - 3, radius),
        )
        self.coords(
            self._inner_rim,
            *stable_rounded_rectangle_points(4, 4, width - 4, height - 6, max(1, radius - self.s(4))),
        )
        self.coords(
            self._top_sheen,
            self.s(18),
            self.s(4),
            max(self.s(18), width - self.s(30)),
            self.s(4),
        )
        entry_x = self.s(self.metrics.text_x)
        clear_margin = self.s(self.metrics.clear_x_margin)
        self.itemconfigure(
            self._entry_window,
            width=max(1, width - entry_x - self.s(34)),
        )
        self.coords(self._entry_window, entry_x, height // 2)
        self.coords(self._search_icon, self.s(self.metrics.icon_x), height // 2)
        self.coords(self._placeholder, self.s(self.metrics.text_x + 2), height // 2)
        self.coords(self._clear, width - clear_margin, height // 2)

    def _submit(self, _event=None):
        if self.on_submit is not None:
            self.on_submit()
        return "break"

    def _value_changed(self, *_args):
        has_value = bool(self.variable.get())
        self.itemconfigure(
            self._placeholder,
            state="hidden" if has_value or self._focused else "normal",
        )
        self.itemconfigure(self._clear, state="normal" if has_value else "hidden")

    def _set_hovered(self, hovered):
        self._hovered = bool(hovered)
        self._render_border()

    def _set_focused(self, focused):
        self._focused = bool(focused)
        self._value_changed()
        self._render_border()

    def _render_border(self):
        border = (
            self.theme["border_focus"]
            if self._focused
            else self.theme["border_hover"]
            if self._hovered
            else self.theme["glass_border"]
        )
        fill = (
            self.theme["glass_fill_hover"]
            if self._focused or self._hovered
            else self.theme["glass_fill"]
        )
        self.itemconfigure(self._shape, outline=border, fill=fill)
        self.itemconfigure(
            self._search_icon,
            fill=self.theme["purple_light"] if self._focused else self.theme["text_secondary"],
        )

    def focus(self):
        self.entry.focus_set()

    def clear(self):
        self.variable.set("")
        self.focus()

    def destroy(self):
        try:
            self.variable.trace_remove("write", self._trace_id)
        except (tk.TclError, AttributeError):
            pass
        super().destroy()
