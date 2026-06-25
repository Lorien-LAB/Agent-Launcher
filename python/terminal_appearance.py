from __future__ import annotations

from collections.abc import Callable

from launcher_state import AppearanceSettings


class TerminalAppearanceController:
    """Manage preview/apply/cancel semantics for Terminal appearance changes."""

    def __init__(
        self,
        reader: Callable[[], AppearanceSettings],
        writer: Callable[[AppearanceSettings], None],
        persist: Callable[[AppearanceSettings], None],
        logger=None,
    ):
        self.reader = reader
        self.writer = writer
        self.persist = persist
        self.logger = logger
        self.applied_settings = self.reader()
        self.preview_settings = self.applied_settings
        self.is_dirty = False

    def reload(self) -> AppearanceSettings:
        self.applied_settings = self.reader()
        self.preview_settings = self.applied_settings
        self.is_dirty = False
        return self.applied_settings

    def preview(self, settings: AppearanceSettings) -> None:
        if settings == self.preview_settings:
            return
        self.writer(settings)
        self.preview_settings = settings
        self.is_dirty = settings != self.applied_settings
        if self.logger:
            self.logger.info(
                "terminal appearance preview mode=%s opacity=%s",
                settings.mode,
                settings.opacity,
            )

    def apply(self) -> AppearanceSettings:
        if self.preview_settings != self.applied_settings:
            self.persist(self.preview_settings)
            self.applied_settings = self.preview_settings
        self.is_dirty = False
        if self.logger:
            self.logger.info(
                "terminal appearance applied mode=%s opacity=%s",
                self.applied_settings.mode,
                self.applied_settings.opacity,
            )
        return self.applied_settings

    def cancel(self) -> AppearanceSettings:
        if self.is_dirty:
            self.writer(self.applied_settings)
            if self.logger:
                self.logger.info(
                    "terminal appearance rolled back mode=%s opacity=%s",
                    self.applied_settings.mode,
                    self.applied_settings.opacity,
                )
        self.preview_settings = self.applied_settings
        self.is_dirty = False
        return self.applied_settings
