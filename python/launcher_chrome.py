from __future__ import annotations

import ctypes
from dataclasses import dataclass
import sys
import tkinter as tk


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

    def apply_rounded_corners(self, hwnd: int, enabled: bool = True) -> bool:
        if sys.platform != "win32":
            return False
        preference = ctypes.c_int(self.DWMWCP_ROUND if enabled else self.DWMWCP_DEFAULT)
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
            get_style = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
            set_style = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
            style = int(get_style(int(hwnd), self.GWL_EXSTYLE))
            style = (style & ~self.WS_EX_TOOLWINDOW) | self.WS_EX_APPWINDOW
            set_style(int(hwnd), self.GWL_EXSTYLE, style)
        except (AttributeError, OSError, TypeError):
            return False
        return True


class LauncherChromeController:
    """Apply frameless styling and own drag state without owning app shutdown."""

    def __init__(self, root, platform=None) -> None:
        self.root = root
        self.platform = platform or WindowsChromePlatform()
        self.state = ChromeState()
        self._drag_anchor: DragAnchor | None = None

    def apply_frameless(self) -> None:
        self.root.overrideredirect(True)
        try:
            self.root.update_idletasks()
        except Exception:
            pass
        try:
            hwnd = int(self.root.winfo_id())
            ensure_taskbar = getattr(self.platform, "ensure_taskbar_presence", None)
            if ensure_taskbar is not None:
                ensure_taskbar(hwnd)
            self.platform.apply_rounded_corners(hwnd, True)
        except Exception:
            # Visual integration must never prevent the Launcher from starting.
            pass

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


class LauncherTitleBar(tk.Frame):
    """Minimal custom title bar. Window lifecycle callbacks stay outside this widget."""

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
            height=self.s(38),
            highlightthickness=0,
            bd=0,
        )
        self.pack_propagate(False)
        self.grid_columnconfigure(1, weight=1)

        self._brand = tk.Label(
            self,
            text="◆",
            bg=theme["surface_0"],
            fg=theme["purple_light"],
            font=("Segoe UI Symbol", 11, "bold"),
            padx=self.s(10),
        )
        self._brand.grid(row=0, column=0, sticky="ns")
        self._title = tk.Label(
            self,
            text="Agent Launcher",
            bg=theme["surface_0"],
            fg=theme["text_primary"],
            font=("Segoe UI Semibold", 10),
            anchor="w",
        )
        self._title.grid(row=0, column=1, sticky="nsew")

        self.expand_button = self._make_button("↗", on_toggle_expanded, "Expand")
        self.expand_button.grid(row=0, column=2, sticky="ns")
        self.minimize_button = self._make_button("—", on_minimize, "Minimize")
        self.minimize_button.grid(row=0, column=3, sticky="ns")
        self.maximize_button = self._make_button("□", on_toggle_maximize, "Maximize")
        self.maximize_button.grid(row=0, column=4, sticky="ns")
        self.close_button = self._make_button("×", on_close, "Close", danger=True)
        self.close_button.grid(row=0, column=5, sticky="ns")

        self.separator = tk.Frame(self, bg=theme["border"], height=self.s(1))
        self.separator.place(relx=0, rely=1, relwidth=1, anchor="sw")

        for widget in (self, self._brand, self._title):
            widget.bind("<ButtonPress-1>", self._drag_controller.begin_drag)
            widget.bind("<B1-Motion>", self._drag_controller.drag)
            widget.bind("<ButtonRelease-1>", self._drag_controller.end_drag)
            widget.bind("<Double-Button-1>", self._toggle_maximize)

    def _toggle_maximize(self, _event=None):
        self._on_toggle_maximize()
        return "break"

    def _make_button(self, text, command, accessible_name, danger=False):
        normal = self.theme["surface_0"]
        hover = self.theme["danger"] if danger else self.theme["surface_hover"]
        label = tk.Label(
            self,
            text=text,
            bg=normal,
            fg=self.theme["text_secondary"],
            width=3,
            cursor="hand2",
            font=("Segoe UI Symbol", 11),
            takefocus=True,
        )
        label.accessible_name = accessible_name
        label.bind("<Enter>", lambda _event, w=label: w.configure(bg=hover, fg=self.theme["text_primary"]))
        label.bind("<Leave>", lambda _event, w=label: w.configure(bg=normal, fg=self.theme["text_secondary"]))
        label.bind("<Button-1>", lambda _event: command())
        label.bind("<Return>", lambda _event: command())
        label.bind("<space>", lambda _event: command())
        return label

    def set_expanded(self, expanded: bool) -> None:
        self.expand_button.configure(text="↙" if expanded else "↗")

    def set_maximized(self, maximized: bool) -> None:
        self.maximize_button.configure(text="❐" if maximized else "□")
