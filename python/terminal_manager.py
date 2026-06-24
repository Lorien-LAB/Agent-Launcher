"""
Agent Launcher - UI for Claude Code, Hermes & Terminal customization
"""
import ctypes
import json
import math
import os
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk

import pystray
from PIL import Image

from session_monitor import SessionMonitor, _fmt_tokens, _fmt_cost

# Enable DPI awareness
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def get_dpi_scale() -> float:
    try:
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
        ctypes.windll.user32.ReleaseDC(0, hdc)
        return dpi / 96.0
    except Exception:
        return 1.0


WT_SETTINGS_PATH = os.path.join(
    os.environ["LOCALAPPDATA"],
    "Packages",
    "Microsoft.WindowsTerminal_8wekyb3d8bbwe",
    "LocalState",
    "settings.json",
)
BASE_DIRS = [
    r"D:\Quantitative Trading",
    r"D:\University\Kaggle",
    r"D:\Obsidian_Lorien_Lab",
    r"D:\University\比赛\AFAC2026挑战组-赛题一：市场参与者交易行为识别与资金流向分析",
    r"C:\Users\Lorien\terminal-manager",
]
HOME_DIR = os.path.expanduser("~")
CLAUDE_PATH = "C:/Users/Lorien/.local/bin/claude.exe"
CLAUDE_ARGS = "--dangerously-skip-permissions"
HERMES_PATH = "C:/Users/Lorien/AppData/Local/hermes/hermes-agent/venv/Scripts/hermes.exe"


# ─── Colors ──────────────────────────────────────────
class C:
    # Main launcher palette
    base    = "#1E1E2E"
    card    = "#181825"
    listbg  = "#313244"
    border  = "#45475A"
    subtle  = "#585B70"
    text    = "#FFFFFF"
    sub     = "#CCCCDD"
    blue    = "#89B4FA"
    green   = "#A6E3A1"
    yellow  = "#F9E2AF"
    mauve   = "#CBA6F7"

    # Session Monitor palette
    panel_bg       = "#11131F"
    panel_card     = "#191C2B"
    panel_hover    = "#20243A"
    panel_border   = "#343B59"
    panel_busy     = "#4D78B8"
    panel_focus    = "#7C8CFF"
    panel_text     = "#F4F7FF"
    panel_sub      = "#AAB3D1"
    panel_muted    = "#68708D"
    cyan           = "#68F0B0"
    orange         = "#FF9D5C"
    red            = "#FF6878"
    purple         = "#A58BFF"


def _clamp_pct(value):
    """Return a display-safe percentage in the inclusive 0..100 range."""
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _short_model_name(model):
    """Compact verbose model identifiers for card badges."""
    if not model or model == "?":
        return ""
    return model.replace("deepseek-v4-pro", "DSv4").replace("claude-", "")


def _format_updated_age(updated_at, now=None):
    """Format a timestamp as a compact human-readable age label."""
    if not updated_at:
        return "Updated —"
    age = max(0, int((time.time() if now is None else now) - updated_at))
    if age < 60:
        return f"Updated {age}s ago"
    if age < 3600:
        return f"Updated {age // 60}m ago"
    return f"Updated {age // 3600}h ago"


def _progress_fill_width(width, pct):
    """Return the fixed progress fill width for a percentage."""
    return int(max(0, width) * _clamp_pct(pct) / 100.0)


def _status_style(display_state):
    """Return (label, accent, border) for a card display state."""
    if display_state == "running":
        return "RUNNING", C.cyan, C.panel_busy
    if display_state == "done":
        return "DONE", C.yellow, C.yellow
    return "IDLE", C.panel_muted, C.panel_border


def _context_text_color(pct):
    """Return the warning text color for a context percentage."""
    pct = _clamp_pct(pct)
    if pct >= 95:
        return C.red
    if pct >= 85:
        return C.orange
    if pct >= 70:
        return C.yellow
    return C.panel_sub


def _blend_hex(color_a, color_b, amount):
    """Linearly blend two #RRGGBB colors."""
    amount = max(0.0, min(1.0, amount))
    vals = []
    for i in (1, 3, 5):
        a = int(color_a[i:i + 2], 16)
        b = int(color_b[i:i + 2], 16)
        vals.append(round(a + (b - a) * amount))
    return "#" + "".join(f"{v:02x}" for v in vals)



def scan_directories():
    """Return tree: [(label, path, parent_iid)] where parent_iid=None means root.
    Treeview iids are assigned during build."""
    items = [("🏠  ~ (home)", HOME_DIR, None)]
    for base in BASE_DIRS:
        if not os.path.isdir(base):
            continue
        try:
            subs = sorted(
                d for d in os.listdir(base)
                if not d.startswith(".") and os.path.isdir(os.path.join(base, d))
            )
            if not subs:
                continue
            parent_name = os.path.basename(base)
            # Pass the base label as a signal for the tree builder
            items.append((f"▸  {parent_name}", base, "PARENT"))
            for sub in subs:
                items.append((f"📁  {sub}", os.path.join(base, sub), None))
        except PermissionError:
            pass
    return items


