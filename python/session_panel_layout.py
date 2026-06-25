"""Ultra-compact layout for the Python Session Monitor."""
from __future__ import annotations

import time


PANEL_WIDTH = 195
COLLAPSED_HEIGHT = 36
EXPANDED_HEIGHT = 78


def _compact_branch(branch: str, limit: int = 12) -> str:
    branch = (branch or "").strip()
    if branch.lower() in {"main", "master"}:
        return ""
    if len(branch) <= limit:
        return branch
    return branch[: limit - 1] + "…"


def apply_compact_layout(core) -> None:
    """Keep collapsed cards to two rows and move metadata into hover details."""
    card_cls = core.SessionCard
    manager_cls = core.TerminalManager
    tk = core.tk
    colors = core.C

    original_create_stats_panel = manager_cls._create_stats_panel

    core.SESSION_PANEL_WIDTH = PANEL_WIDTH
    card_cls.COLLAPSED_H = COLLAPSED_HEIGHT
    card_cls.EXPANDED_H = EXPANDED_HEIGHT

    def compact_init(
        self,
        parent,
        scale,
        on_activate,
        on_height_changed,
        on_hover_request,
        on_mousewheel=None,
    ):
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
        self._details_visible = False

        self.frame = tk.Frame(
            parent,
            bg=colors.panel_bg,
            height=self._current_h,
            highlightthickness=0,
            cursor="hand2",
        )
        self.frame.grid_propagate(False)
        self.frame.grid_columnconfigure(0, weight=1)

        self._card_canvas = tk.Canvas(
            self.frame,
            bg=colors.panel_bg,
            highlightthickness=0,
            bd=0,
        )
        self._card_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._card_canvas.bind(
            "<Configure>", lambda _event: self._draw_card(0.0)
        )

        self._content = tk.Frame(self.frame, bg=colors.panel_card)
        self._content.place(
            x=self.s(9),
            y=self.s(3),
            relwidth=1,
            width=-self.s(18),
        )

        # Collapsed row 1: session name only.
        self._name_label = tk.Label(
            self._content,
            text="",
            bg=colors.panel_card,
            fg=colors.panel_text,
            font=("Consolas", 10, "bold"),
            anchor="w",
        )
        self._name_label.pack(fill="x")

        # Collapsed row 2: context bar only.
        self._progress_canvas = tk.Canvas(
            self._content,
            height=self.s(6),
            bg=colors.panel_card,
            highlightthickness=0,
            bd=0,
        )
        self._progress_canvas.pack(fill="x", pady=(self.s(3), 0))
        self._progress_canvas.bind(
            "<Configure>", lambda _event: self._draw_progress(0.0)
        )

        # Expanded-only details. It is genuinely removed from geometry while
        # collapsed instead of merely being clipped by the card height.
        self._details = tk.Frame(self._content, bg=colors.panel_card)

        first_detail_row = tk.Frame(self._details, bg=colors.panel_card)
        first_detail_row.pack(fill="x")
        self._branch_badge = self._make_badge(first_detail_row, colors.blue)
        self._agent_badge = self._make_badge(first_detail_row, colors.cyan)

        second_detail_row = tk.Frame(self._details, bg=colors.panel_card)
        second_detail_row.pack(fill="x", pady=(self.s(2), 0))
        self._pct_label = tk.Label(
            second_detail_row,
            text="0.0%",
            bg=colors.panel_card,
            fg=colors.panel_sub,
            font=("Consolas", 8, "bold"),
            anchor="w",
        )
        self._pct_label.pack(side="left")
        self._token_label = tk.Label(
            second_detail_row,
            text="",
            bg=colors.panel_card,
            fg=colors.panel_sub,
            font=("Consolas", 8),
            anchor="e",
        )
        self._token_label.pack(side="right")

        self._bind_interactions(self.frame)

    def show_details(self):
        if self._details_visible:
            return
        self._details.pack(fill="x", pady=(self.s(7), 0))
        self._details_visible = True

    def hide_details(self):
        if not self._details_visible:
            return
        self._details.pack_forget()
        self._details_visible = False

    def compact_apply_hover(self, hovered):
        self._hover_after_id = None
        if self._destroyed or self.hovered == hovered:
            return

        self.hovered = hovered
        if hovered:
            self._show_details()

        self._animation_from_h = self._current_h
        self._target_h = self.s(
            self.EXPANDED_H if hovered else self.COLLAPSED_H
        )
        self._animation_started_at = time.perf_counter()
        self._apply_background()

        # Reserve the final panel space once before expansion. The outer panel
        # shrinks only after collapse finishes, avoiding transparent-window trails.
        if hovered:
            self.on_height_changed()
        self._start_height_animation()

    def compact_update_snapshot(self, snapshot, display_state):
        if self._destroyed:
            return

        self.snapshot = snapshot
        self.session_id = snapshot.session_id
        self.display_state = display_state

        name = snapshot.short_dir or snapshot.name or "?"
        if len(name) > 21:
            name = name[:20] + "…"
        self._name_label.configure(text=name)

        branch = _compact_branch(snapshot.git_branch)
        agents = (
            f"{snapshot.subagent_count} agents"
            if snapshot.subagent_count
            else ""
        )
        self._set_badge(self._branch_badge, branch)
        self._set_badge(self._agent_badge, agents)

        pct = core._clamp_pct(snapshot.context_pct)
        state_text, state_color, _border = core._status_style(display_state)
        self._pct_label.configure(
            text=f"{state_text} · {pct:.1f}%",
            fg=state_color if display_state != "idle" else core._context_text_color(pct),
        )
        self._token_label.configure(
            text=(
                f"{core._fmt_tokens(snapshot.input_tokens)}/"
                f"{core._fmt_tokens(snapshot.output_tokens)} · "
                f"{core._fmt_cost(snapshot.cost_usd)}"
            )
        )

        self._apply_background()
        self._draw_all(0.0)

    def compact_apply_background(self):
        bg = colors.panel_hover if self.hovered else colors.panel_card
        widgets = [
            self._content,
            self._name_label,
            self._progress_canvas,
            self._details,
            self._branch_badge,
            self._agent_badge,
            self._pct_label,
            self._token_label,
        ]
        for widget in widgets:
            try:
                widget.configure(bg=bg)
            except tk.TclError:
                pass

        for child in self._details.winfo_children():
            if isinstance(child, tk.Frame):
                child.configure(bg=bg)

    def compact_draw_all(self, phase):
        # There is deliberately no status star in the collapsed card. State is
        # conveyed through the card border and shown as text only after expansion.
        self._draw_card(phase)
        self._draw_progress(phase)

    def compact_on_click(self, _event=None):
        if self.snapshot:
            self.on_activate(self.snapshot)

    def compact_grid_at(self, row):
        if self._destroyed:
            return
        self.frame.grid(
            row=row,
            column=0,
            sticky="ew",
            padx=(self.s(1), self.s(1)),
            pady=(0, self.s(3)),
        )

    def compact_create_stats_panel(self):
        original_create_stats_panel(self)

        # The original viewport started 64 logical pixels below the header,
        # leaving a large gap at high DPI. Move it directly beneath the scan line.
        body_y = self._panel_pad + self.s(48)
        self._body_y0 = body_y
        self._panel_viewport.place_configure(y=body_y)

        # Keep the two header rows readable at 195 logical pixels.
        self._clock_label.configure(font=("Consolas", 9, "bold"))
        self._active_summary.configure(font=("Consolas", 7, "bold"))
        self._idle_summary.configure(font=("Consolas", 7, "bold"))
        self._token_summary.configure(font=("Consolas", 7, "bold"))
        self._idle_summary.pack_configure(padx=(self.s(5), 0))

        try:
            header = self._clock_label.master.master
            for child in header.winfo_children():
                for widget in child.winfo_children():
                    if isinstance(widget, tk.Label) and widget.cget("text") == "SESSION MONITOR":
                        widget.configure(font=("Segoe UI", 9, "bold"))
        except tk.TclError:
            pass

    card_cls.__init__ = compact_init
    card_cls._show_details = show_details
    card_cls._hide_details = hide_details
    card_cls._apply_hover = compact_apply_hover
    card_cls.update_snapshot = compact_update_snapshot
    card_cls._apply_background = compact_apply_background
    card_cls._draw_all = compact_draw_all
    card_cls._on_click = compact_on_click
    card_cls.grid_at = compact_grid_at

    manager_cls._create_stats_panel = compact_create_stats_panel
