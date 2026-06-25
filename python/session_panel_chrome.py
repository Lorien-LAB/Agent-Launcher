"""Final spacing and collapsed-state label tweaks for Session Monitor."""
from __future__ import annotations


def apply_panel_chrome(core) -> None:
    card_cls = core.SessionCard
    manager_cls = core.TerminalManager
    tk = core.tk
    colors = core.C

    original_card_init = card_cls.__init__
    original_update_snapshot = card_cls.update_snapshot
    original_apply_background = card_cls._apply_background
    original_create_stats_panel = manager_cls._create_stats_panel

    def card_init(self, *args, **kwargs):
        original_card_init(self, *args, **kwargs)

        # Rebuild only the first row. The progress bar remains the second row,
        # and expanded metadata remains managed by session_panel_layout.
        old_name = self._name_label
        old_name.pack_forget()
        self._progress_canvas.pack_forget()

        self._collapsed_header = tk.Frame(
            self._content,
            bg=colors.panel_card,
        )
        self._collapsed_header.pack(fill="x")

        self._name_label = tk.Label(
            self._collapsed_header,
            text="",
            bg=colors.panel_card,
            fg=colors.panel_text,
            font=("Consolas", 10, "bold"),
            anchor="w",
        )
        self._name_label.pack(side="left", fill="x", expand=True)

        self._state_label = tk.Label(
            self._collapsed_header,
            text="IDLE",
            bg=colors.panel_card,
            fg=colors.panel_muted,
            font=("Consolas", 9, "bold"),
            anchor="e",
        )
        self._state_label.pack(side="right", padx=(self.s(4), 0))

        self._progress_canvas.pack(fill="x", pady=(self.s(3), 0))
        try:
            old_name.destroy()
        except tk.TclError:
            pass

        # Rebind the newly created widgets so click and hover work everywhere.
        self._bind_interactions(self._collapsed_header)

    def update_snapshot(self, snapshot, display_state):
        original_update_snapshot(self, snapshot, display_state)
        state_text, state_color, _border = core._status_style(display_state)
        self._state_label.configure(text=state_text, fg=state_color)

    def apply_background(self):
        original_apply_background(self)
        bg = colors.panel_hover if self.hovered else colors.panel_card
        try:
            self._collapsed_header.configure(bg=bg)
            self._state_label.configure(bg=bg)
        except tk.TclError:
            pass

    def create_stats_panel(self):
        original_create_stats_panel(self)

        # Keep inter-card spacing unchanged. Only reduce the empty area around
        # the card stack and the gap below the header divider.
        body_x = self.s(3)
        body_y = self.s(44)
        self._body_y0 = body_y
        self._panel_viewport.place_configure(
            x=body_x,
            y=body_y,
            relwidth=1,
            width=-2 * body_x,
        )

    card_cls.__init__ = card_init
    card_cls.update_snapshot = update_snapshot
    card_cls._apply_background = apply_background
    manager_cls._create_stats_panel = create_stats_panel