def load_wt_settings():
    try:
        with open(WT_SETTINGS_PATH, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


def save_wt_settings(data):
    with open(WT_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_current_mode():
    wt = load_wt_settings()
    d = wt.get("profiles", {}).get("defaults", {})
    if d.get("useAcrylic"):
        return "acrylic", int(d.get("acrylicOpacity", 0.33) * 100)
    elif "opacity" in d:
        return "opacity", d["opacity"]
    return "none", 100


def apply_background(mode, value):
    wt = load_wt_settings()
    wt.setdefault("profiles", {}).setdefault("defaults", {})
    d = wt["profiles"]["defaults"]
    for k in ("useAcrylic", "acrylicOpacity", "opacity"):
        d.pop(k, None)
    if mode == "acrylic":
        d["useAcrylic"] = True
        d["acrylicOpacity"] = value / 100.0
    elif mode == "opacity":
        d["opacity"] = value
    save_wt_settings(wt)


# ── Terminal-window handle tracking ─────────────────
# Maps normalized cwd → HWND for pop-to-front.
# Uses "snapshot diff" — enumerate all WT windows before and after launch,
# the new one is the difference.  (PID-based doesn't work: wt.exe is a launcher
# that talks to WindowsTerminal.exe and then exits.)
_terminal_hwnds: dict = {}   # norm_cwd → int hwnd
_HWND_LOCK = threading.Lock()

WT_CLASS = "CASCADIA_HOSTING_WINDOW_CLASS"


def _snapshot_wt_hwnds() -> set:
    """Return a set of HWNDs for all CASCADIA_HOSTING_WINDOW_CLASS windows."""
    seen = set()
    try:
        import ctypes
        @ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_long, ctypes.c_long)
        def _enum(hwnd, _):
            buf = ctypes.create_unicode_buffer(64)
            ctypes.windll.user32.GetClassNameW(hwnd, buf, 63)
            if buf.value == WT_CLASS:
                seen.add(hwnd)
            return 1
        ctypes.windll.user32.EnumWindows(_enum, 0)
    except Exception:
        pass
    return seen


def launch_in_terminal(dir_path, exe_path, args, title):
    """Open exe in a new Windows Terminal window. Track HWND for pop-to-front.

    Uses a temporary PowerShell script to avoid argument-quoting hell
    (wt -Command with semicolons/quotes gets mangled by WT's parser).
    """
    if not os.path.isdir(dir_path):
        return False
    try:
        dir_tag = os.path.basename(dir_path)
        full_title = f"{title} — {dir_tag}"
        norm_cwd = os.path.normpath(dir_path).lower()

        # Write a temp .ps1 — no quoting issues because pwsh reads the file directly
        safe_title = full_title.replace("'", "''")
        safe_exe = exe_path.replace("'", "''")
        script = (
            f"$Host.UI.RawUI.WindowTitle = '{safe_title}'{os.linesep}"
            f"& '{safe_exe}' {args}{os.linesep}"
        )
        tmp = os.path.join(
            os.environ.get("TEMP", os.path.expanduser("~")),
            f"launch_{os.urandom(6).hex()}.ps1")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(script)

        before = _snapshot_wt_hwnds()

        subprocess.Popen(
            ["wt", "-w", "new", "-d", dir_path, "--title", full_title,
             "pwsh", "-NoExit", "-File", tmp],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        # Cleanup temp file after a few seconds
        def _cleanup():
            time.sleep(5)
            try:
                os.remove(tmp)
            except OSError:
                pass
        threading.Thread(target=_cleanup, daemon=True, name="tmp-cleanup").start()

        # Track the new HWND
        def _track():
            for _ in range(40):
                time.sleep(0.1)
                after = _snapshot_wt_hwnds()
                new_hwnds = after - before
                if new_hwnds:
                    with _HWND_LOCK:
                        _terminal_hwnds[norm_cwd] = new_hwnds.pop()
                    return
        threading.Thread(target=_track, daemon=True, name="hwnd-track").start()
        return True
    except Exception:
        return False


def launch_claude(dir_path):
    return launch_in_terminal(dir_path, CLAUDE_PATH, CLAUDE_ARGS, "Claude Code")


def launch_hermes(dir_path):
    return launch_in_terminal(dir_path, HERMES_PATH, "", "Hermes")


# ─── Rounded Button (Canvas-based, lightweight, stable) ──
def _round_rect(canvas, x1, y1, x2, y2, r, **kw):
    """Draw a rounded rectangle using thick rounded lines (proper anti-alias)."""
    r = min(r, (x2 - x1) // 2, (y2 - y1) // 2)
    d = 2 * r
    # Center rectangle fill
    canvas.create_rectangle(x1+r, y1, x2-r, y2, **kw)
    # Top and bottom strips
    canvas.create_rectangle(x1, y1+r, x2, y2-r, **kw)
    # Four corner arcs (pieslice = filled quarter-circle)
    canvas.create_arc(x1, y1, x1+d, y1+d, start=90, extent=90, style="pieslice", **kw)
    canvas.create_arc(x2-d, y1, x2, y1+d, start=0, extent=90, style="pieslice", **kw)
    canvas.create_arc(x2-d, y2-d, x2, y2, start=270, extent=90, style="pieslice", **kw)
    canvas.create_arc(x1, y2-d, x1+d, y2, start=180, extent=90, style="pieslice", **kw)
    # Outline — stroked arcs for crisp edges
    if "outline" in kw and kw.get("outline"):
        ol_color = kw["outline"]
        canvas.create_arc(x1, y1, x1+d, y1+d, start=90, extent=90, style="arc", outline=ol_color)
        canvas.create_arc(x2-d, y1, x2, y1+d, start=0, extent=90, style="arc", outline=ol_color)
        canvas.create_arc(x2-d, y2-d, x2, y2, start=270, extent=90, style="arc", outline=ol_color)
        canvas.create_arc(x1, y2-d, x1+d, y2, start=180, extent=90, style="arc", outline=ol_color)
        canvas.create_line(x1+r, y1, x2-r, y1, fill=ol_color)
        canvas.create_line(x1+r, y2, x2-r, y2, fill=ol_color)
        canvas.create_line(x1, y1+r, x1, y2-r, fill=ol_color)
        canvas.create_line(x2, y1+r, x2, y2-r, fill=ol_color)


class NeonButton(tk.Canvas):
    """Canvas button: dark fill + colored glow border + text."""

    def __init__(self, parent, text, bg, glow, fg="#F5F5FF",
                 command=None, radius=20, font=("Segoe UI", 12, "bold"), **kw):
        super().__init__(parent, highlightthickness=0, cursor="hand2", bg=C.base, **kw)
        self._text = text
        self._bg = bg
        self._glow = glow
        self._fg = fg
        self._cmd = command
        self._r = radius
        self._font = font
        self._hovered = False

        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", lambda e: self._cmd())

    def _set_hover(self, h):
        self._hovered = h
        self._draw()

    def _draw(self, event=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 8 or h < 8:
            return
        r = self._r

        # Background fill
        self.create_rectangle(0, 0, w, h, fill=C.base, outline="", width=0)

        # Glow border (thick, low alpha look — simulate with layered outlines)
        colors = [self._glow, self._glow, self._glow] if self._hovered else []
        widths = [3, 2, 1]

        # Outer glow (larger, more transparent via darker blend)
        # Hover: extra glow ring
        if self._hovered:
            _round_rect(self, 1, 1, w-1, h-1, r, fill="", outline=self._glow)

        # Base fill
        fill_color = self._glow if self._hovered else self._bg
        _round_rect(self, 3, 3, w-3, h-3, r-1, fill=fill_color, outline="")

        # Text
        self.create_text(w//2, h//2, text=self._text, fill=self._fg,
                          font=self._font)


class SessionCard:
    """Reusable, independently updated Session Monitor card."""

    COLLAPSED_H = 68
    EXPANDED_H = 118
    ENTER_DELAY_MS = 80
    LEAVE_DELAY_MS = 120
    HEIGHT_TICK_MS = 20

    def __init__(self, parent, scale, on_activate, on_height_changed,
                 on_hover_request, on_mousewheel=None):
        self.parent = parent
        self.s = scale
        self.on_activate = on_activate
        self.on_height_changed = on_height_changed
        self.on_hover_request = on_hover_request
        self.on_mousewheel = on_mousewheel
        self.snapshot = None
        self.session_id = ""
        self.display_state = "idle"
        self.hovered = False
        self._destroyed = False
        self._hover_after_id = None
        self._height_after_id = None
        self._leave_check_id = None
        self._tooltip_after_id = None
        self._path_tooltip = None
        self._full_path = ""
        self._last_age_second = None
        self._current_h = self.s(self.COLLAPSED_H)
        self._target_h = self._current_h

        self.frame = tk.Frame(
            parent, bg=C.panel_bg, height=self._current_h,
            highlightthickness=0, cursor="hand2",
        )
        self.frame.grid_propagate(False)
        self.frame.grid_columnconfigure(0, weight=1)

        self._card_canvas = tk.Canvas(
            self.frame, bg=C.panel_bg, highlightthickness=0, bd=0,
        )
        self._card_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._card_canvas.bind("<Configure>", lambda _e: self._draw_card(0.0))

        self._content = tk.Frame(self.frame, bg=C.panel_card)
        self._content.place(
            x=self.s(13), y=self.s(8), relwidth=1, width=-self.s(26),
        )

        top = tk.Frame(self._content, bg=C.panel_card)
        top.pack(fill="x")
        self._status_canvas = tk.Canvas(
            top, width=self.s(18), height=self.s(18), bg=C.panel_card,
            highlightthickness=0, bd=0,
        )
        self._status_canvas.pack(side="left", padx=(0, self.s(6)))
        self._name_label = tk.Label(
            top, text="", bg=C.panel_card, fg=C.panel_text,
            font=("Consolas", 11, "bold"), anchor="w",
        )
        self._name_label.pack(side="left", fill="x", expand=True)
        self._state_label = tk.Label(
            top, text="IDLE", bg=C.panel_card, fg=C.panel_muted,
            font=("Consolas", 9, "bold"), anchor="e",
        )
        self._state_label.pack(side="right")

        meta = tk.Frame(self._content, bg=C.panel_card)
        meta.pack(fill="x", pady=(self.s(2), 0))
        badges = tk.Frame(meta, bg=C.panel_card)
        badges.pack(side="left", fill="x", expand=True)
        self._model_badge = self._make_badge(badges, C.purple)
        self._branch_badge = self._make_badge(badges, C.blue)
        self._agent_badge = self._make_badge(badges, C.cyan)
        self._pct_label = tk.Label(
            meta, text="0.0%", bg=C.panel_card, fg=C.panel_sub,
            font=("Consolas", 9, "bold"), anchor="e",
        )
        self._pct_label.pack(side="right")

        self._progress_canvas = tk.Canvas(
            self._content, height=self.s(7), bg=C.panel_card,
            highlightthickness=0, bd=0,
        )
        self._progress_canvas.pack(fill="x", pady=(self.s(4), 0))
        self._progress_canvas.bind(
            "<Configure>", lambda _e: self._draw_progress(0.0)
        )

        self._details = tk.Frame(self._content, bg=C.panel_card)
        self._details.pack(fill="x", pady=(self.s(8), 0))
        self._token_label = tk.Label(
            self._details, text="", bg=C.panel_card, fg=C.panel_sub,
            font=("Consolas", 9), anchor="w",
        )
        self._token_label.pack(fill="x")
        self._path_label = tk.Label(
            self._details, text="", bg=C.panel_card, fg=C.panel_muted,
            font=("Consolas", 8), anchor="w",
        )
        self._path_label.pack(fill="x", pady=(self.s(2), 0))
        self._updated_label = tk.Label(
            self._details, text="Updated —", bg=C.panel_card,
            fg=C.panel_muted, font=("Segoe UI", 8), anchor="w",
        )
        self._updated_label.pack(fill="x", pady=(self.s(1), 0))
        self._path_label.bind("<Enter>", self._schedule_path_tooltip, add="+")
        self._path_label.bind("<Leave>", self._hide_path_tooltip, add="+")

        self._bind_interactions(self.frame)

    def _make_badge(self, parent, color):
        label = tk.Label(
            parent, text="", bg=C.panel_card, fg=color,
            font=("Consolas", 8, "bold"), padx=self.s(4), pady=0,
        )
        return label

    def _set_badge(self, label, text):
        if text:
            label.configure(text=text)
            if not label.winfo_manager():
                label.pack(side="left", padx=(0, self.s(5)))
        elif label.winfo_manager():
            label.pack_forget()

    def _bind_interactions(self, widget):
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<Button-1>", self._on_click, add="+")
        if self.on_mousewheel is not None:
            widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        for child in widget.winfo_children():
            self._bind_interactions(child)

    def _on_click(self, _event=None):
        if self.snapshot and self.snapshot.cwd:
            self.on_activate(self.snapshot.cwd)

    def _on_mousewheel(self, event):
        if self.on_mousewheel is not None:
            self.on_mousewheel(event.delta)
        return "break"

    def _schedule_path_tooltip(self, _event=None):
        self._hide_path_tooltip()
        if not self._full_path or self._full_path == "—":
            return
        try:
            self._tooltip_after_id = self.frame.after(450, self._show_path_tooltip)
        except tk.TclError:
            self._tooltip_after_id = None

    def _show_path_tooltip(self):
        self._tooltip_after_id = None
        if self._destroyed or not self._full_path:
            return
        try:
            tip = tk.Toplevel(self.frame)
            tip.overrideredirect(True)
            tip.attributes("-topmost", True)
            tip.configure(bg=C.panel_focus)
            tk.Label(
                tip, text=self._full_path, bg=C.panel_card, fg=C.panel_text,
                font=("Consolas", 8), padx=self.s(8), pady=self.s(4),
            ).pack(padx=1, pady=1)
            x, y = self.frame.winfo_pointerxy()
            tip.geometry(f"+{x + self.s(12)}+{y + self.s(14)}")
            self._path_tooltip = tip
        except tk.TclError:
            self._path_tooltip = None

    def _hide_path_tooltip(self, _event=None):
        self._cancel_after("_tooltip_after_id")
        tip = self._path_tooltip
        self._path_tooltip = None
        if tip is not None:
            try:
                tip.destroy()
            except tk.TclError:
                pass

    def _on_enter(self, _event=None):
        if self._destroyed:
            return
        self._cancel_after("_leave_check_id")
        self.on_hover_request(self.session_id, True)

    def _on_leave(self, _event=None):
        if self._destroyed:
            return
        self._cancel_after("_leave_check_id")
        self._leave_check_id = self.frame.after(25, self._check_pointer_left)

    def _check_pointer_left(self):
        self._leave_check_id = None
        if self._destroyed:
            return
        try:
            x, y = self.frame.winfo_pointerxy()
            widget = self.frame.winfo_containing(x, y)
            while widget is not None:
                if widget is self.frame:
                    return
                widget = getattr(widget, "master", None)
        except tk.TclError:
            pass
        self.on_hover_request(self.session_id, False)

    def set_hovered(self, hovered, immediate=False):
        if self._destroyed:
            return
        self._cancel_after("_hover_after_id")
        delay = 0 if immediate else (
            self.ENTER_DELAY_MS if hovered else self.LEAVE_DELAY_MS
        )
        self._hover_after_id = self.frame.after(
            delay, lambda h=hovered: self._apply_hover(h)
        )

    def _apply_hover(self, hovered):
        self._hover_after_id = None
        if self._destroyed or self.hovered == hovered:
            return
        self.hovered = hovered
        self._target_h = self.s(
            self.EXPANDED_H if hovered else self.COLLAPSED_H
        )
        self._apply_background()
        self._start_height_animation()

    def _start_height_animation(self):
        if self._height_after_id is None:
            self._height_after_id = self.frame.after(0, self._tick_height)

    def _tick_height(self):
        self._height_after_id = None
        if self._destroyed:
            return
        delta = self._target_h - self._current_h
        if abs(delta) <= 1:
            self._current_h = self._target_h
        else:
            step = max(1, int(abs(delta) * 0.34))
            self._current_h += step if delta > 0 else -step
        try:
            self.frame.configure(height=self._current_h)
            self._draw_card(0.0)
            self.on_height_changed()
        except tk.TclError:
            return
        if self._current_h != self._target_h:
            self._height_after_id = self.frame.after(
                self.HEIGHT_TICK_MS, self._tick_height
            )

    def update_snapshot(self, snapshot, display_state):
        if self._destroyed:
            return
        self.snapshot = snapshot
        self.session_id = snapshot.session_id
        self.display_state = display_state

        name = snapshot.short_dir or snapshot.name or "?"
        if len(name) > 30:
            name = name[:29] + "…"
        self._name_label.configure(text=name)

        state_text, state_color, _border = _status_style(display_state)
        self._state_label.configure(text=state_text, fg=state_color)

        model = _short_model_name(snapshot.model)
        branch = (snapshot.git_branch or "").strip()
        if branch.lower() in ("main", "master"):
            branch = ""
        agents = f"{snapshot.subagent_count} agents" if snapshot.subagent_count else ""
        self._set_badge(self._model_badge, model)
        self._set_badge(self._branch_badge, branch)
        self._set_badge(self._agent_badge, agents)

        pct = _clamp_pct(snapshot.context_pct)
        self._pct_label.configure(
            text=f"{pct:.1f}%", fg=_context_text_color(pct)
        )
        self._token_label.configure(
            text=(f"{_fmt_tokens(snapshot.input_tokens)} input  ·  "
                  f"{_fmt_tokens(snapshot.output_tokens)} output  ·  "
                  f"{_fmt_cost(snapshot.cost_usd)}")
        )
        full_path = snapshot.cwd or "—"
        self._full_path = full_path
        shown_path = full_path if len(full_path) <= 58 else "…" + full_path[-57:]
        self._path_label.configure(text=shown_path)
        self._updated_label.configure(text=_format_updated_age(snapshot.updated_at))
        self._last_age_second = int(time.time())
        self._apply_background()
        self._draw_all(0.0)

    def _apply_background(self):
        bg = C.panel_hover if self.hovered else C.panel_card
        widgets = [
            self._content, self._name_label, self._state_label,
            self._model_badge, self._branch_badge, self._agent_badge,
            self._pct_label, self._progress_canvas, self._details,
            self._token_label, self._path_label, self._updated_label,
            self._status_canvas,
        ]
        for widget in widgets:
            try:
                widget.configure(bg=bg)
            except tk.TclError:
                pass
        for child in self._content.winfo_children():
            if isinstance(child, tk.Frame):
                child.configure(bg=bg)
                for grandchild in child.winfo_children():
                    if isinstance(grandchild, tk.Frame):
                        grandchild.configure(bg=bg)

    def _draw_all(self, phase):
        self._draw_card(phase)
        self._draw_status(phase)
        self._draw_progress(phase)

    def _draw_card(self, phase):
        if self._destroyed:
            return
        try:
            cv = self._card_canvas
            w = cv.winfo_width()
            h = self._current_h
            if w < self.s(40) or h < self.s(20):
                return
            cv.delete("all")
            bg = C.panel_hover if self.hovered else C.panel_card
            _label, _accent, border = _status_style(self.display_state)
            if self.hovered:
                border = C.panel_focus
            elif self.display_state == "running":
                strength = 0.18 + 0.18 * (0.5 + 0.5 * math.sin(phase))
                border = _blend_hex(C.panel_busy, C.panel_focus, strength)
            _round_rect(
                cv, 1, 1, w - 2, h - 2, self.s(14),
                fill=bg, outline=border,
            )
            # Thin cyber accent rail on the left.
            rail = _status_style(self.display_state)[1]
            cv.create_line(
                self.s(5), self.s(18), self.s(5), h - self.s(18),
                fill=rail, width=self.s(2),
            )
        except tk.TclError:
            pass

    def _draw_status(self, phase):
        try:
            cv = self._status_canvas
            cv.delete("all")
            d = self.s(18)
            cx = cy = d / 2
            _text, color, _border = _status_style(self.display_state)
            if self.display_state == "running":
                size = self.s(6.2) * (0.90 + 0.10 * math.sin(phase))
            elif self.display_state == "done":
                size = self.s(6.0)
            else:
                size = self.s(4.2)
            p = 0.38
            pts = [
                cx, cy - size, cx + size * p, cy - size * p,
                cx + size, cy, cx + size * p, cy + size * p,
                cx, cy + size, cx - size * p, cy + size * p,
                cx - size, cy, cx - size * p, cy - size * p,
            ]
            if self.display_state == "idle":
                cv.create_polygon(pts, fill="", outline=color, width=1, smooth=True)
            else:
                cv.create_polygon(pts, fill=color, outline="", smooth=True)
                if self.display_state == "running":
                    glow = _blend_hex(color, "#FFFFFF", 0.35)
                    cv.create_polygon(pts, fill="", outline=glow, width=1, smooth=True)
        except tk.TclError:
            pass

    def _draw_progress(self, phase):
        if self._destroyed or not self.snapshot:
            return
        try:
            import colorsys
            cv = self._progress_canvas
            w = cv.winfo_width()
            h = max(self.s(5), cv.winfo_height())
            if w < self.s(20):
                return
            cv.delete("all")
            r = h / 2
            d = 2 * r
            bg = "#282C43"
            cv.create_arc(0, 0, d, h, start=90, extent=180, fill=bg, outline="")
            cv.create_rectangle(r, 0, w - r, h, fill=bg, outline="")
            cv.create_arc(w - d, 0, w, h, start=270, extent=180, fill=bg, outline="")

            pct = _clamp_pct(self.snapshot.context_pct)
            fw = _progress_fill_width(w, pct)
            if fw <= 0:
                return

            def grad_color(position):
                t = max(0.0, min(1.0, position / max(1, w)))
                hue = (1.0 - t) * 0.33
                rr, gg, bb = colorsys.hsv_to_rgb(hue, 0.86, 0.96)
                return f"#{int(rr * 255):02x}{int(gg * 255):02x}{int(bb * 255):02x}"

            if fw <= d:
                cv.create_oval(0, 0, fw, h, fill=grad_color(fw / 2), outline="")
            else:
                cv.create_arc(0, 0, d, h, start=90, extent=180,
                              fill=grad_color(0), outline="")
                body_start = r
                body_end = fw - r
                segments = max(1, min(40, int((body_end - body_start) / 5)))
                seg_w = (body_end - body_start) / segments if segments else 0
                for i in range(segments):
                    x0 = body_start + i * seg_w
                    x1 = body_start + (i + 1) * seg_w + 1
                    cv.create_rectangle(
                        x0, 0, x1, h,
                        fill=grad_color((x0 + x1) / 2), outline="",
                    )
                cv.create_arc(fw - d, 0, fw, h, start=270, extent=180,
                              fill=grad_color(fw), outline="")

            if self.display_state == "running" and fw > self.s(14):
                shimmer_t = (0.5 + 0.5 * math.sin(phase * 0.72))
                x = self.s(5) + shimmer_t * max(1, fw - self.s(10))
                cv.create_line(x, 1, x, h - 1, fill="#E8FFFF", width=self.s(2))
            if pct >= 95 and fw > r:
                pulse = 0.45 + 0.35 * (0.5 + 0.5 * math.sin(phase * 1.3))
                endpoint = _blend_hex(C.red, "#FFFFFF", pulse)
                cv.create_oval(
                    fw - r - self.s(1), -self.s(1),
                    fw + r + self.s(1), h + self.s(1),
                    outline=endpoint, width=1,
                )
        except tk.TclError:
            pass

    def animate(self, phase, now):
        if self._destroyed or not self.snapshot:
            return
        second = int(now)
        if second != self._last_age_second:
            self._last_age_second = second
            try:
                self._updated_label.configure(
                    text=_format_updated_age(self.snapshot.updated_at, now)
                )
            except tk.TclError:
                return
        pct = _clamp_pct(self.snapshot.context_pct)
        if self.display_state == "running" or self.display_state == "done" or self.hovered or pct >= 95:
            self._draw_all(phase)

    def grid_at(self, row):
        if self._destroyed:
            return
        self.frame.grid(
            row=row, column=0, sticky="ew",
            padx=(self.s(1), self.s(1)), pady=(0, self.s(6)),
        )

    def _cancel_after(self, attr):
        after_id = getattr(self, attr, None)
        if after_id is None:
            return
        try:
            self.frame.after_cancel(after_id)
        except tk.TclError:
            pass
        setattr(self, attr, None)

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        self._hide_path_tooltip()
        for attr in ("_hover_after_id", "_height_after_id", "_leave_check_id"):
            self._cancel_after(attr)
        try:
            self.frame.destroy()
        except tk.TclError:
            pass


# ─── Main App ────────────────────────────────────────
class TerminalManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Agent Launcher")

        self.scale = get_dpi_scale()
        self.root.tk.call("tk", "scaling", self.scale)
        self.root.configure(bg=C.base)

        self.root.resizable(True, True)

        base_w, base_h = 300, 420
        self.w = max(1, round(base_w * self.scale))
        self.h = max(1, round(base_h * self.scale))
        self.root.minsize(self.w, self.h)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - self.w) // 2
        y = (sh - self.h) // 2
        self.root.geometry(f"{self.w}x{self.h}+{x}+{y}")

        self.dirs = scan_directories()
        self.build_ui()
        self.load_current_settings()

        # ── System Tray + Session Monitor ──
        self._tray = None
        self._tray_icon = None
        self._stats = None
        self._stats_panel = None
        self._animation_phase = 0.0
        self._animation_after_id = None
        self._panel_resize_after_id = None
        self._last_statuses = {}
        self._done_until = {}
        self._session_cards = {}
        self._expanded_session_id = None

        self._create_stats_panel()
        self._monitor = SessionMonitor()
        self._monitor.on_update(self._on_stats_update)
        self._monitor.scan()
        self._monitor.start()

        self.root.protocol("WM_DELETE_WINDOW", self._hide_to_tray)
        self.root.after(100, self._create_tray)
        self._animation_after_id = self.root.after(200, self._animate_loop)

    def _create_stats_panel(self):
        """Create the rounded, futuristic Session Monitor window."""
        if self._stats_panel is not None:
            return
        s = self.s

        panel = tk.Toplevel(self.root)
        panel.title("Session Monitor")
        panel.overrideredirect(True)
        panel.attributes("-topmost", True)
        panel.attributes("-alpha", 0.94)
        panel.configure(bg=C.panel_bg)

        pw, ph = s(430), s(104)
        sw = panel.winfo_screenwidth()
        panel.geometry(f"{pw}x{ph}+{sw // 2 - pw // 2}+0")

        radius = s(18)
        pad = s(8)

        header = tk.Frame(panel, bg=C.panel_bg, height=s(60))
        header.place(x=pad, y=pad, relwidth=1, width=-2 * pad, height=s(60))
        header.pack_propagate(False)

        top = tk.Frame(header, bg=C.panel_bg)
        top.pack(fill="x")
        tk.Label(
            top, text="SESSION MONITOR", bg=C.panel_bg, fg=C.panel_text,
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")
        self._clock_label = tk.Label(
            top, text="--:--:--", bg=C.panel_bg, fg=C.panel_sub,
            font=("Consolas", 12, "bold"),
        )
        self._clock_label.pack(side="right")

        summary = tk.Frame(header, bg=C.panel_bg)
        summary.pack(fill="x", pady=(s(5), 0))
        self._active_summary = tk.Label(
            summary, text="● 0 ACTIVE", bg=C.panel_bg, fg=C.cyan,
            font=("Consolas", 8, "bold"),
        )
        self._active_summary.pack(side="left")
        self._idle_summary = tk.Label(
            summary, text="○ 0 IDLE", bg=C.panel_bg, fg=C.panel_muted,
            font=("Consolas", 8, "bold"),
        )
        self._idle_summary.pack(side="left", padx=(s(12), 0))
        self._token_summary = tk.Label(
            summary, text="0 TOKENS", bg=C.panel_bg, fg=C.purple,
            font=("Consolas", 8, "bold"),
        )
        self._token_summary.pack(side="right")

        self._header_scan = tk.Canvas(
            header, height=s(2), bg=C.panel_bg, highlightthickness=0, bd=0,
        )
        self._header_scan.pack(fill="x", pady=(s(6), 0))

        self._bind_panel_drag(header)

        body_y = pad + s(64)
        viewport = tk.Canvas(
            panel, bg=C.panel_bg, highlightthickness=0, bd=0,
            yscrollincrement=s(28),
        )
        viewport.place(x=pad, y=body_y, relwidth=1, width=-2 * pad)
        content = tk.Frame(viewport, bg=C.panel_bg)
        content.grid_columnconfigure(0, weight=1)
        body_window = viewport.create_window((0, 0), window=content, anchor="nw")
        content.bind(
            "<Configure>",
            lambda _e: viewport.configure(scrollregion=viewport.bbox("all")),
        )
        viewport.bind(
            "<Configure>",
            lambda e: viewport.itemconfigure(body_window, width=e.width),
        )
        viewport.bind("<MouseWheel>", lambda e: self._scroll_panel(e.delta))
        self._panel_viewport = viewport
        self._panel_body_window = body_window
        self._panel_body = content
        self._body_y0 = body_y
        self._panel_r = radius
        self._panel_pad = pad
        self._panel_h = ph
        self._stats_panel = panel

        self._empty_label = tk.Label(
            content, text="NO ACTIVE SESSIONS", bg=C.panel_bg,
            fg=C.panel_muted, font=("Consolas", 9, "bold"),
        )

        def _do_clip():
            try:
                import ctypes.wintypes
                hwnd = int(panel.frame(), 16)
                rect = ctypes.wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(
                    ctypes.wintypes.HWND(hwnd), ctypes.byref(rect)
                )
                clip_w = rect.right - rect.left
                clip_h = rect.bottom - rect.top
                if clip_w < 10 or clip_h < 10:
                    return
                d = radius * 2
                hrgn = ctypes.windll.gdi32.CreateRoundRectRgn(
                    0, 0, clip_w, clip_h, d, d
                )
                ctypes.windll.user32.SetWindowRgn(
                    ctypes.wintypes.HWND(hwnd), hrgn, True
                )
            except Exception:
                pass

        self._clip_panel = _do_clip
        panel.after(200, _do_clip)

    def _bind_panel_drag(self, widget):
        """Bind dragging only to the header and all of its children."""
        widget.bind("<Button-1>", self._panel_drag_start, add="+")
        widget.bind("<B1-Motion>", self._panel_drag_move, add="+")
        for child in widget.winfo_children():
            self._bind_panel_drag(child)

    def _panel_drag_start(self, event):
        self._drag_x = event.x_root - self._stats_panel.winfo_x()
        self._drag_y = event.y_root - self._stats_panel.winfo_y()

    @staticmethod
    def _get_screen_bottom():
        """Return the effective bottom y (screen height minus taskbar gap).
        Handles both permanent taskbar and auto-hide via SHAppBarMessage."""
        import ctypes.wintypes
        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
        work = RECT()
        full = RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(work), 0)
        ctypes.windll.user32.GetWindowRect(
            ctypes.windll.user32.GetDesktopWindow(), ctypes.byref(full))
        visible_tb = full.bottom - work.bottom  # 0 when auto-hide
        if visible_tb > 0:
            return work.bottom
        try:
            state = ctypes.windll.shell32.SHAppBarMessage(0x00000004, None)
            if state & 1:
                return full.bottom - 4  # auto-hide: 4px trigger gap
        except Exception:
            pass
        return full.bottom

    def _panel_drag_move(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        pw = self._stats_panel.winfo_width()
        ph = self._stats_panel.winfo_height()
        sw = self._stats_panel.winfo_screenwidth()
        sb = self._get_screen_bottom()
        snap = self.s(40)
        if abs(x) < snap:
            x = 0
        if abs(x + pw - sw) < snap:
            x = sw - pw
        if abs(y) < snap:
            y = 0
        if abs(y + ph - sb) < snap:
            y = sb - ph
        self._stats_panel.geometry(f"+{x}+{y}")

    def _on_stats_update(self, stats):
        """Called by monitor thread; marshal all widget work to tkinter."""
        self._stats = stats
        try:
            self.root.after(
                0, lambda: (self._update_tray(stats), self._update_panel(stats))
            )
        except tk.TclError:
            pass

    def _animate_loop(self):
        """Animate only active visual accents; never rebuild card widgets."""
        self._animation_phase = (self._animation_phase + 0.12) % (2 * math.pi)
        phase = self._animation_phase
        self._frame_count = getattr(self, "_frame_count", 0) + 1
        now = time.time()

        if self._frame_count % 10 == 0:
            try:
                import datetime
                self._clock_label.configure(
                    text=datetime.datetime.now().strftime("%H:%M:%S")
                )
            except tk.TclError:
                pass

        try:
            cv = self._header_scan
            width = cv.winfo_width()
            height = max(1, cv.winfo_height())
            cv.delete("all")
            cv.create_line(0, height / 2, width, height / 2,
                           fill=C.panel_border, width=1)
            if width > 10:
                scan_x = ((phase / (2 * math.pi)) * (width + self.s(70))) - self.s(35)
                cv.create_line(
                    scan_x - self.s(28), height / 2,
                    scan_x + self.s(28), height / 2,
                    fill=C.panel_focus, width=self.s(2),
                )
        except (AttributeError, tk.TclError):
            pass

        monotonic_now = time.monotonic()
        for sid, deadline in list(self._done_until.items()):
            if monotonic_now >= deadline:
                self._done_until.pop(sid, None)
                card = self._session_cards.get(sid)
                if card and card.snapshot and card.snapshot.status != "busy":
                    card.update_snapshot(card.snapshot, "idle")

        for card in list(self._session_cards.values()):
            card.animate(phase, now)

        try:
            self._animation_after_id = self.root.after(100, self._animate_loop)
        except tk.TclError:
            self._animation_after_id = None

    def _update_panel(self, stats):
        """Reconcile persistent SessionCard instances with monitor snapshots."""
        try:
            if not self._stats_panel or not self._stats_panel.winfo_exists():
                return
        except tk.TclError:
            return

        self._active_summary.configure(text=f"● {stats.active_count} ACTIVE")
        self._idle_summary.configure(text=f"○ {stats.idle_count} IDLE")
        self._token_summary.configure(
            text=f"{_fmt_tokens(stats.total_tokens)} TOKENS"
        )

        current_statuses = {s.session_id: s.status for s in stats.sessions}
        cwd_by_id = {s.session_id: s.cwd for s in stats.sessions}
        for sid, status in current_statuses.items():
            previous = self._last_statuses.get(sid)
            if previous == "busy" and status == "idle":
                self._done_until[sid] = time.monotonic() + 5.0
                cwd = cwd_by_id.get(sid, "")
                if cwd:
                    self.root.after(
                        500, lambda target=cwd: self._bring_terminal_to_front(target)
                    )
            elif status == "busy":
                self._done_until.pop(sid, None)
        self._last_statuses = current_statuses

        visible = list(stats.sessions[:12])
        wanted = {snapshot.session_id for snapshot in visible}
        for sid in set(self._session_cards) - wanted:
            card = self._session_cards.pop(sid)
            card.destroy()
            self._done_until.pop(sid, None)
            if self._expanded_session_id == sid:
                self._expanded_session_id = None

        monotonic_now = time.monotonic()
        for row, snapshot in enumerate(visible):
            card = self._session_cards.get(snapshot.session_id)
            if card is None:
                card = SessionCard(
                    self._panel_body,
                    self.s,
                    on_activate=self._bring_terminal_to_front,
                    on_height_changed=self._schedule_panel_resize,
                    on_hover_request=self._request_card_hover,
                    on_mousewheel=self._scroll_panel,
                )
                self._session_cards[snapshot.session_id] = card
            if snapshot.status == "busy":
                display_state = "running"
            elif self._done_until.get(snapshot.session_id, 0) > monotonic_now:
                display_state = "done"
            else:
                display_state = "idle"
            card.update_snapshot(snapshot, display_state)
            card.grid_at(row)

        if visible:
            self._empty_label.grid_remove()
        else:
            self._empty_label.grid(
                row=0, column=0, sticky="ew",
                padx=self.s(8), pady=(self.s(16), self.s(18)),
            )

        self._schedule_panel_resize()

    def _request_card_hover(self, session_id, hovered):
        """Enforce the single-expanded-card rule."""
        card = self._session_cards.get(session_id)
        if card is None:
            return
        if hovered:
            previous_id = self._expanded_session_id
            if previous_id and previous_id != session_id:
                previous = self._session_cards.get(previous_id)
                if previous:
                    previous.set_hovered(False, immediate=True)
            self._expanded_session_id = session_id
            card.set_hovered(True)
        else:
            card.set_hovered(False)
            if self._expanded_session_id == session_id:
                self._expanded_session_id = None

    def _scroll_panel(self, delta):
        """Scroll the card viewport while preserving the floating panel position."""
        try:
            direction = -1 if delta > 0 else 1
            self._panel_viewport.yview_scroll(direction, "units")
        except (AttributeError, tk.TclError):
            pass

    def _schedule_panel_resize(self):
        """Coalesce rapid card-height changes into one geometry update."""
        if not self._stats_panel:
            return
        if self._panel_resize_after_id is not None:
            try:
                self.root.after_cancel(self._panel_resize_after_id)
            except tk.TclError:
                pass
        try:
            self._panel_resize_after_id = self.root.after(
                15, self._resize_stats_panel
            )
        except tk.TclError:
            self._panel_resize_after_id = None

    def _resize_stats_panel(self):
        self._panel_resize_after_id = None
        try:
            body = self._panel_body
            body.update_idletasks()
            body_req = body.winfo_reqheight()
            width = self.s(430)
            pad = self._panel_pad
            needed = max(
                self.s(104), self._body_y0 + pad + max(body_req, self.s(30))
            )
            screen_bottom = self._get_screen_bottom()
            needed = min(needed, max(self.s(104), screen_bottom - self.s(8)))

            x = self._stats_panel.winfo_x()
            y = self._stats_panel.winfo_y()
            previous_h = getattr(self, "_panel_h", needed)
            bottom_pinned = abs((y + previous_h) - screen_bottom) < self.s(60)
            top_pinned = y <= self.s(5)
            if bottom_pinned:
                y = max(0, screen_bottom - needed)
            elif top_pinned:
                y = 0
            else:
                y = max(0, min(y, screen_bottom - needed))

            self._stats_panel.geometry(f"{width}x{needed}+{x}+{y}")
            viewport_h = max(self.s(30), needed - self._body_y0 - pad)
            self._panel_viewport.place_configure(height=viewport_h)
            self._panel_viewport.configure(scrollregion=self._panel_viewport.bbox("all"))
            self._panel_h = needed
            if hasattr(self, "_clip_panel"):
                self.root.after(35, self._clip_panel)
        except (AttributeError, tk.TclError):
            pass

    def _update_tray(self, stats):
        """Refresh tray tooltip with live stats."""
        if not self._tray_icon:
            return
        tip = f"Lorien_Lab"
        tip += f"\n{stats.active_count} active · {stats.idle_count} idle"
        tip += f"\n{_fmt_tokens(stats.total_input)} in · {_fmt_tokens(stats.total_output)} out"
        if stats.total_cost > 0.001:
            tip += f" · {_fmt_cost(stats.total_cost)}"
        for s in stats.sessions[:6]:
            icon = "●" if s.status == "busy" else "○"
            tip += f"\n{icon} {s.short_dir:<28} {_fmt_tokens(s.input_tokens):>6} in"
        self._tray_icon.title = tip[:127]  # Windows limit

    def _create_tray(self):
        """Create system tray icon (runs after window is ready)."""
        try:
            icon_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "icon.png")
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
            else:
                img = Image.new("RGB", (64, 64), "#2E1A47")
            menu = pystray.Menu(
                pystray.MenuItem("Show", self._show_from_tray, default=True),
                pystray.MenuItem("Restart", self._restart_app),
                pystray.MenuItem("Exit", self._quit_app),
            )
            self._tray_icon = pystray.Icon(
                "AgentLauncher", img, "Agent Launcher", menu)
            self._tray_thread = threading.Thread(
                target=self._tray_icon.run, daemon=True)
            self._tray_thread.start()
        except Exception:
            pass  # tray is optional

    def _hide_to_tray(self):
        """Minimize to tray instead of closing."""
        self.root.withdraw()

    def _show_from_tray(self):
        """Restore window from tray."""
        self.root.after(0, self._restore_window)

    def _restore_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _bring_terminal_to_front(self, cwd=None):
        """Bring the terminal window matching cwd to front.

        Uses the snapshot-diff HWND map populated by launch_in_terminal.
        Falls back to title scan for windows launched outside this session.
        """
        if not cwd:
            return
        norm = os.path.normpath(cwd).lower()

        # 1. HWND cache (fast path)
        with _HWND_LOCK:
            hwnd = _terminal_hwnds.get(norm)
        if hwnd:
            try:
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                return
            except Exception: pass

        # 2. Fallback — title-based enumeration
        self._bring_terminal_by_title(cwd)

    def _bring_terminal_by_title(self, cwd):
        """Enumerate all WT windows and match by title substring."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            dir_tag = os.path.basename(cwd) if cwd else None
            if not dir_tag:
                return

            found_hwnd = None

            @ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_long, ctypes.c_long)
            def _enum(hwnd, _):
                nonlocal found_hwnd
                buf_cls = ctypes.create_unicode_buffer(64)
                user32.GetClassNameW(hwnd, buf_cls, 63)
                if buf_cls.value != WT_CLASS:
                    return 1
                buf_text = ctypes.create_unicode_buffer(256)
                user32.GetWindowTextW(hwnd, buf_text, 255)
                t = buf_text.value
                if dir_tag in t:
                    found_hwnd = hwnd
                    return 0  # stop
                return 1
            user32.EnumWindows(_enum, 0)

            if found_hwnd:
                with _HWND_LOCK:
                    _terminal_hwnds[os.path.normpath(cwd).lower()] = found_hwnd
                user32.SetForegroundWindow(found_hwnd)
        except Exception:
            pass

    def _quit_app(self):
        """Fully exit and cancel monitor/card callbacks safely."""
        if threading.current_thread() is not threading.main_thread():
            try:
                self.root.after(0, self._quit_app)
            except tk.TclError:
                pass
            return
        try:
            self._monitor.stop()
        except Exception:
            pass
        for card in list(self._session_cards.values()):
            card.destroy()
        self._session_cards.clear()
        for after_id in (self._panel_resize_after_id, self._animation_after_id):
            if after_id is not None:
                try:
                    self.root.after_cancel(after_id)
                except tk.TclError:
                    pass
        self._panel_resize_after_id = None
        self._animation_after_id = None
        try:
            if self._tray_icon:
                self._tray_icon.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def _restart_app(self):
        """Restart the application — spawn new process, then quit."""
        import sys
        python = sys.executable
        script = os.path.abspath(__file__)
        # Spawn the new process first (detached from parent lifetime)
        try:
            subprocess.Popen(
                [python, script],
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                close_fds=True,
            )
        except Exception:
            pass
        # Then quit — schedule on main thread since we're in pystray's thread
        self.root.after(0, self._quit_app)

    def s(self, v):
        return max(1, round(v * self.scale))

    # ── Build ──
    def build_ui(self):
        s = self.s
        r = self.root

        # Header
        header = tk.Frame(r, bg="#2E1A47", height=s(22))
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Frame(header, height=s(1), bg=C.mauve).pack(side="bottom", fill="x")
        tk.Label(header, text="Agent Launcher & Terminal Themes",
                 bg="#2E1A47", fg=C.sub, font=("Segoe UI", 9)).pack(pady=(s(3), 0))

        # Content
        content = tk.Frame(r, bg=C.base)
        content.pack(fill="both", expand=True, padx=s(6), pady=(s(2), s(2)))

        # ── Directory Card ──
        dir_card = tk.Frame(content, bg=C.card)
        dir_card.pack(fill="both", expand=True, pady=(0, s(2)))

        hdr_frame = tk.Frame(dir_card, bg=C.card)
        hdr_frame.pack(fill="x", padx=s(4), pady=(s(1), 0))
        tk.Label(hdr_frame, text="📂  Working Directory", bg=C.card, fg=C.text,
                 font=("Segoe UI", 10, "bold")).pack(side="left")

        lb_frame = tk.Frame(dir_card, bg=C.listbg)
        lb_frame.pack(fill="both", expand=True, padx=0, pady=(s(1), 0))

        # Flat listbox: no triangles, headers toggle children visibility
        self.dir_list = tk.Listbox(
            lb_frame, bg=C.listbg, fg=C.text,
            selectbackground=C.blue, selectforeground="#000000",
            font=("Cascadia Code", 10), borderwidth=0,
            highlightthickness=0, activestyle="none",
            relief="flat", cursor="hand2",
        )
        self.dir_list.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(lb_frame, orient="vertical", command=self.dir_list.yview)
        sb.pack(side="right", fill="y")
        self.dir_list.config(yscrollcommand=sb.set)

        # Store all entries: (label, path, parent_name or "")
        self._all_dirs = []
        self._expanded = {}  # parent_name -> bool
        self._dir_map = {}   # listbox idx -> (label, path)
        current_parent = ""
        for label, path, flag in self.dirs:
            if flag == "PARENT":
                current_parent = label.lstrip("▸  ")
                self._expanded[current_parent] = False
                self._all_dirs.append((label, path, ""))
            else:
                self._all_dirs.append((label, path, current_parent if current_parent else ""))
        current_parent = ""

        self._refresh_list()

        self.dir_list.bind("<Double-Button-1>", lambda e: self.on_launch())
        self.dir_list.bind("<Return>", lambda e: self.on_launch())
        self.dir_list.bind("<Button-1>", self._on_list_click)

        # ── Background Card ──
        bg_card = tk.Frame(content, bg=C.card)
        bg_card.pack(fill="x", pady=(0, s(2)))

        tk.Label(bg_card, text="🎨  Background Mode", bg=C.card, fg=C.text,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=s(8), pady=(s(2), s(2)))
        tk.Frame(bg_card, height=1, bg=C.border).pack(fill="x", padx=s(8))

        self.mode_var = tk.StringVar(value="none")
        modes = [
            ("acrylic", "🪟  Acrylic — frosted glass"),
            ("opacity", "🔲  Opacity — pure transparent"),
            ("none",    "⬛  None — solid color"),
        ]
        for val, txt in modes:
            tk.Radiobutton(bg_card, text=txt, value=val, variable=self.mode_var,
                           command=self.on_mode_change, bg=C.card, fg=C.text,
                           selectcolor=C.card, activebackground=C.card,
                           activeforeground=C.blue, font=("Segoe UI", 10),
                           anchor="w", padx=s(6), pady=0, cursor="hand2",
                           ).pack(fill="x")

        sf = tk.Frame(bg_card, bg=C.card)
        sf.pack(fill="x", padx=s(8), pady=(s(1), s(3)))
        tk.Label(sf, text="🔆", bg=C.card, font=("Segoe UI", 11)).pack(side="left", padx=(0, s(4)))
        self.opacity_var = tk.IntVar(value=50)
        self.opacity_scale = ttk.Scale(
            sf, from_=0, to=100, variable=self.opacity_var,
            orient="horizontal", command=self.on_slider_change)
        style = ttk.Style()
        style.configure("TScale", background=C.card, troughcolor=C.border)
        self.opacity_scale.pack(side="left", fill="x", expand=True, padx=(0, s(8)))
        self.opacity_label = tk.Label(
            sf, text="50%", bg=C.card, fg=C.text,
            font=("Segoe UI", 10, "bold"), width=4, anchor="e")
        self.opacity_label.pack(side="right")

        # ── Buttons ──
        btn_area = tk.Frame(content, bg=C.base)
        btn_area.pack(fill="x", pady=(s(0), s(0)))

        # Use grid with uniform columns → truly equal width buttons
        btn_area.grid_columnconfigure(0, weight=1, uniform="btn")
        btn_area.grid_columnconfigure(1, weight=1, uniform="btn")

        self._launch_btn = NeonButton(
            btn_area, "🚀  Claude Code",
            bg="#35B368", glow="#50FA7B",
            command=self.on_launch, font=("Segoe UI", 12, "bold"))
        self._launch_btn.configure(height=s(32))
        self._launch_btn.grid(row=0, column=0, sticky="ew", padx=(0, s(4)))

        self._hermes_btn = NeonButton(
            btn_area, "🤖  Hermes",
            bg="#E89050", glow="#FFB86C",
            command=self.on_launch_hermes, font=("Segoe UI", 12, "bold"))
        self._hermes_btn.configure(height=s(32))
        self._hermes_btn.grid(row=0, column=1, sticky="ew")

        # Row 2: save button, full width
        self._save_btn = NeonButton(
            btn_area, "💾  Save Background",
            bg="#4A6DB8", glow="#89B4FA",
            command=self.on_save_background, font=("Segoe UI", 12, "bold"))
        self._save_btn.configure(height=s(32))
        self._save_btn.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(s(1), 0))

        # Status
        self.status_var = tk.StringVar(value="Lorien_Lab")
        tk.Label(content, textvariable=self.status_var, bg=C.base, fg=C.subtle,
                 font=("Segoe UI", 9)).pack(pady=(s(2), 0))

    # ── Logic ──
    def load_current_settings(self):
        mode, value = get_current_mode()
        self.mode_var.set(mode)
        self.opacity_var.set(value)
        self.opacity_label.config(text=f"{value}%")
        self._update_slider_state()

    def _update_slider_state(self):
        if self.mode_var.get() == "none":
            self.opacity_scale.config(state="disabled")
            self.opacity_label.config(fg=C.subtle)
        else:
            self.opacity_scale.config(state="normal")
            self.opacity_label.config(fg=C.text)

    def on_mode_change(self):
        self._update_slider_state()

    def on_slider_change(self, val):
        self.opacity_label.config(text=f"{int(float(val))}%")

    def on_save_background(self):
        mode = self.mode_var.get()
        value = self.opacity_var.get()
        apply_background(mode, value)
        self.status_var.set(f"✓  Saved: {mode} at {value}%")
        self.root.after(3000, lambda: self.status_var.set("Lorien_Lab"))

    def _refresh_list(self):
        """Rebuild listbox based on current expand state."""
        self.dir_list.delete(0, tk.END)
        self._dir_map.clear()
        lidx = 0
        for label, path, parent in self._all_dirs:
            if parent and not self._expanded.get(parent, False):
                continue
            # Flip arrow for headers
            if label.startswith("▸"):
                name = label[3:]
                arrow = "▾" if self._expanded.get(name, False) else "▸"
                display = f" {arrow}  {name}"
            else:
                display = label
            self.dir_list.insert(tk.END, display)
            if display.strip().startswith(("▸", "▾")):
                self.dir_list.itemconfig(lidx, fg=C.mauve)
            self._dir_map[lidx] = (label, path)
            lidx += 1

    def _on_list_click(self, event):
        """Toggle expand on parent header click; select non-header items."""
        idx = self.dir_list.nearest(event.y)
        if idx < 0 or idx not in self._dir_map:
            return
        label, path = self._dir_map[idx]
        if label.strip().startswith(("▸", "▾")):
            name = label.strip()[3:]  # strip arrow + spaces
            self._expanded[name] = not self._expanded.get(name, False)
            self._refresh_list()
        else:
            # Explicitly select the clicked directory item.
            # The custom <Button-1> binding can prevent Tk's default
            # class binding from selecting — do it ourselves.
            self.dir_list.selection_clear(0, tk.END)
            self.dir_list.selection_set(idx)
            self.dir_list.activate(idx)

    def _get_selected(self):
        sel = self.dir_list.curselection()
        if not sel:
            return None
        idx = sel[0]
        data = self._dir_map.get(idx)
        if data:
            return data  # (label, path)
        return None

    def on_launch(self):
        pair = self._get_selected()
        if not pair:
            self.status_var.set("⚠  Please select a directory first")
            return
        label, path = pair
        name = label.strip().lstrip("🏠📁  ")
        if launch_claude(path):
            self.status_var.set(f"✓  Claude Code launched: {name}")
            self.root.after(5000, lambda: self.status_var.set("Lorien_Lab"))
        else:
            self.status_var.set("✗  Failed to launch")

    def on_launch_hermes(self):
        pair = self._get_selected()
        if not pair:
            self.status_var.set("⚠  Please select a directory first")
            return
        label, path = pair
        name = label.strip().lstrip("🏠📁  ")
        if launch_hermes(path):
            self.status_var.set(f"✓  Hermes launched: {name}")
            self.root.after(5000, lambda: self.status_var.set("Lorien_Lab"))
        else:
            self.status_var.set("✗  Failed to launch")


def main():
    root = tk.Tk()
    TerminalManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()
