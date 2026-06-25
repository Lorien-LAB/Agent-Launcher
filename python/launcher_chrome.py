from __future__ import annotations

import ctypes
from dataclasses import dataclass
import sys
import tkinter as tk

from launcher_theme import METRICS
from launcher_widgets import rounded_rectangle_points


@dataclass(frozen=True)
class WindowBounds:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class DragAnchor:
    pointer_x: int
    pointer_y: int
    window_x: int
    window_y: int


class ChromeState:
    """Track maximized state and the bounds needed to restore a frameless window."""

    def __init__(self) -> None:
        self.maximized = False
        self.restore_bounds: WindowBounds | None = None

    def mark_maximized(self, restore_bounds: WindowBounds) -> None:
        self.restore_bounds = restore_bounds
        self.maximized = True

    def mark_restored(self) -> None:
        self.maximized = False


def calculate_drag_position(
    anchor: DragAnchor,
    pointer_x: int,
    pointer_y: int,
) -> tuple[int, int]:
    """Return a new top-left position while preserving the initial pointer offset."""
    return (
        anchor.window_x + int(pointer_x) - anchor.pointer_x,
        anchor.window_y + int(pointer_y) - anchor.pointer_y,
    )


def restore_for_drag(
    pointer_x: int,
    pointer_y: int,
    maximized: WindowBounds,
    restored: WindowBounds,
) -> WindowBounds:
    """Restore a maximized window under the pointer without a horizontal jump."""
    ratio = max(
        0.0,
        min(
            1.0,
            (int(pointer_x) - maximized.x) / max(1, maximized.width),
        ),
    )
    x = round(int(pointer_x) - restored.width * ratio)
    return WindowBounds(
        x=x,
        y=int(pointer_y),
        width=restored.width,
        height=restored.height,
    )


class WindowsChromePlatform:
    """Best-effort Win32/DWM integration with safe no-op fallbacks."""

    DWMWA_WINDOW_CORNER_PREFERENCE = 33
    DWMWCP_DEFAULT = 0
    DWMWCP_ROUND = 2
    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00040000
    SW_MINIMIZE = 6

    def resolve_toplevel(self, hwnd: int) -> int:
        if sys.platform != "win32":
            return int(hwnd)
        try:
            user32 = ctypes.windll.user32
            current = int(hwnd)
            for _ in range(8):
                parent = int(user32.GetParent(current) or 0)
                if not parent or parent == current:
                    break
                current = parent
            return current
        except (AttributeError, OSError, TypeError, ValueError):
            return int(hwnd)

    def apply_rounded_corners(self, hwnd: int, enabled: bool = True) -> bool:
        if sys.platform != "win32":
            return False
        preference = ctypes.c_int(
            self.DWMWCP_ROUND if enabled else self.DWMWCP_DEFAULT
        )
        try:
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(int(hwnd)),
                ctypes.c_uint(self.DWMWA_WINDOW_CORNER_PREFERENCE),
                ctypes.byref(preference),
                ctypes.sizeof(preference),
            )
        except (AttributeError, OSError):
            return False
        return result == 0

    def ensure_taskbar_presence(self, hwnd: int) -> bool:
        if sys.platform != "win32":
            return False
        try:
            user32 = ctypes.windll.user32
            get_style = getattr(
                user32,
                "GetWindowLongPtrW",
                user32.GetWindowLongW,
            )
            set_style = getattr(
                user32,
                "SetWindowLongPtrW",
                user32.SetWindowLongW,
            )
            style = int(get_style(int(hwnd), self.GWL_EXSTYLE))
            style = (style & ~self.WS_EX_TOOLWINDOW) | self.WS_EX_APPWINDOW
            set_style(int(hwnd), self.GWL_EXSTYLE, style)
        except (AttributeError, OSError, TypeError):
            return False
        return True

    def minimize_window(self, hwnd: int) -> bool:
        if sys.platform != "win32":
            return False
        try:
            ctypes.windll.user32.ShowWindow(
                int(hwnd),
                self.SW_MINIMIZE,
            )
        except (AttributeError, OSError, TypeError, ValueError):
            return False
        return True


