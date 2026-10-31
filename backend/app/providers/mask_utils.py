"""Mask geometry helpers shared by fixtures, crops and evaluation."""

from __future__ import annotations


def raster_to_svg_path(bits: list[int], width: int, height: int) -> str:
    """Exact SVG path for a row-major 0/1 raster: one rectangle per horizontal run.

    Vertically adjacent identical runs are merged to keep the path compact.
    """
    rects: list[list[int]] = []  # [x, y, w, h]
    open_runs: dict[tuple[int, int], list[int]] = {}
    for y in range(height):
        row = bits[y * width:(y + 1) * width]
        runs, x = [], 0
        while x < width:
            if row[x]:
                start = x
                while x < width and row[x]:
                    x += 1
                runs.append((start, x - start))
            else:
                x += 1
        next_open: dict[tuple[int, int], list[int]] = {}
        for run in runs:
            if run in open_runs:
                rect = open_runs[run]
                rect[3] += 1
            else:
                rect = [run[0], y, run[1], 1]
                rects.append(rect)
            next_open[run] = rect
        open_runs = next_open
    return "".join(f"M{x} {y}h{w}v{h}h{-w}z" for x, y, w, h in rects)


def iou(bits_a: list[int], bounds_a: tuple[int, int, int, int], bits_b: list[int],
        bounds_b: tuple[int, int, int, int]) -> float:
    """IoU of two masks given as rasters aligned 1:1 to their (half-open) bounds."""
    def pixels(bits: list[int], bounds: tuple[int, int, int, int]) -> set[tuple[int, int]]:
        x1, y1, x2, _ = bounds
        w = x2 - x1
        return {(x1 + i % w, y1 + i // w) for i, v in enumerate(bits) if v}

    a, b = pixels(bits_a, bounds_a), pixels(bits_b, bounds_b)
    union = len(a | b)
    return len(a & b) / union if union else 0.0
