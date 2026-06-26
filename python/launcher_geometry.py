from __future__ import annotations


def stable_rounded_rectangle_points(x1, y1, x2, y2, radius):
    left = int(round(x1))
    top = int(round(y1))
    right = int(round(x2))
    bottom = int(round(y2))
    radius = max(
        0,
        min(
            int(round(radius)),
            max(0, (right - left) // 2),
            max(0, (bottom - top) // 2),
        ),
    )
    return [
        left + radius, top,
        left + radius, top,
        right - radius, top,
        right - radius, top,
        right, top,
        right, top + radius,
        right, top + radius,
        right, bottom - radius,
        right, bottom - radius,
        right, bottom,
        right - radius, bottom,
        right - radius, bottom,
        left + radius, bottom,
        left + radius, bottom,
        left, bottom,
        left, bottom - radius,
        left, bottom - radius,
        left, top + radius,
        left, top + radius,
        left, top,
    ]
