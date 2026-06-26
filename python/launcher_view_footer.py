from __future__ import annotations

from launcher_branding import GlassBrandButton
from launcher_surfaces import CleanRoundedCard
from launcher_theme import METRICS


def compact_footer_sections() -> tuple[str, ...]:
    return ("launch_actions",)


def build_footer(view) -> None:
    theme = view.theme
    panel_theme = dict(theme)
    panel_theme["surface_1"] = theme["glass_content"]
    view.compact_footer = CleanRoundedCard(
        view.background,
        theme=theme,
        scale=view.s,
        height=view.s(64),
        radius=METRICS.card_radius,
        padding=10,
    )
    view.compact_footer.grid(
        row=3,
        column=0,
        columnspan=2,
        sticky="ew",
        padx=view.s(12),
        pady=(view.s(8), 0),
    )

    footer = view.compact_footer.content
    footer.grid_columnconfigure(0, weight=1, uniform="compact_launch")
    footer.grid_columnconfigure(1, weight=1, uniform="compact_launch")

    view.compact_claude_button = GlassBrandButton(
        footer,
        role="claude",
        text="Claude Code",
        command=lambda: view._launch("claude"),
        theme=panel_theme,
        scale=view.s,
        width=145,
        height=38,
    )
    view.compact_claude_button.grid(row=0, column=0, sticky="ew", padx=(0, view.s(4)))

    view.compact_hermes_button = GlassBrandButton(
        footer,
        role="hermes",
        text="Hermes",
        command=lambda: view._launch("hermes"),
        theme=panel_theme,
        scale=view.s,
        width=120,
        height=38,
    )
    view.compact_hermes_button.grid(row=0, column=1, sticky="ew", padx=(view.s(4), 0))
