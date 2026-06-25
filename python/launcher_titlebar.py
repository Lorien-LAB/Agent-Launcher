from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

from launcher_theme import METRICS
from launcher_widgets import GhostButton
from launcher_windows_icons import caption_glyphs, windows_icon_font


class _CaptionButton(tk.Canvas):
    def __init__(
        self,
        master,
        *,
        glyph,
        command,
        accessible_name,
        theme,
        scale,
        font_family,
        danger=False,
    ):
        self.theme = theme
        self.s = scale
        self.command = command
        self.accessible_name = accessible_name
        self._glyph = glyph
        self._hovered = False
        self._pressed = False
        self._danger = bool(danger)
        super().__init__(
            master,
            width=self.s(42),
            height=self.s(METRICS.titlebar_height - 2),
            bg=theme["surface_0"],
            highlightthickness=0,
            bd=0,
            takefocus=1,
            cursor="hand2",
        )
        self._background = self.create_rectangle(
            0,
            0,
            self.s(42),
            self.s(METRICS.titlebar_height - 2),
            fill=theme["surface_0"],
            outline="",
        )
        self._label = self.create_text(
            self.s(21),
            self.s((METRICS.titlebar_height - 2) / 2),
            text=glyph,
            fill=theme["text_secondary"],
            font=(font_family, 10),
        )
        self.bind("<Configure>", self._configure_geometry)
        self.bind("<Enter>", lambda _event: self._set_hovered(True))
        self.bind("<Leave>", lambda _event: self._set_hovered(False))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Return>", lambda _event: self.invoke())
        self.bind("<space>", lambda _event: self.invoke())

    def _configure_geometry(self, event):
        width = max(1, int(event.width))
        height = max(1, int(event.height))
        self.coords(self._background, 0, 0, width, height)
        self.coords(self._label, width // 2, height // 2)

    def _set_hovered(self, hovered):
        self._hovered = bool(hovered)
        if not self._hovered:
            self._pressed = False
        self._render()

    def _press(self, _event):
        self.focus_set()
        self._pressed = True
        self._render()
        return "break"

    def _release(self, event):
        was_pressed = self._pressed
        inside = (
            0 <= int(event.x) <= int(self.winfo_width())
            and 0 <= int(event.y) <= int(self.winfo_height())
        )
        self._pressed = False
        self._render()
        if was_pressed and inside:
            self.invoke()
        return "break"

    def _render(self):
        if self._danger and self._hovered:
            background = self.theme["danger"]
            foreground = self.theme["text_primary"]
        elif self._pressed:
            background = self.theme["surface_selected"]
            foreground = self.theme["text_primary"]
        elif self._hovered:
            background = self.theme["surface_hover"]
            foreground = self.theme["text_primary"]
        else:
            background = self.theme["surface_0"]
            foreground = self.theme["text_secondary"]
        self.itemconfigure(self._background, fill=background)
        self.itemconfigure(self._label, fill=foreground, text=self._glyph)

    def set_glyph(self, glyph):
        self._glyph = glyph
        self._render()

    def invoke(self):
        return self.command()


class LauncherTitleBar(tk.Frame):
    """Custom chrome using the same caption glyphs as Windows system UI."""

    def __init__(
        self,
        master,
        *,
        theme: dict,
        scale,
        on_minimize,
        on_toggle_maximize,
        on_close,
        on_toggle_expanded,
        drag_controller,
    ):
        self.theme = theme
        self.s = scale
        self._on_toggle_maximize = on_toggle_maximize
        self._drag_controller = drag_controller
        self._glyphs = caption_glyphs()
        self._icon_family = windows_icon_font(set(tkfont.families(master)))
        super().__init__(
            master,
            bg=theme["surface_0"],
            height=self.s(METRICS.titlebar_height),
            highlightthickness=0,
            bd=0,
        )
        self.grid_propagate(False)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._brand = tk.Canvas(
            self,
            width=self.s(20),
            height=self.s(20),
            bg=theme["surface_0"],
            highlightthickness=0,
            bd=0,
        )
        center = self.s(10)
        outer = self.s(7)
        inner = self.s(3)
        self._brand.create_polygon(
            center,
            center - outer,
            center + outer,
            center,
            center,
            center + outer,
            center - outer,
            center,
            fill=theme["purple"],
            outline="",
        )
        self._brand.create_polygon(
            center,
            center - inner,
            center + inner,
            center,
            center,
            center + inner,
            center - inner,
            center,
            fill=theme["blue_light"],
            outline="",
        )
        self._brand.grid(
            row=0,
            column=0,
            padx=(self.s(10), self.s(7)),
        )

        self._title = tk.Label(
            self,
            text="Agent Launcher",
            bg=theme["surface_0"],
            fg=theme["text_primary"],
            font=("Segoe UI Semibold", 10),
            anchor="w",
        )
        self._title.grid(row=0, column=1, sticky="nsew")

        self.expand_button = GhostButton(
            self,
            text="Expand",
            command=on_toggle_expanded,
            theme=theme,
            scale=scale,
            width=70,
            height=28,
        )
        self.expand_button.grid(row=0, column=2, padx=(self.s(4), self.s(4)))

        self.minimize_button = _CaptionButton(
            self,
            glyph=self._glyphs.minimize,
            command=on_minimize,
            accessible_name="Minimize",
            theme=theme,
            scale=scale,
            font_family=self._icon_family,
        )
        self.minimize_button.grid(row=0, column=3, sticky="ns")

        self.maximize_button = _CaptionButton(
            self,
            glyph=self._glyphs.maximize,
            command=on_toggle_maximize,
            accessible_name="Maximize",
            theme=theme,
            scale=scale,
            font_family=self._icon_family,
        )
        self.maximize_button.grid(row=0, column=4, sticky="ns")

        self.close_button = _CaptionButton(
            self,
            glyph=self._glyphs.close,
            command=on_close,
            accessible_name="Close",
            theme=theme,
            scale=scale,
            font_family=self._icon_family,
            danger=True,
        )
        self.close_button.grid(row=0, column=5, sticky="ns")

        self.separator = tk.Frame(
            self,
            bg=theme["border"],
            height=self.s(1),
        )
        self.separator.place(relx=0, rely=1, relwidth=1, anchor="sw")

        for widget in (self, self._brand, self._title):
            widget.bind("<ButtonPress-1>", self._drag_controller.begin_drag)
            widget.bind("<B1-Motion>", self._drag_controller.drag)
            widget.bind("<ButtonRelease-1>", self._drag_controller.end_drag)
            widget.bind("<Double-Button-1>", self._toggle_maximize)

    def _toggle_maximize(self, _event=None):
        self._on_toggle_maximize()
        return "break"

    def set_expanded(self, expanded: bool):
        self.expand_button.set_text("Compact" if expanded else "Expand")

    def set_maximized(self, maximized: bool):
        self.maximize_button.set_glyph(
            self._glyphs.restore if maximized else self._glyphs.maximize
        )
