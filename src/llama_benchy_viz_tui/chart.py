"""Unicode line-chart and sparkline helpers.

Hero chart: each terminal cell is a 2x4 Braille sub-pixel grid. Lines are
drawn between consecutive samples with Bresenham, then each cell becomes a
single Braille character (U+2800 + dot mask). When two streams share a
cell, dots OR together and the dominant color (most bits) wins.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from rich.text import Text

# Sparkline density blocks (cell-resolution).
_DENSITY = "▁▂▃▄▅▆▇█"

# Braille bit layout per sub-pixel within a cell (top→bottom, left/right):
#
#   0x01  0x08    row 0
#   0x02  0x10    row 1
#   0x04  0x20    row 2
#   0x40  0x80    row 3
#
_BRAILLE_BITS: List[List[int]] = [
    [0x01, 0x08],
    [0x02, 0x10],
    [0x04, 0x20],
    [0x40, 0x80],
]
_BRAILLE_BASE = 0x2800


def render_sparkline(values: Sequence[float], color: str, width: int = 16) -> Text:
    """Small sparkline using density blocks. One char per data point."""
    if not values:
        return Text(" " * width, style=color)
    vmax = max(values) or 1.0
    vmin = min(values)
    span = max(vmax - vmin, 1e-6)
    sample: List[float] = list(values)[-width:]
    while len(sample) < width:
        sample.insert(0, sample[0])
    out = Text()
    for v in sample:
        norm = (v - vmin) / span
        idx = max(0, min(len(_DENSITY) - 1, int(norm * (len(_DENSITY) - 1))))
        out.append(_DENSITY[idx], style=color)
    return out


def render_chart(
    series: List[Tuple[str, str, List[Tuple[float, float]]]],
    *,
    width: int,
    height: int,
    history_seconds: float,
    now: float,
    y_max: Optional[float] = None,
    show_xaxis: bool = True,
    show_legend: bool = True,
) -> Text:
    """Render the hero performance chart.

    series: [(label, color_hex, history)] where history = [(t, v), …].
    width/height: total cells available, including y-axis labels and right badges.
    history_seconds: rolling window length the chart shows.
    now: right-edge "now" timestamp (in the same time space as the history).
    """
    width = max(20, width)
    height = max(7, height)

    yaxis_cols = 6
    right_cols = 9
    plot_cols = max(10, width - yaxis_cols - right_cols)
    plot_rows = max(3, height - (1 if show_xaxis else 0) - (1 if show_legend else 0))

    sub_w = plot_cols * 2
    sub_h = plot_rows * 4

    t_min = max(0.0, now - history_seconds)
    all_vals: List[float] = []
    last_vals: List[Optional[float]] = []
    for _, _, hist in series:
        windowed = [v for (t, v) in hist if t >= t_min]
        all_vals.extend(windowed)
        last_vals.append(windowed[-1] if windowed else (hist[-1][1] if hist else None))

    # Use caller-provided ratcheted y_max when available, else fall back to
    # a per-frame computation. The caller path keeps the axis stable across
    # ticks so the line doesn't visually jump as data evolves.
    if y_max is not None and y_max > 0:
        scale_max = max(y_max * 1.15, 5.0)
    else:
        scale_max = max(max(all_vals) if all_vals else 30.0, 5.0) * 1.15
    y_max = scale_max
    y_min = 0.0

    def _sub_x(t: float) -> int:
        if now - t_min <= 0:
            return sub_w - 1
        norm = (t - t_min) / (now - t_min)
        norm = max(0.0, min(1.0, norm))
        return int(round(norm * (sub_w - 1)))

    def _sub_y(v: float) -> int:
        if y_max <= y_min:
            return sub_h - 1
        norm = (v - y_min) / (y_max - y_min)
        norm = max(0.0, min(1.0, norm))
        return int(round((1.0 - norm) * (sub_h - 1)))

    cell_bits: Dict[Tuple[int, int], Dict[str, int]] = {}

    def _set_dot(sub_x: int, sub_y: int, color: str) -> None:
        if sub_x < 0 or sub_x >= sub_w or sub_y < 0 or sub_y >= sub_h:
            return
        cell_x = sub_x // 2
        cell_y = sub_y // 4
        bit = _BRAILLE_BITS[sub_y % 4][sub_x % 2]
        bucket = cell_bits.setdefault((cell_x, cell_y), {})
        bucket[color] = bucket.get(color, 0) | bit

    grid_color = "grey23"
    for r_frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        sy = int(round(r_frac * (sub_h - 1)))
        for sx in range(0, sub_w, 4):
            _set_dot(sx, sy, grid_color)

    for label, color, hist in series:
        windowed = [(t, v) for (t, v) in hist if t >= t_min]
        if not windowed:
            continue
        prev: Optional[Tuple[int, int]] = None
        for t, v in windowed:
            sx = _sub_x(t)
            sy = _sub_y(v)
            if prev is None:
                _set_dot(sx, sy, color)
            else:
                for px, py in _bresenham(prev[0], prev[1], sx, sy):
                    _set_dot(px, py, color)
            prev = (sx, sy)

    out = Text()
    y_labels = _yaxis_labels(y_min, y_max, plot_rows)
    for cy in range(plot_rows):
        out.append(f"{y_labels[cy]:>5} ", style="grey50")
        for cx in range(plot_cols):
            bucket = cell_bits.get((cx, cy))
            if not bucket:
                out.append(" ")
                continue
            combined = 0
            best_color = grid_color
            best_pop = -1
            for color, pattern in bucket.items():
                combined |= pattern
                if color == grid_color:
                    continue
                pop = bin(pattern).count("1")
                if pop > best_pop:
                    best_pop = pop
                    best_color = color
            ch = chr(_BRAILLE_BASE + combined) if combined else " "
            out.append(ch, style=best_color)

        # Right-edge live value badge
        badge_drawn = False
        for (label, color, _hist), last in zip(series, last_vals):
            if last is None:
                continue
            badge_row = max(0, min(plot_rows - 1, int(round(_sub_y(last) / 4))))
            if badge_row == cy:
                out.append(f" {last:>4.1f}", style=f"black on {color}")
                badge_drawn = True
                break
        if not badge_drawn:
            out.append(" " * right_cols, style="default")
        out.append("\n")

    if show_xaxis:
        out.append(" " * yaxis_cols, style="default")
        ticks_text = ""
        for tick_frac, tick_label in [
            (0.0, f"-{int(history_seconds)}s"),
            (0.25, f"-{int(history_seconds * 0.75)}s"),
            (0.5, f"-{int(history_seconds * 0.5)}s"),
            (0.75, f"-{int(history_seconds * 0.25)}s"),
            (1.0, "NOW"),
        ]:
            pos = int(tick_frac * (plot_cols - 1))
            while len(ticks_text) < pos:
                ticks_text += " "
            ticks_text = ticks_text[:pos] + tick_label + ticks_text[pos + len(tick_label):]
        ticks_text = ticks_text[:plot_cols].ljust(plot_cols)
        out.append(ticks_text, style="grey50")
        out.append("\n")

    if show_legend:
        out.append(" " * yaxis_cols)
        for label, color, _ in series:
            out.append("● ", style=color)
            out.append(f"{label}  ", style="white")
        out.append("\n")

    return out


def _bresenham(x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
    pts: List[Tuple[int, int]] = []
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            return pts
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def _yaxis_labels(y_min: float, y_max: float, rows: int) -> List[str]:
    labels = []
    for r in range(rows):
        frac = 1.0 - (r / max(rows - 1, 1))
        v = y_min + frac * (y_max - y_min)
        labels.append(f"{v:5.0f}")
    return labels