class LauncherChromeController:
    """Apply frameless styling and own drag state without owning app shutdown."""

    def __init__(self, root, platform=None) -> None:
        self.root = root
        self.platform = platform or WindowsChromePlatform()
        self.state = ChromeState()
        self._drag_anchor: DragAnchor | None = None

    def _window_handle(self) -> int:
        hwnd = int(self.root.winfo_id())
        resolver = getattr(self.platform, "resolve_toplevel", None)
        return int(resolver(hwnd)) if resolver is not None else hwnd

    def apply_frameless(self) -> None:
        self.root.overrideredirect(True)
        try:
            self.root.update_idletasks()
        except Exception:
            pass
        try:
            hwnd = self._window_handle()
            ensure_taskbar = getattr(
                self.platform,
                "ensure_taskbar_presence",
                None,
            )
            if ensure_taskbar is not None:
                ensure_taskbar(hwnd)
            self.platform.apply_rounded_corners(hwnd, True)
        except Exception:
            pass

    def minimize_native(self) -> bool:
        try:
            hwnd = self._window_handle()
            minimize = getattr(self.platform, "minimize_window", None)
            return bool(minimize is not None and minimize(hwnd))
        except Exception:
            return False

    def reapply_after_restore(self) -> None:
        try:
            self.root.after_idle(self.apply_frameless)
        except Exception:
            self.apply_frameless()

    def current_bounds(self) -> WindowBounds:
        return WindowBounds(
            x=int(self.root.winfo_x()),
            y=int(self.root.winfo_y()),
            width=max(1, int(self.root.winfo_width())),
            height=max(1, int(self.root.winfo_height())),
        )

    def begin_drag(self, event) -> str:
        if self.state.maximized and self.state.restore_bounds is not None:
            maximized = self.current_bounds()
            restored = restore_for_drag(
                int(event.x_root),
                int(event.y_root),
                maximized,
                self.state.restore_bounds,
            )
            self.root.geometry(
                f"{restored.width}x{restored.height}+{restored.x}+{restored.y}"
            )
            self.state.mark_restored()
        self._drag_anchor = DragAnchor(
            pointer_x=int(event.x_root),
            pointer_y=int(event.y_root),
            window_x=int(self.root.winfo_x()),
            window_y=int(self.root.winfo_y()),
        )
        return "break"

    def drag(self, event) -> str:
        if self._drag_anchor is None:
            return "break"
        x, y = calculate_drag_position(
            self._drag_anchor,
            int(event.x_root),
            int(event.y_root),
        )
        bounds = self.current_bounds()
        self.root.geometry(f"{bounds.width}x{bounds.height}+{x}+{y}")
        return "break"

    def end_drag(self, _event=None) -> str:
        self._drag_anchor = None
        return "break"


class _ChromeButton(tk.Canvas):
    def __init__(
        self,
        master,
        *,
        text,
        command,
        accessible_name,
        theme,
        scale,
        width,
        danger=False,
        compact_font=False,
    ):
        self.theme = theme
        self.s = scale
        self.command = command
        self.accessible_name = accessible_name
        self._text = str(text)
        self._hovered = False
        self._pressed = False
        self._danger = bool(danger)
        super().__init__(
            master,
            width=self.s(width),
            height=self.s(28),
            bg=theme["surface_0"],
            highlightthickness=0,
            bd=0,
            takefocus=1,
            cursor="hand2",
        )
        self._shape = self.create_polygon(
            *rounded_rectangle_points(
                1,
                1,
                self.s(width) - 1,
                self.s(28) - 1,
                self.s(7),
            ),
            smooth=True,
            splinesteps=20,
            fill=theme["surface_0"],
            outline="",
        )
        font = (
            ("Segoe UI Semibold", 8)
            if compact_font
            else ("Segoe UI Symbol", 10)
        )
        self._label = self.create_text(
            self.s(width) // 2,
            self.s(14),
            text=self._text,
            fill=theme["text_secondary"],
            font=font,
        )
        self.bind("<Configure>", self._on_configure)
        self.bind("<Enter>", lambda _event: self._set_hovered(True))
        self.bind("<Leave>", lambda _event: self._set_hovered(False))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Return>", lambda _event: self.invoke())
        self.bind("<space>", lambda _event: self.invoke())

    def _on_configure(self, event):
        width = max(2, int(event.width))
        height = max(2, int(event.height))
        self.coords(
            self._shape,
            *rounded_rectangle_points(
                1,
                1,
                width - 1,
                height - 1,
                self.s(7),
            ),
        )
        self.coords(self._label, width // 2, height // 2)

    def _set_hovered(self, hovered):
        self._hovered = bool(hovered)
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
        elif self._pressed:
            background = self.theme["surface_selected"]
        elif self._hovered:
            background = self.theme["surface_hover"]
        else:
            background = self.theme["surface_0"]
        foreground = (
            self.theme["text_primary"]
            if self._hovered or self._pressed
            else self.theme["text_secondary"]
        )
        self.itemconfigure(self._shape, fill=background)
        self.itemconfigure(self._label, fill=foreground, text=self._text)

    def set_text(self, text):
        self._text = str(text)
        self._render()

    def invoke(self):
        return self.command()


class LauncherTitleBar(tk.Frame):
    """Compact custom title bar with stable geometry and native-style controls."""

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
        drag_controller: LauncherChromeController,
    ) -> None:
        self.theme = theme
        self.s = scale
        self._on_toggle_maximize = on_toggle_maximize
        self._drag_controller = drag_controller
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

        self.expand_button = _ChromeButton(
            self,
            text="Expand",
            command=on_toggle_expanded,
            accessible_name="Expand",
            theme=theme,
            scale=scale,
            width=66,
            compact_font=True,
        )
        self.expand_button.grid(row=0, column=2, padx=(self.s(4), self.s(2)))

        self.minimize_button = _ChromeButton(
            self,
            text="—",
            command=on_minimize,
            accessible_name="Minimize",
            theme=theme,
            scale=scale,
            width=34,
        )
        self.minimize_button.grid(row=0, column=3)

        self.maximize_button = _ChromeButton(
            self,
            text="□",
            command=on_toggle_maximize,
            accessible_name="Maximize",
            theme=theme,
            scale=scale,
            width=34,
        )
        self.maximize_button.grid(row=0, column=4)

        self.close_button = _ChromeButton(
            self,
            text="×",
            command=on_close,
            accessible_name="Close",
            theme=theme,
            scale=scale,
            width=34,
            danger=True,
        )
        self.close_button.grid(row=0, column=5, padx=(0, self.s(4)))

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

    def set_expanded(self, expanded: bool) -> None:
        self.expand_button.set_text("Compact" if expanded else "Expand")

    def set_maximized(self, maximized: bool) -> None:
        self.maximize_button.set_text("❐" if maximized else "□")
