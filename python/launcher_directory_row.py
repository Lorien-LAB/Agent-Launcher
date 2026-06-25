from __future__ import annotations

import os
import tkinter as tk


class DirectoryRowWidget(tk.Frame):
    def __init__(self, master, row, colors, on_select, on_launch, on_favorite):
        super().__init__(master, bg=colors["card"], height=32, cursor="hand2")
        self.pack_propagate(False)
        self.row = row
        self.colors = colors
        self.name_label = tk.Label(
            self,
            text=os.path.basename(row.path) or row.path,
            bg=colors["card"],
            fg=colors["text"],
            anchor="w",
            font=("Segoe UI", 10),
            cursor="hand2",
        )
        self.name_label.pack(side="left", fill="x", expand=True, padx=(8, 4))
        self.star = tk.Label(
            self,
            text="★" if row.favorite else "☆",
            bg=colors["card"],
            fg=colors["accent"],
            width=3,
            cursor="hand2",
            font=("Segoe UI Symbol", 11),
        )
        self.star.pack(side="right")
        for widget in (self, self.name_label):
            widget.bind("<Button-1>", lambda _event, p=row.path: on_select(p))
            widget.bind("<Double-Button-1>", lambda _event: on_launch("claude"))
        self.star.bind("<Button-1>", lambda _event, p=row.path: on_favorite(p))

    def set_selected(self, selected: bool) -> None:
        background = self.colors["selected"] if selected else self.colors["card"]
        self.configure(bg=background)
        self.name_label.configure(bg=background)
        self.star.configure(bg=background)
