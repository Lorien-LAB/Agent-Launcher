"""
Agent Launcher - UI for Claude Code, Hermes & Terminal customization
"""
import ctypes
import json
import math
import os
import subprocess
import tempfile
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
BASE_DIRS = [r"D:\Quantitative Trading", r"D:\University\Kaggle"]
HOME_DIR = os.path.expanduser("~")
CLAUDE_PATH = "C:/Users/Lorien/.local/bin/claude.exe"
CLAUDE_ARGS = "--dangerously-skip-permissions"
HERMES_PATH = "C:/Users/Lorien/AppData/Local/hermes/hermes-agent/venv/Scripts/hermes.exe"


# ─── Colors ──────────────────────────────────────────
class C:
    base    = "#1E1E2E"
    card    = "#181825"
    listbg  = "#313244"
    border  = "#45475A"
    subtle  = "#585B70"
    text    = "#CDD6F4"
    sub     = "#A6ADC8"
    blue    = "#89B4FA"
    green   = "#A6E3A1"
    yellow  = "#F9E2AF"
    mauve   = "#CBA6F7"


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


def launch_in_terminal(dir_path, exe_path, args, title):
    """Generic launcher: write ps1 and open in Windows Terminal."""
    if not os.path.isdir(dir_path):
        return False
    ps = f"cd '{dir_path}'; & '{exe_path}' {args}"
    try:
        fd, tp = tempfile.mkstemp(suffix='.ps1', prefix='launch_')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(ps)
        subprocess.Popen(
            ["wt", "--title", title, "pwsh", "-NoExit", "-File", tp],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        def _clean():
            time.sleep(3)
            try: os.unlink(tp)
            except OSError: pass
        threading.Thread(target=_clean, daemon=True).start()
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

        # ── System Tray ──
        self._tray = None
        self._tray_icon = None
        self._monitor = SessionMonitor()
        self._monitor.on_update(self._on_stats_update)
        self._monitor.scan()  # initial scan
        self._monitor.start()
        self._stats_panel = None  # persistent stats panel
        self._animation_phase = 0  # 0.0 → 1.0 cycling for busy pulse
        self._animating = False
        self._last_statuses = {}  # session_id → old status for transition detection
        self._created_sessions = set()  # sessions that just appeared
        self._create_stats_panel()
        self.root.protocol("WM_DELETE_WINDOW", self._hide_to_tray)
        self.root.after(100, self._create_tray)
        self.root.after(200, self._animate_loop)

    def _create_stats_panel(self):
        """Create a persistent floating stats panel near the taskbar."""
        s = self.s
        panel = tk.Toplevel(self.root)
        panel.title("Session Monitor")
        panel.configure(bg=C.base)
        panel.overrideredirect(True)  # borderless
        panel.attributes("-topmost", True)  # always on top
        panel.attributes("-alpha", 0.92)

        # Position: bottom-right of screen
        sw = panel.winfo_screenwidth()
        sh = panel.winfo_screenheight()
        pw, ph = s(420), s(350)
        panel.geometry(f"{pw}x{ph}+{sw - pw - s(10)}+{sh - ph - s(60)}")

        # Make draggable
        self._drag_x, self._drag_y = 0, 0
        panel.bind("<Button-1>", self._panel_drag_start)
        panel.bind("<B1-Motion>", self._panel_drag_move)

        # Header
        hdr = tk.Frame(panel, bg="#2E1A47", height=s(26))
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Frame(hdr, height=s(1), bg=C.mauve).pack(side="bottom", fill="x")
        self._panel_title = tk.Label(
            hdr, text="📊  Session Monitor",
            bg="#2E1A47", fg=C.text, font=("Segoe UI", 10, "bold"))
        self._panel_title.pack(pady=(s(3), 0))

        # Body — scrollable frame
        body = tk.Frame(panel, bg=C.base)
        body.pack(fill="both", expand=True, padx=s(4), pady=s(4))
        self._panel_body = body

        self._stats_panel = panel

    def _panel_drag_start(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _panel_drag_move(self, event):
        x = self._stats_panel.winfo_x() + event.x - self._drag_x
        y = self._stats_panel.winfo_y() + event.y - self._drag_y
        self._stats_panel.geometry(f"+{x}+{y}")

    def _on_stats_update(self, stats):
        """Called by monitor thread → schedule UI update in main thread."""
        self._stats = stats
        self.root.after(0, lambda: [self._update_tray(stats), self._update_panel(stats)])

    def _animate_loop(self):
        """Only update colors of existing animated labels — no widget destruction."""
        self._animation_phase = (self._animation_phase + 0.08) % (2 * math.pi)
        phase = self._animation_phase

        for group in getattr(self, '_wave_labels', []):
            for i, (label, base_color, offset) in enumerate(group):
                try:
                    color = self._pulse_color(base_color, phase - i * offset)
                    label.config(fg=color)
                except tk.TclError:
                    pass

        # Also pulse status dots for busy rows
        for dot_label, base_color, offset in getattr(self, '_dot_labels', []):
            try:
                color = self._pulse_color(base_color, phase - offset)
                dot_label.config(fg=color)
            except tk.TclError:
                pass

        self.root.after(120, self._animate_loop)

    @staticmethod
    def _pulse_color(base_hex, phase):
        """Return a color that pulses between dim and near-white."""
        r = int(base_hex[1:3], 16)
        g = int(base_hex[3:5], 16)
        b = int(base_hex[5:7], 16)
        # Sine wave 0→1→0, squared for sharper peak, scaled to 0→170
        intensity = math.sin(phase) ** 2
        boost = int(170 * intensity)
        r = min(255, r + boost)
        g = min(255, g + boost)
        b = min(255, b + boost)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _update_panel(self, stats):
        try:
            if not self._stats_panel: return
            self._stats_panel.winfo_exists()
        except tk.TclError: return
        s = self.s
        body = self._panel_body
        for w in body.winfo_children(): w.destroy()
        self._wave_labels = []; self._dot_labels = []
        phase = self._animation_phase

        # Header
        t = f"{_fmt_tokens(stats.total_input)} in  {_fmt_tokens(stats.total_output)} out"
        c = _fmt_cost(stats.total_cost) if stats.total_cost > 0.001 else ""
        if c: t += f"       {c}"
        tk.Label(body, text=t, bg=C.base, fg=C.text, font=("Consolas",10)).grid(row=0,column=0,columnspan=2,sticky="w",pady=(s(2),s(4)))
        tk.Frame(body, height=1, bg=C.border).grid(row=1,column=0,columnspan=2,sticky="ew",pady=s(2))

        # Transitions
        cur = {se.session_id: se.status for se in stats.sessions}
        for sid,st in cur.items():
            pv = self._last_statuses.get(sid)
            if pv == "busy" and st == "idle": self._created_sessions.add(sid)
        self._last_statuses = cur
        tc = [si for si in list(self._created_sessions) if cur.get(si) != "busy"]
        if tc:
            def _cl(): [self._created_sessions.discard(x) for x in tc]; self.root.after(0,lambda: self._update_panel(self._stats) if self._stats else None)
            self.root.after(5000, _cl)

        row = 2
        for se in stats.sessions[:12]:
            if se.status == "busy": ic,dc="●", self._pulse_color(C.green, phase+row*0.3)
            elif se.session_id in self._created_sessions: ic,dc="✦",C.yellow
            else: ic,dc="○", C.subtle
            dl=tk.Label(body,text=ic,bg=C.base,fg=dc,font=("Segoe UI",10,"bold"))
            dl.grid(row=row,column=0,sticky="nw")
            if se.status=="busy": self._dot_labels.append((dl,C.green,row*0.3))

            info=tk.Frame(body,bg=C.base)
            info.grid(row=row,column=1,sticky="ew",padx=(s(4),s(4)))
            l1=tk.Frame(info,bg=C.base); l1.pack(fill="x")

            if se.status=="busy":
                gr=[]
                for ci,ch in enumerate(se.short_dir):
                    co=self._pulse_color(C.text,phase-ci*0.35)
                    lb=tk.Label(l1,text=ch,bg=C.base,fg=co,font=("Consolas",9,"bold"))
                    lb.pack(side="left"); gr.append((lb,C.text,0.35))
                self._wave_labels.append(gr)
            else:
                tk.Label(l1,text=se.short_dir,bg=C.base,fg=C.text,font=("Consolas",9)).pack(side="left")

            if se.model and se.model!="?":
                ms=se.model.replace("deepseek-v4-pro","DSv4").replace("claude-","")
                tk.Label(l1,text=f" [{ms}]",bg=C.base,fg=C.subtle,font=("Consolas",7)).pack(side="left",padx=(s(4),0))
            if se.git_branch:
                tk.Label(l1,text=f" {se.git_branch}",bg=C.base,fg=C.subtle,font=("Consolas",7)).pack(side="left",padx=(s(2),0))
            if se.subagent_count>0:
                tk.Label(l1,text=f" [{se.subagent_count}]",bg=C.base,fg=C.mauve,font=("Consolas",7)).pack(side="left",padx=(s(2),0))

            if se.status=="busy":
                tk.Label(l1,text="  ",bg=C.base).pack(side="left")
                for ci,ch in enumerate("RUNNING"):
                    co=self._pulse_color(C.green,phase-ci*0.4)
                    lb=tk.Label(l1,text=ch,bg=C.base,fg=co,font=("Consolas",8,"bold"))
                    lb.pack(side="left"); gr.append((lb,C.green,0.4))
            elif se.session_id in self._created_sessions:
                tk.Label(l1,text="  ",bg=C.base).pack(side="left")
                for ci,ch in enumerate("DONE"):
                    co=self._pulse_color(C.yellow,phase-ci*0.35)
                    tk.Label(l1,text=ch,bg=C.base,fg=co,font=("Consolas",8,"bold")).pack(side="left")

            l2=tk.Frame(info,bg=C.base); l2.pack(fill="x")
            pct=se.context_pct
            bc=C.mauve if pct>80 else (C.yellow if pct>60 else C.blue)
            bw,bh=s(200),s(3)
            bar=tk.Canvas(l2,width=bw,height=bh,bg=C.base,highlightthickness=0)
            bar.create_rectangle(0,0,bw,bh,fill=C.listbg,outline="")
            fw=max(2,int(bw*pct/100))
            bar.create_rectangle(0,0,fw,bh,fill=bc,outline="")
            bar.pack(side="left",padx=(0,s(4)))
            cs=f"{pct:.1f}%"
            tk.Label(l2,text=f"{cs}  {_fmt_tokens(se.input_tokens)} in",bg=C.base,fg=C.sub,font=("Consolas",7)).pack(side="left")
            row+=1

        if not stats.sessions:
            tk.Label(body,text="No active sessions",bg=C.base,fg=C.subtle,font=("Segoe UI",9)).grid(row=3,column=0,columnspan=2)
        body.grid_columnconfigure(1,weight=1)

        # Resize
        h=max(80, s(28+max(len(stats.sessions),1)*24))
        try: self._stats_panel.geometry(f"{s(400)}x{h}")
        except tk.TclError: pass

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

    def _quit_app(self):
        """Fully exit the application."""
        try:
            if self._tray_icon:
                self._tray_icon.stop()
        except Exception:
            pass
        self.root.destroy()

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
        """Toggle expand on parent header click."""
        idx = self.dir_list.nearest(event.y)
        if idx < 0 or idx not in self._dir_map:
            return
        label, path = self._dir_map[idx]
        if label.strip().startswith(("▸", "▾")):
            name = label.strip()[3:]  # strip arrow + spaces
            self._expanded[name] = not self._expanded.get(name, False)
            self._refresh_list()

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
