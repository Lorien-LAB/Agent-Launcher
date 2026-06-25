"""Dynamic expanded-detail rows for Session Monitor cards."""
from __future__ import annotations


ONE_DETAIL_ROW_HEIGHT = 58
TWO_DETAIL_ROW_HEIGHT = 78


def apply_dynamic_details(core) -> None:
    card_cls = core.SessionCard
    tk = core.tk

    original_init = card_cls.__init__
    original_update_snapshot = card_cls.update_snapshot
    original_apply_hover = card_cls._apply_hover
    original_show_details = card_cls._show_details

    def card_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        rows = list(self._details.winfo_children())
        self._detail_meta_row = rows[0] if len(rows) > 0 else None
        self._detail_value_row = rows[1] if len(rows) > 1 else None
        self._detail_row_count = 0
        self._dynamic_expanded_h = self.COLLAPSED_H

    def refresh_detail_rows(self):
        meta_visible = bool(
            self._branch_badge.cget("text")
            or self._agent_badge.cget("text")
        )
        value_visible = bool(
            self._pct_label.cget("text")
            or self._token_label.cget("text")
        )

        if self._detail_meta_row is not None:
            self._detail_meta_row.pack_forget()
        if self._detail_value_row is not None:
            self._detail_value_row.pack_forget()

        row_count = 0
        if meta_visible and self._detail_meta_row is not None:
            self._detail_meta_row.pack(fill="x")
            row_count += 1
        if value_visible and self._detail_value_row is not None:
            pady = (self.s(2), 0) if row_count else (0, 0)
            self._detail_value_row.pack(fill="x", pady=pady)
            row_count += 1

        self._detail_row_count = row_count
        if row_count <= 0:
            self._dynamic_expanded_h = self.COLLAPSED_H
        elif row_count == 1:
            self._dynamic_expanded_h = ONE_DETAIL_ROW_HEIGHT
        else:
            self._dynamic_expanded_h = TWO_DETAIL_ROW_HEIGHT

        if row_count == 0 and self._details_visible:
            self._details.pack_forget()
            self._details_visible = False

    def update_snapshot(self, snapshot, display_state):
        original_update_snapshot(self, snapshot, display_state)

        pct = core._clamp_pct(snapshot.context_pct)
        self._pct_label.configure(
            text=f"{pct:.1f}%" if pct > 0 else "",
            fg=core._context_text_color(pct),
        )

        token_parts = []
        if snapshot.input_tokens:
            token_parts.append(f"{core._fmt_tokens(snapshot.input_tokens)} in")
        if snapshot.output_tokens:
            token_parts.append(f"{core._fmt_tokens(snapshot.output_tokens)} out")
        if snapshot.cost_usd > 0:
            token_parts.append(core._fmt_cost(snapshot.cost_usd))
        self._token_label.configure(text=" · ".join(token_parts))

        self._refresh_detail_rows()
        if self.hovered:
            self._target_h = self.s(self._dynamic_expanded_h)
            self.on_height_changed()

    def show_details(self):
        self._refresh_detail_rows()
        if self._detail_row_count <= 0:
            return
        original_show_details(self)

    def apply_hover(self, hovered):
        original_apply_hover(self, hovered)
        if hovered:
            self._target_h = self.s(self._dynamic_expanded_h)
            if self._detail_row_count <= 0:
                self._target_h = self.s(self.COLLAPSED_H)
            self.on_height_changed()

    card_cls.__init__ = card_init
    card_cls._refresh_detail_rows = refresh_detail_rows
    card_cls.update_snapshot = update_snapshot
    card_cls._show_details = show_details
    card_cls._apply_hover = apply_hover
