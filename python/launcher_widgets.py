from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk

from launcher_theme import METRICS, interpolate_hex


@dataclass(frozen=True)
class WidgetVisualState:
    hovered: bool = False
    pressed: bool = False
    focused: bool = False
    enabled: bool = True


@dataclass(frozen=True)
class ResolvedButtonColors:
    background: str


def rounded_rectangle_points(x1, y1, x2, y2, radius):
    radius = max(0, min(int(radius), max(0, int((x2 - x1) // 2)), max(0, int((y2 - y1) // 2))))
    return [
        x1 + radius,
        y1,
        x2 - radius,
        y1,
        x2,
        y1,
        x2,
        y1 + radius,
        x2,
        y2 - radius,
        x2,
        y2,
        x2 - radius,
        y2,
        x1 + radius,
        y2,
        x1,
        y2,
        x1,
        y2 - radius,
        x1,
        y1 + radius,
        x1,
        y1,
    ]


def resolve_button_colors(state, *, normal, hover, pressed, disabled):
    if not state.enabled:
        return ResolvedButtonColors(disabled)
    if state.pressed:
        return ResolvedButtonColors(pressed)
    if state.hovered:
        return ResolvedButtonColors(hover)
    return ResolvedButtonColors(normal)


def scrollbar_should_show(first, last):
    return float(first) > 0.0 or float(last) < 1.0


class RoundedCard(tk.Canvas):
    def __init__(self, master, *, theme, scale, radius=12, padding=12, **kwargs):
        self.theme = theme
        self.s = scale
        self.radius = radius
        self.padding = padding
        self._hovered = False
        self._focused = False
        super().__init__(
            master,
            bg=theme["window_bg"],
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self._shape = self.create_polygon(
            rounded_rectangle_points(0, 0, 1, 1, self.s(radius)),
            smooth=True,
            splinesteps=24,
            fill=theme["surface_1"],
            outline=theme["border"],
            width=self.s(1),
        )
        self.content = tk.Frame(self, bg=theme["surface_1"])
        self._content_window = self.create_window(
            self.s(padding),
            self.s(padding),
            anchor="nw",
            window=self.content,
        )
        self.bind("<Configure>", self._on_configure)

    def _on_configure(self, event):
        width = max(1, int(event.width))
        height = max(1, int(event.height))
        self.coords(
            self._shape,
            *rounded_rectangle_points(
                self.s(1),
                self.s(1),
                width - self.s(1),
                height - self.s(1),
                self.s(self.radius),
            ),
        )
        inner_width = max(1, width - self.s(self.padding * 2))
        inner_height = max(1, height - self.s(self.padding * 2))
        self.itemconfigure(self._content_window, width=inner_width, height=inner_height)

    def set_interactive_state(self, *, hovered=False, focused=False):
        self._hovered = bool(hovered)
        self._focused = bool(focused)
        background = self.theme["surface_hover"] if self._hovered else self.theme["surface_1"]
        border = self.theme["border_focus"] if self._focused else (
            self.theme["border_hover"] if self._hovered else self.theme["border"]
        )
        self.itemconfigure(self._shape, fill=background, outline=border)
        self.content.configure(bg=background)


class ThemedButton(tk.Canvas):
    def __init__(
        self,
        master,
        *,
        text,
        command,
        theme,
        scale,
        kind="ghost",
        icon=None,
        width=120,
        height=32,
    ):
        self.theme = theme
        self.s = scale
        self.command = command
        self.kind = kind
        self.icon = icon
        self._text = str(text)
        self._state = WidgetVisualState()
        super().__init__(
            master,
            width=self.s(width),
            height=self.s(height),
            bg=master.cget("bg") if hasattr(master, "cget") else theme["window_bg"],
            highlightthickness=0,
            bd=0,
            takefocus=1,
            cursor="hand2",
        )
        self._shape = self.create_polygon(
            rounded_rectangle_points(1, 1, self.s(width) - 1, self.s(height) - 1, self.s(METRICS.button_radius)),
            smooth=True,
            splinesteps=24,
            width=self.s(1),
        )
        self._label = self.create_text(
            self.s(width) // 2,
            self.s(height) // 2,
            text=self._label_text(),
            font=("Segoe UI Semibold", 9),
        )
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

    def _label_text(self):
        return f"{self.icon}  {self._text}" if self.icon else self._text

    def _palette(self):
        if self.kind == "claude":
            return (
                self.theme["claude"],
                self.theme["claude_hover"],
                interpolate_hex(self.theme["claude"], "#000000", 0.18),
                self.theme["surface_0"],
                "#08110C",
            )
        if self.kind == "hermes":
            return (
                self.theme["hermes"],
                self.theme["hermes_hover"],
                interpolate_hex(self.theme["hermes"], "#000000", 0.18),
                self.theme["surface_0"],
                "#171008",
            )
        if self.kind == "accent":
            return (
                self.theme["purple"],
                self.theme["purple_light"],
                interpolate_hex(self.theme["purple"], "#000000", 0.18),
                self.theme["surface_0"],
                self.theme["text_primary"],
            )
        return (
            self.theme["surface_2"],
            self.theme["surface_hover"],
            self.theme["surface_selected"],
            self.theme["surface_0"],
            self.theme["text_secondary"],
        )

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
        inside = 0 <= int(event.x) <= int(self.winfo_width()) and 0 <= int(event.y) <= int(self.winfo_height())
        self._set_state(pressed=False)
        if was_pressed and inside:
            self.invoke()
        return "break"

    def _on_configure(self, event):
        width = max(2, int(event.width))
        height = max(2, int(event.height))
        self.coords(
            self._shape,
            *rounded_rectangle_points(1, 1, width - 1, height - 1, self.s(METRICS.button_radius)),
        )
        self.coords(self._label, width // 2, height // 2)

    def _render(self):
        normal, hover, pressed, disabled, text_color = self._palette()
        resolved = resolve_button_colors(
            self._state,
            normal=normal,
            hover=hover,
            pressed=pressed,
            disabled=disabled,
        )
        border = self.theme["border_focus"] if self._state.focused else (
            self.theme["border_hover"] if self._state.hovered else self.theme["border"]
        )
        if self.kind in {"claude", "hermes", "accent"} and not self._state.focused:
            border = resolved.background
        self.itemconfigure(self._shape, fill=resolved.background, outline=border)
        self.itemconfigure(
            self._label,
            fill=text_color if self._state.enabled else self.theme["text_disabled"],
            text=self._label_text(),
        )
        self.configure(cursor="hand2" if self._state.enabled else "arrow")

    def configure_state(self, enabled: bool):
        self._set_state(enabled=bool(enabled), pressed=False)

    def set_text(self, text: str):
        self._text = str(text)
        self._render()

    def invoke(self):
        if not self._state.enabled:
            return None
        return self.command()


class GhostButton(ThemedButton):
    def __init__(self, master, **kwargs):
        super().__init__(master, kind="ghost", **kwargs)


class PrimaryButton(ThemedButton):
    def __init__(self, master, *, role, **kwargs):
        if role not in {"claude", "hermes", "accent"}:
            raise ValueError(f"unknown primary button role: {role}")
        super().__init__(master, kind=role, **kwargs)


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
        self._focused = False
        self._hovered = False
        super().__init__(
            master,
            height=self.s(METRICS.search_height),
            bg=master.cget("bg") if hasattr(master, "cget") else theme["window_bg"],
            highlightthickness=0,
            bd=0,
        )
        self._shape = self.create_polygon(
            rounded_rectangle_points(1, 1, 100, self.s(METRICS.search_height) - 1, self.s(METRICS.input_radius)),
            smooth=True,
            splinesteps=24,
            fill=theme["surface_1"],
            outline=theme["border"],
            width=self.s(1),
        )
        self._search_icon = self.create_text(
            self.s(18),
            self.s(METRICS.search_height) // 2,
            text="⌕",
            fill=theme["text_muted"],
            font=("Segoe UI Symbol", 12),
        )
        self.entry = tk.Entry(
            self,
            textvariable=variable,
            relief="flat",
            bd=0,
            highlightthickness=0,
            bg=theme["surface_1"],
            fg=theme["text_primary"],
            insertbackground=theme["purple_light"],
            selectbackground=theme["surface_selected"],
            selectforeground=theme["text_primary"],
            font=("Segoe UI", 10),
        )
        self._entry_window = self.create_window(
            self.s(36),
            self.s(METRICS.search_height) // 2,
            anchor="w",
            window=self.entry,
        )
        self._placeholder = self.create_text(
            self.s(38),
            self.s(METRICS.search_height) // 2,
            anchor="w",
            text=placeholder,
            fill=theme["text_muted"],
            font=("Segoe UI", 10),
        )
        self._clear = self.create_text(
            1,
            self.s(METRICS.search_height) // 2,
            text="×",
            fill=theme["text_muted"],
            font=("Segoe UI Symbol", 11),
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
        self.variable.trace_add("write", self._value_changed)
        self._value_changed()

    def _on_configure(self, event):
        width = max(1, int(event.width))
        height = max(1, int(event.height))
        self.coords(
            self._shape,
            *rounded_rectangle_points(1, 1, width - 1, height - 1, self.s(METRICS.input_radius)),
        )
        entry_width = max(1, width - self.s(74))
        self.itemconfigure(self._entry_window, width=entry_width)
        self.coords(self._entry_window, self.s(36), height // 2)
        self.coords(self._search_icon, self.s(18), height // 2)
        self.coords(self._placeholder, self.s(38), height // 2)
        self.coords(self._clear, width - self.s(18), height // 2)

    def _submit(self, _event=None):
        if self.on_submit is not None:
            self.on_submit()
        return "break"

    def _value_changed(self, *_args):
        has_value = bool(self.variable.get())
        self.itemconfigure(self._placeholder, state="hidden" if has_value or self._focused else "normal")
        self.itemconfigure(self._clear, state="normal" if has_value else "hidden")

    def _set_hovered(self, hovered):
        self._hovered = bool(hovered)
        self._render_border()

    def _set_focused(self, focused):
        self._focused = bool(focused)
        self._value_changed()
        self._render_border()

    def _render_border(self):
        border = self.theme["border_focus"] if self._focused else (
            self.theme["border_hover"] if self._hovered else self.theme["border"]
        )
        self.itemconfigure(self._shape, outline=border)

    def focus(self):
        self.entry.focus_set()

    def clear(self):
        self.variable.set("")
        self.focus()


class SegmentedState:
    def __init__(self, values, selected):
        self.values = tuple(values)
        if not self.values or selected not in self.values:
            raise ValueError(selected)
        self.selected = selected

    def select(self, value):
        if value not in self.values:
            raise ValueError(value)
        self.selected = value
        return value


class ToggleState:
    def __init__(self, value, on_change):
        self.value = bool(value)
        self.on_change = on_change

    def set(self, value, *, emit=True):
        self.value = bool(value)
        if emit:
            self.on_change(self.value)

    def toggle(self):
        self.set(not self.value)


class SegmentedControl(tk.Canvas):
    def __init__(self, master, *, options, variable, command, theme, scale, height=32):
        self.options = tuple(options)
        self.variable = variable
        self.command = command
        self.theme = theme
        self.s = scale
        values = tuple(value for value, _text in self.options)
        self.state_model = SegmentedState(values, variable.get())
        super().__init__(
            master,
            height=self.s(height),
            bg=master.cget("bg") if hasattr(master, "cget") else theme["window_bg"],
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=1,
        )
        self.bind("<Configure>", lambda _event: self._render())
        self.bind("<Button-1>", self._clicked)
        self.variable.trace_add("write", lambda *_args: self._sync_from_variable())

    def _sync_from_variable(self):
        value = self.variable.get()
        if value in self.state_model.values:
            self.state_model.select(value)
            self._render()

    def _clicked(self, event):
        width = max(1, int(self.winfo_width()))
        index = min(len(self.options) - 1, max(0, int(event.x * len(self.options) / width)))
        self.set_value(self.options[index][0], emit=True)
        return "break"

    def set_value(self, value, *, emit=False):
        self.state_model.select(value)
        self.variable.set(value)
        self._render()
        if emit:
            self.command(value)

    def _render(self):
        self.delete("segment")
        width = max(1, int(self.winfo_width()))
        height = max(1, int(self.winfo_height()))
        segment_width = width / len(self.options)
        self.create_polygon(
            rounded_rectangle_points(1, 1, width - 1, height - 1, self.s(8)),
            smooth=True,
            splinesteps=24,
            fill=self.theme["surface_0"],
            outline=self.theme["border"],
            width=self.s(1),
            tags="segment",
        )
        selected = self.state_model.selected
        for index, (value, text) in enumerate(self.options):
            x1 = round(index * segment_width) + self.s(2)
            x2 = round((index + 1) * segment_width) - self.s(2)
            if value == selected:
                self.create_polygon(
                    rounded_rectangle_points(x1, self.s(3), x2, height - self.s(3), self.s(6)),
                    smooth=True,
                    splinesteps=20,
                    fill=self.theme["surface_selected"],
                    outline=self.theme["border_focus"],
                    width=self.s(1),
                    tags="segment",
                )
            self.create_text(
                (x1 + x2) // 2,
                height // 2,
                text=text,
                fill=self.theme["text_primary"] if value == selected else self.theme["text_secondary"],
                font=("Segoe UI Semibold" if value == selected else "Segoe UI", 8),
                tags="segment",
            )


class ToggleSwitch(tk.Canvas):
    def __init__(self, master, *, variable, command, theme, scale):
        self.variable = variable
        self.command = command
        self.theme = theme
        self.s = scale
        self.state_model = ToggleState(variable.get(), self._emit)
        super().__init__(
            master,
            width=self.s(34),
            height=self.s(20),
            bg=master.cget("bg") if hasattr(master, "cget") else theme["window_bg"],
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=1,
        )
        self.bind("<Button-1>", lambda _event: self._toggle())
        self.bind("<Return>", lambda _event: self._toggle())
        self.bind("<space>", lambda _event: self._toggle())
        self.bind("<Configure>", lambda _event: self._render())
        self.variable.trace_add("write", lambda *_args: self._sync_from_variable())
        self._render()

    def _emit(self, value):
        self.variable.set(value)
        self.command(value)

    def _sync_from_variable(self):
        self.state_model.set(self.variable.get(), emit=False)
        self._render()

    def _toggle(self):
        self.state_model.toggle()
        self._render()
        return "break"

    def set_value(self, value, *, emit=False):
        self.state_model.set(value, emit=emit)
        self.variable.set(bool(value))
        self._render()

    def _render(self):
        self.delete("all")
        width = max(1, int(self.winfo_width()))
        height = max(1, int(self.winfo_height()))
        enabled = self.state_model.value
        self.create_oval(1, 1, height - 1, height - 1, fill=self.theme["purple"] if enabled else self.theme["border_hover"], outline="")
        self.create_oval(width - height + 1, 1, width - 1, height - 1, fill=self.theme["purple"] if enabled else self.theme["border_hover"], outline="")
        self.create_rectangle(height // 2, 1, width - height // 2, height - 1, fill=self.theme["purple"] if enabled else self.theme["border_hover"], outline="")
        knob = height - self.s(6)
        knob_x = width - self.s(3) - knob if enabled else self.s(3)
        self.create_oval(knob_x, self.s(3), knob_x + knob, self.s(3) + knob, fill=self.theme["text_primary"], outline="")


class ThemedSlider(tk.Canvas):
    def __init__(self, master, *, variable, command, theme, scale, from_=0, to=100, width=180):
        self.variable = variable
        self.command = command
        self.theme = theme
        self.s = scale
        self.from_ = float(from_)
        self.to = float(to)
        self.enabled = True
        super().__init__(
            master,
            width=self.s(width),
            height=self.s(24),
            bg=master.cget("bg") if hasattr(master, "cget") else theme["window_bg"],
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.bind("<Configure>", lambda _event: self._render())
        self.bind("<Button-1>", self._user_set)
        self.bind("<B1-Motion>", self._user_set)
        self.variable.trace_add("write", lambda *_args: self._render())
        self._render()

    def _fraction(self):
        value = max(self.from_, min(self.to, float(self.variable.get())))
        return (value - self.from_) / max(1e-9, self.to - self.from_)

    def _user_set(self, event):
        if not self.enabled:
            return "break"
        width = max(1, int(self.winfo_width()) - self.s(12))
        fraction = max(0.0, min(1.0, (int(event.x) - self.s(6)) / width))
        value = self.from_ + (self.to - self.from_) * fraction
        self.variable.set(round(value))
        self.command(value)
        return "break"

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)
        self.configure(cursor="hand2" if self.enabled else "arrow")
        self._render()

    def _render(self):
        self.delete("all")
        width = max(1, int(self.winfo_width()))
        height = max(1, int(self.winfo_height()))
        left = self.s(6)
        right = width - self.s(6)
        center = height // 2
        fraction = self._fraction()
        knob_x = round(left + (right - left) * fraction)
        track = self.theme["border_hover"] if self.enabled else self.theme["surface_0"]
        fill = self.theme["purple"] if self.enabled else self.theme["text_disabled"]
        self.create_line(left, center, right, center, fill=track, width=self.s(4), capstyle="round")
        self.create_line(left, center, knob_x, center, fill=fill, width=self.s(4), capstyle="round")
        self.create_oval(
            knob_x - self.s(6),
            center - self.s(6),
            knob_x + self.s(6),
            center + self.s(6),
            fill=self.theme["purple_light"] if self.enabled else self.theme["text_disabled"],
            outline=self.theme["text_primary"] if self.enabled else self.theme["surface_0"],
            width=self.s(1),
        )


class OverlayScrollbar(tk.Canvas):
    def __init__(self, master, *, command, theme, scale, on_visibility_change=None):
        self.command = command
        self.theme = theme
        self.s = scale
        self.on_visibility_change = on_visibility_change
        self.first = 0.0
        self.last = 1.0
        self._visible = False
        self._drag_start_y = None
        self._drag_start_first = 0.0
        super().__init__(
            master,
            width=self.s(8),
            bg=master.cget("bg") if hasattr(master, "cget") else theme["window_bg"],
            highlightthickness=0,
            bd=0,
            cursor="arrow",
        )
        self._thumb = self.create_polygon(0, 0, 0, 0, fill=theme["border_hover"], outline="", state="hidden")
        self.bind("<Configure>", lambda _event: self._render())
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", lambda _event: self._release())

    def set(self, first, last):
        self.first = max(0.0, min(1.0, float(first)))
        self.last = max(self.first, min(1.0, float(last)))
        visible = scrollbar_should_show(self.first, self.last)
        changed = visible != self._visible
        self._visible = visible
        if changed and self.on_visibility_change is not None:
            self.on_visibility_change(visible)
        self._render()

    def visible(self):
        return self._visible

    def _thumb_bounds(self):
        height = max(1, int(self.winfo_height()))
        min_height = self.s(24)
        top = round(self.first * height)
        bottom = round(self.last * height)
        if bottom - top < min_height:
            bottom = min(height, top + min_height)
            top = max(0, bottom - min_height)
        return top, bottom

    def _render(self):
        if not self._visible:
            self.itemconfigure(self._thumb, state="hidden")
            return
        width = max(1, int(self.winfo_width()))
        top, bottom = self._thumb_bounds()
        self.coords(
            self._thumb,
            *rounded_rectangle_points(self.s(1), top, width - self.s(1), bottom, self.s(4)),
        )
        self.itemconfigure(self._thumb, state="normal")

    def _press(self, event):
        if not self._visible:
            return "break"
        top, bottom = self._thumb_bounds()
        if top <= int(event.y) <= bottom:
            self._drag_start_y = int(event.y)
            self._drag_start_first = self.first
        else:
            fraction = max(0.0, min(1.0, int(event.y) / max(1, int(self.winfo_height()))))
            self.command("moveto", fraction)
        return "break"

    def _drag(self, event):
        if self._drag_start_y is None:
            return "break"
        height = max(1, int(self.winfo_height()))
        page = max(1e-9, self.last - self.first)
        movable = max(1e-9, 1.0 - page)
        delta = (int(event.y) - self._drag_start_y) / height
        target = max(0.0, min(movable, self._drag_start_first + delta))
        self.command("moveto", target)
        return "break"

    def _release(self):
        self._drag_start_y = None
        return "break"
