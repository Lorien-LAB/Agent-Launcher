"""Compact visual overrides for the Python Session Monitor.

The launcher, tray, and Windows Terminal behavior stay in
``terminal_manager_core``. This module contains only the card presentation and
panel animation policy so the design can be iterated independently.
"""
from __future__ import annotations

import colorsys
import ctypes
import math
import os
import time

from session_monitor import AggregateStats


ANIMATION_DURATION = 0.18
ANIMATION_FRAME_MS = 16


def _animated_progress_width(target_width: int, phase: float, running: bool) -> int:
    """Return the visible fill width for the current animation frame.

    Running cards use the original sawtooth motion: the whole gradient grows
    from left to right and then restarts. Other states show the true width.
    """
    target = max(0, int(target_width))
    if not running or target == 0:
        return target
    progress = (float(phase) % (2 * math.pi)) / (2 * math.pi)
    return max(1, int(target * progress))


def _pid_is_running(pid: int) -> bool:
    """Return whether a session PID still represents a running process."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return True

    if os.name == "nt":
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if not ctypes.windll.kernel32.GetExitCodeProcess(
                handle, ctypes.byref(exit_code)
            ):
                return False
            return exit_code.value == STILL_ACTIVE
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)

    try:
        os.kill(pid, 0)
        return True
    except (OSError, PermissionError):
        return False


def _session_is_open(snapshot, pid_checker=_pid_is_running) -> bool:
    status = str(getattr(snapshot, "status", "")).lower()
    if status in {"closed", "closing", "terminated", "exited", "dead"}:
        return False
    return pid_checker(getattr(snapshot, "pid", 0))


def _filter_live_stats(stats) -> AggregateStats:
    sessions = [s for s in stats.sessions if _session_is_open(s)]
    return AggregateStats(
        active_count=sum(1 for s in sessions if s.status == "busy"),
        idle_count=sum(1 for s in sessions if s.status == "idle"),
        total_input=sum(s.input_tokens for s in sessions),
        total_output=sum(s.output_tokens for s in sessions),
        total_cost=sum(s.cost_usd for s in sessions),
        sessions=sessions,
    )


def apply_session_panel_overrides(core) -> None:
    """Patch ``terminal_manager_core`` with the compact card presentation."""
    card_cls = core.SessionCard
    manager_cls = core.TerminalManager
    tk = core.tk
    C = core.C

    card_cls.COLLAPSED_H = 56
    card_cls.EXPANDED_H = 80
    card_cls.HEIGHT_TICK_MS = ANIMATION_FRAME_MS

    def compact_init(self, parent, scale, on_activate, on_height_changed,
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
        self._current_h = self.s(self.COLLAPSED_H)
        self._target_h = self._current_h
        self._animation_from_h = self._current_h
        self._animation_started_at = 0.0

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
            x=self.s(11), y=self.s(5), relwidth=1, width=-self.s(22),
        )

        top = tk.Frame(self._content, bg=C.panel_card)
        top.pack(fill="x")
        self._status_canvas = tk.Canvas(
            top, width=self.s(18), height=self.s(18), bg=C.panel_card,
            highlightthickness=0, bd=0,
        )
        self._status_canvas.pack(side="left", padx=(0, self.s(5)))
        self._name_label = tk.Label(
            top, text="", bg=C.panel_card, fg=C.panel_text,
            font=("Consolas", 11, "bold"), anchor="w",
        )
        self._name_label.pack(side="left", fill="x", expand=True)
        self._state_label = tk.Label(
            top, text="IDLE", bg=C.panel_card, fg=C.panel_muted,
            font=("Consolas", 11, "bold"), anchor="e",
        )
        self._state_label.pack(side="right")

        meta = tk.Frame(self._content, bg=C.panel_card)
        meta.pack(fill="x", pady=(self.s(1), 0))
        badges = tk.Frame(meta, bg=C.panel_card)
        badges.pack(side="left", fill="x", expand=True)
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
        self._progress_canvas.pack(fill="x", pady=(self.s(3), 0))
        self._progress_canvas.bind(
            "<Configure>", lambda _e: self._draw_progress(0.0)
        )

        self._details = tk.Frame(self._content, bg=C.panel_card)
        self._details.pack(fill="x", pady=(self.s(6), 0))
        self._token_label = tk.Label(
            self._details, text="", bg=C.panel_card, fg=C.panel_sub,
            font=("Consolas", 9), anchor="w",
        )
        self._token_label.pack(fill="x")

        self._bind_interactions(self.frame)

    def compact_apply_hover(self, hovered):
        self._hover_after_id = None
        if self._destroyed or self.hovered == hovered:
            return
        self.hovered = hovered
        self._animation_from_h = self._current_h
        self._target_h = self.s(
            self.EXPANDED_H if hovered else self.COLLAPSED_H
        )
        self._animation_started_at = time.perf_counter()
        self._apply_background()

        # Expansion reserves panel space once before animation. Collapse shrinks
        # the panel only after the card animation finishes. This avoids resizing
        # the transparent top-level window every 16 ms, which caused ghosting.
        if hovered:
            self.on_height_changed()
        self._start_height_animation()

    def compact_start_height_animation(self):
        if self._height_after_id is not None:
            try:
                self.frame.after_cancel(self._height_after_id)
            except tk.TclError:
                pass
        self._height_after_id = self.frame.after(0, self._tick_height)

    def compact_tick_height(self):
        self._height_after_id = None
        if self._destroyed:
            return
        elapsed = time.perf_counter() - self._animation_started_at
        t = max(0.0, min(1.0, elapsed / ANIMATION_DURATION))
        eased = 1.0 - (1.0 - t) ** 3
        next_height = round(
            self._animation_from_h
            + (self._target_h - self._animation_from_h) * eased
        )
        if next_height != self._current_h:
            self._current_h = next_height
            try:
                self.frame.configure(height=self._current_h)
                self._draw_all(0.0)
            except tk.TclError:
                return

        if t < 1.0:
            self._height_after_id = self.frame.after(
                ANIMATION_FRAME_MS, self._tick_height
            )
            return

        self._current_h = self._target_h
        try:
            self.frame.configure(height=self._current_h)
            self._draw_all(0.0)
        except tk.TclError:
            return
        if not self.hovered:
            self.on_height_changed()

    def compact_update_snapshot(self, snapshot, display_state):
        if self._destroyed:
            return
        self.snapshot = snapshot
        self.session_id = snapshot.session_id
        self.display_state = display_state

        name = snapshot.short_dir or snapshot.name or "?"
        if len(name) > 28:
            name = name[:27] + "…"
        self._name_label.configure(text=name)

        state_text, state_color, _border = core._status_style(display_state)
        self._state_label.configure(text=state_text, fg=state_color)

        branch = (snapshot.git_branch or "").strip()
        if branch.lower() in ("main", "master"):
            branch = ""
        agents = f"{snapshot.subagent_count} agents" if snapshot.subagent_count else ""
        self._set_badge(self._branch_badge, branch)
        self._set_badge(self._agent_badge, agents)

        pct = core._clamp_pct(snapshot.context_pct)
        self._pct_label.configure(
            text=f"{pct:.1f}%", fg=core._context_text_color(pct)
        )
        self._token_label.configure(
            text=(f"{core._fmt_tokens(snapshot.input_tokens)} input  ·  "
                  f"{core._fmt_tokens(snapshot.output_tokens)} output  ·  "
                  f"{core._fmt_cost(snapshot.cost_usd)}")
        )
        self._apply_background()
        self._draw_all(0.0)

    def compact_apply_background(self):
        bg = C.panel_hover if self.hovered else C.panel_card
        widgets = [
            self._content, self._name_label, self._state_label,
            self._branch_badge, self._agent_badge, self._pct_label,
            self._progress_canvas, self._details, self._token_label,
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

    @staticmethod
    def pill_background(canvas, width, height, color):
        radius = height / 2
        canvas.create_oval(0, 0, height, height, fill=color, outline="")
        canvas.create_rectangle(
            radius, 0, max(radius, width - radius), height,
            fill=color, outline="",
        )
        canvas.create_oval(
            max(0, width - height), 0, width, height,
            fill=color, outline="",
        )

    @staticmethod
    def gradient_color(position, total_width):
        ratio = max(0.0, min(1.0, position / max(1, total_width)))
        hue = (1.0 - ratio) * 0.33
        red, green, blue = colorsys.hsv_to_rgb(hue, 0.86, 0.96)
        return f"#{int(red * 255):02x}{int(green * 255):02x}{int(blue * 255):02x}"

    def compact_draw_progress(self, phase):
        if self._destroyed or not self.snapshot:
            return
        try:
            canvas = self._progress_canvas
            width = canvas.winfo_width()
            height = max(self.s(5), canvas.winfo_height())
            if width < self.s(20):
                return
            canvas.delete("all")
            pill_background(canvas, width, height, "#282C43")

            pct = core._clamp_pct(self.snapshot.context_pct)
            target_width = core._progress_fill_width(width, pct)
            fill_width = _animated_progress_width(
                target_width, phase, self.display_state == "running"
            )
            if fill_width <= 0:
                return

            if fill_width <= height:
                canvas.create_oval(
                    0, 0, fill_width, height,
                    fill=gradient_color(fill_width / 2, width), outline="",
                )
            else:
                radius = height / 2
                canvas.create_oval(
                    0, 0, height, height,
                    fill=gradient_color(0, width), outline="",
                )
                body_start = radius
                body_end = fill_width - radius
                span = max(0.0, body_end - body_start)
                segments = max(1, min(48, int(span / 4) or 1))
                segment_width = span / segments if segments else 0
                for index in range(segments):
                    x0 = body_start + index * segment_width
                    x1 = body_start + (index + 1) * segment_width + 1
                    canvas.create_rectangle(
                        x0, 0, x1, height,
                        fill=gradient_color((x0 + x1) / 2, width),
                        outline="",
                    )
                canvas.create_oval(
                    fill_width - height, 0, fill_width, height,
                    fill=gradient_color(fill_width, width), outline="",
                )

            if pct >= 95 and fill_width > height / 2:
                pulse = 0.45 + 0.35 * (0.5 + 0.5 * math.sin(phase * 1.3))
                endpoint = core._blend_hex(C.red, "#FFFFFF", pulse)
                radius = height / 2
                canvas.create_oval(
                    fill_width - radius - self.s(1), -self.s(1),
                    fill_width + radius + self.s(1), height + self.s(1),
                    outline=endpoint, width=1,
                )
        except tk.TclError:
            pass

    def compact_animate(self, phase, now):
        del now
        if self._destroyed or not self.snapshot:
            return
        pct = core._clamp_pct(self.snapshot.context_pct)
        if (self.display_state in ("running", "done")
                or self.hovered or pct >= 95):
            self._draw_all(phase)

    def compact_grid_at(self, row):
        if self._destroyed:
            return
        self.frame.grid(
            row=row, column=0, sticky="ew",
            padx=(self.s(1), self.s(1)), pady=(0, self.s(3)),
        )

    def compact_destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        for attr in ("_hover_after_id", "_height_after_id", "_leave_check_id"):
            self._cancel_after(attr)
        try:
            self.frame.destroy()
        except tk.TclError:
            pass

    def compact_resize_stats_panel(self):
        self._panel_resize_after_id = None
        try:
            cards = list(self._session_cards.values())
            body_req = sum(
                card._target_h + self.s(3) for card in cards
            ) if cards else self.s(30)
            width = self.s(core.SESSION_PANEL_WIDTH)
            pad = self._panel_pad
            needed = max(
                self.s(104), self._body_y0 + pad + body_req
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
            self._panel_viewport.configure(
                scrollregion=self._panel_viewport.bbox("all")
            )
            self._panel_h = needed
            if hasattr(self, "_clip_panel"):
                self.root.after(35, self._clip_panel)
        except (AttributeError, tk.TclError):
            pass

    def compact_on_stats_update(self, stats):
        filtered = _filter_live_stats(stats)
        self._stats = filtered
        try:
            self.root.after(
                0,
                lambda: (
                    self._update_tray(filtered),
                    self._update_panel(filtered),
                ),
            )
        except tk.TclError:
            pass

    card_cls.__init__ = compact_init
    card_cls._apply_hover = compact_apply_hover
    card_cls._start_height_animation = compact_start_height_animation
    card_cls._tick_height = compact_tick_height
    card_cls.update_snapshot = compact_update_snapshot
    card_cls._apply_background = compact_apply_background
    card_cls._draw_progress = compact_draw_progress
    card_cls.animate = compact_animate
    card_cls.grid_at = compact_grid_at
    card_cls.destroy = compact_destroy

    manager_cls._resize_stats_panel = compact_resize_stats_panel
    manager_cls._on_stats_update = compact_on_stats_update
