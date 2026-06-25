"""Second-stage compact layout for the Python Session Monitor."""
from __future__ import annotations


PANEL_WIDTH = 260
COLLAPSED_HEIGHT = 44
EXPANDED_HEIGHT = 82


def _compact_branch(branch: str, limit: int = 14) -> str:
    branch = (branch or "").strip()
    if branch.lower() in {"main", "master"}:
        return ""
    if len(branch) <= limit:
        return branch
    return branch[: limit - 1] + "…"


def apply_compact_layout(core) -> None:
    """Move metadata into hover details and reduce the panel footprint."""
    card_cls = core.SessionCard
    tk = core.tk
    colors = core.C

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
            x=self.s(10),
            y=self.s(4),
            relwidth=1,
            width=-self.s(20),
        )

        top = tk.Frame(self._content, bg=colors.panel_card)
        top.pack(fill="x")

        self._status_canvas = tk.Canvas(
            top,
            width=self.s(16),
            height=self.s(16),
            bg=colors.panel_card,
            highlightthickness=0,
            bd=0,
        )
        self._status_canvas.pack(side="left", padx=(0, self.s(4)))

        self._name_label = tk.Label(
            top,
            text="",
            bg=colors.panel_card,
            fg=colors.panel_text,
            font=("Consolas", 10, "bold"),
            anchor="w",
        )
        self._name_label.pack(side="left", fill="x", expand=True)

        self._state_label = tk.Label(
            top,
            text="IDLE",
            bg=colors.panel_card,
            fg=colors.panel_muted,
            font=("Consolas", 10, "bold"),
            anchor="e",
        )
        self._state_label.pack(side="right")

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

        self._details = tk.Frame(self._content, bg=colors.panel_card)
        self._details.pack(fill="x", pady=(self.s(7), 0))

        details_meta = tk.Frame(self._details, bg=colors.panel_card)
        details_meta.pack(fill="x")

        self._branch_badge = self._make_badge(details_meta, colors.blue)
        self._agent_badge = self._make_badge(details_meta, colors.cyan)

        self._pct_label = tk.Label(
            details_meta,
            text="0.0%",
            bg=colors.panel_card,
            fg=colors.panel_sub,
            font=("Consolas", 8, "bold"),
            anchor="e",
        )
        self._pct_label.pack(side="right")

        self._token_label = tk.Label(
            self._details,
            text="",
            bg=colors.panel_card,
            fg=colors.panel_sub,
            font=("Consolas", 8),
            anchor="w",
        )
        self._token_label.pack(fill="x", pady=(self.s(3), 0))

        self._bind_interactions(self.frame)

    def compact_update_snapshot(self, snapshot, display_state):
        if self._destroyed:
            return

        self.snapshot = snapshot
        self.session_id = snapshot.session_id
        self.display_state = display_state

        name = snapshot.short_dir or snapshot.name or "?"
        if len(name) > 20:
            name = name[:19] + "…"
        self._name_label.configure(text=name)

        state_text, state_color, _border = core._status_style(display_state)
        self._state_label.configure(text=state_text, fg=state_color)

        branch = _compact_branch(snapshot.git_branch)
        agents = (
            f"{snapshot.subagent_count} agents"
            if snapshot.subagent_count
            else ""
        )
        self._set_badge(self._branch_badge, branch)
        self._set_badge(self._agent_badge, agents)

        pct = core._clamp_pct(snapshot.context_pct)
        self._pct_label.configure(
            text=f"{pct:.1f}%",
            fg=core._context_text_color(pct),
        )
        self._token_label.configure(
            text=(
                f"{core._fmt_tokens(snapshot.input_tokens)} in · "
                f"{core._fmt_tokens(snapshot.output_tokens)} out · "
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
            self._state_label,
            self._branch_badge,
            self._agent_badge,
            self._pct_label,
            self._progress_canvas,
            self._details,
            self._token_label,
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

    card_cls.__init__ = compact_init
    card_cls.update_snapshot = compact_update_snapshot
    card_cls._apply_background = compact_apply_background
    card_cls.grid_at = compact_grid_at
