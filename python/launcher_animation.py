from __future__ import annotations

import time


ANIMATION_SECONDS = 0.22
FRAME_MS = 16


def ease_out_cubic(value: float) -> float:
    t = max(0.0, min(1.0, float(value)))
    return 1.0 - (1.0 - t) ** 3


def clamp_target_size(
    width: int,
    height: int,
    work_width: int,
    work_height: int,
    margin: int = 8,
) -> tuple[int, int]:
    usable_width = max(1, int(work_width) - int(margin))
    usable_height = max(1, int(work_height) - int(margin))
    return max(1, min(int(width), usable_width)), max(1, min(int(height), usable_height))


class WindowAnimator:
    """Animate Tk geometry while preserving the current top-left anchor."""

    def __init__(self, root, scale=lambda value: value, now=time.perf_counter):
        self.root = root
        self.scale = scale
        self.now = now
        self._after_id = None
        self._running = False
        self._cancelled = False

    @property
    def running(self) -> bool:
        return self._running

    def animate_to(
        self,
        target_width: int,
        target_height: int,
        work_width: int,
        work_height: int,
        on_complete=None,
    ) -> bool:
        if self._running:
            return False
        margin = self.scale(8)
        width, height = clamp_target_size(
            self.scale(target_width),
            self.scale(target_height),
            work_width,
            work_height,
            margin,
        )
        start_width = int(self.root.winfo_width())
        start_height = int(self.root.winfo_height())
        anchor_x = int(self.root.winfo_x())
        anchor_y = int(self.root.winfo_y())
        started_at = self.now()
        self._running = True
        self._cancelled = False

        def tick() -> None:
            self._after_id = None
            if self._cancelled:
                self._running = False
                return
            try:
                elapsed = self.now() - started_at
                progress = min(1.0, max(0.0, elapsed / ANIMATION_SECONDS))
                eased = ease_out_cubic(progress)
                current_width = round(start_width + (width - start_width) * eased)
                current_height = round(start_height + (height - start_height) * eased)
                self.root.geometry(
                    f"{current_width}x{current_height}+{anchor_x}+{anchor_y}"
                )
            except Exception:
                self._running = False
                self._after_id = None
                return
            if progress < 1.0:
                try:
                    self._after_id = self.root.after(FRAME_MS, tick)
                except Exception:
                    self._running = False
                return
            self._running = False
            if on_complete is not None:
                on_complete()

        try:
            self._after_id = self.root.after(0, tick)
        except Exception:
            self._running = False
            return False
        return True

    def cancel(self) -> None:
        self._cancelled = True
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = None
        self._running = False
