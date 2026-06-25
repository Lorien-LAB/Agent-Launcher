import _bootstrap  # noqa: F401
import unittest

from launcher_animation import (
    WindowAnimator,
    animation_duration,
    clamp_target_size,
    content_opacity,
    ease_out_cubic,
)


class FakeRoot:
    def __init__(self):
        self.callbacks = []
        self.cancelled = []
        self.geometries = []
        self.width = 360
        self.height = 320
        self.x = 25
        self.y = 40

    def winfo_width(self):
        return self.width

    def winfo_height(self):
        return self.height

    def winfo_x(self):
        return self.x

    def winfo_y(self):
        return self.y

    def geometry(self, value):
        self.geometries.append(value)
        size, position = value.split("+", 1)
        width, height = size.split("x")
        x, y = position.split("+")
        self.width = int(width)
        self.height = int(height)
        self.x = int(x)
        self.y = int(y)

    def after(self, _delay, callback):
        token = f"after-{len(self.callbacks)}"
        self.callbacks.append((token, callback))
        return token

    def after_cancel(self, token):
        self.cancelled.append(token)


class LauncherAnimationTests(unittest.TestCase):
    def test_ease_out_cubic_is_monotonic(self):
        values = [ease_out_cubic(index / 20) for index in range(21)]
        self.assertEqual(values[0], 0.0)
        self.assertEqual(values[-1], 1.0)
        self.assertEqual(values, sorted(values))

    def test_target_size_is_clamped_to_work_area(self):
        self.assertEqual(
            clamp_target_size(720, 520, 640, 480, 8),
            (632, 472),
        )

    def test_reduced_motion_uses_zero_duration(self):
        self.assertEqual(0.0, animation_duration(True))
        self.assertEqual(0.22, animation_duration(False))

    def test_content_opacity_delays_expanded_panel(self):
        self.assertEqual(0.0, content_opacity(0.25, expanding=True))
        self.assertGreater(content_opacity(0.75, expanding=True), 0.0)
        self.assertEqual(1.0, content_opacity(1.0, expanding=True))

    def test_animation_keeps_top_left_position_and_ignores_duplicate_start(self):
        root = FakeRoot()
        times = iter([0.0, 0.11, 0.22])
        progress = []
        animator = WindowAnimator(root, now=lambda: next(times))
        started = animator.animate_to(
            720,
            520,
            1920,
            1080,
            on_progress=progress.append,
        )
        duplicate = animator.animate_to(360, 320, 1920, 1080)
        self.assertTrue(started)
        self.assertFalse(duplicate)
        while root.callbacks:
            _token, callback = root.callbacks.pop(0)
            callback()
        self.assertEqual((root.x, root.y), (25, 40))
        self.assertEqual((root.width, root.height), (720, 520))
        self.assertEqual(progress[-1], 1.0)

    def test_reduced_motion_applies_final_geometry_immediately(self):
        root = FakeRoot()
        progress = []
        completed = []
        animator = WindowAnimator(root)
        self.assertTrue(
            animator.animate_to(
                720,
                520,
                1920,
                1080,
                on_progress=progress.append,
                on_complete=lambda: completed.append(True),
                reduced_motion=True,
            )
        )
        self.assertEqual((root.width, root.height), (720, 520))
        self.assertEqual([1.0], progress)
        self.assertEqual([True], completed)
        self.assertFalse(animator.running)

    def test_cancel_prevents_scheduled_geometry_change(self):
        root = FakeRoot()
        animator = WindowAnimator(root, now=lambda: 0.0)
        animator.animate_to(720, 520, 1920, 1080)
        animator.cancel()
        self.assertFalse(animator.running)
        self.assertTrue(root.cancelled)


if __name__ == "__main__":
    unittest.main()
