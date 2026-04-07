"""
Gráficas vectoriales del PDF de reportes ejecutivos (área bajo curva + trazo suave).

Este módulo existe aparte de views.py para que un despliegue no pueda quedar a medias
(solo views antiguo sin la lógica de área). REPORTE_PDF_GRAFICAS_BUILD cambia cuando se
actualiza el dibujo; la vista admin_reportes_pdf expone la misma cadena en un header HTTP.
"""

from __future__ import annotations

REPORTE_PDF_GRAFICAS_BUILD = "2026-04-05d-area-densa-curva"

# Paleta alineada con el dashboard (morado marca + secundario)
_REPORTE_LINE_PRIMARY_HEX = "#6f42c1"
_REPORTE_LINE_SECONDARY_HEX = "#007bff"
_REPORTE_CHART_COLORS_HEX = (
    "#6f42c1",
    "#007bff",
    "#e83e8c",
    "#5a32a3",
    "#6610f2",
    "#17a2b8",
    "#fd7e14",
    "#20c997",
)

# Contenedor: lila muy tenue (contrasta con la hoja blanca; no es el relleno del área).
_PLOT_BG_HEX = "#f5f3ff"
_PLOT_STROKE_HEX = "#ede9fe"

# Rejilla sobre el fondo (líneas claras tipo dashboard).
_GRID_LINE_HEX = "#ffffff"

# “Mancha” bajo la curva: solo el polígono curva→eje X (no todo el rectángulo).
_AREA_FILL_TOP_HEX = "#ddd6fe"
_AREA_FILL_DEEP_HEX = "#c4b5fd"


def _hex_to_rgb01(h: str) -> tuple[float, float, float]:
    h = (h or "#000000").lstrip("#")
    if len(h) != 6:
        return (0.2, 0.2, 0.35)
    return tuple(int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def _reporte_label_corta(texto: str, max_len: int = 14) -> str:
    t = (texto or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _format_cop_axis_short(val: float) -> str:
    v = max(0.0, float(val))
    if v >= 1_000_000_000:
        return f"${v / 1_000_000_000:.1f}B"
    if v >= 1_000_000:
        return f"${v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v / 1_000:.0f}k"
    return f"${int(round(v))}"


def _sample_catmull_area_top(xs: list[float], ys: list[float], samples_per_seg: int = 18) -> list[tuple[float, float]]:
    n = len(xs)
    if n < 2:
        return [(xs[0], ys[0])]
    out: list[tuple[float, float]] = []
    for i in range(n - 1):
        x0 = xs[i - 1] if i > 0 else xs[0]
        y0 = ys[i - 1] if i > 0 else ys[0]
        x1, y1 = xs[i], ys[i]
        x2, y2 = xs[i + 1], ys[i + 1]
        x3 = xs[i + 2] if i + 2 < n else xs[i + 1]
        y3 = ys[i + 2] if i + 2 < n else ys[i + 1]
        cx1 = x1 + (x2 - x0) / 6.0
        cy1 = y1 + (y2 - y0) / 6.0
        cx2 = x2 - (x3 - x1) / 6.0
        cy2 = y2 - (y3 - y1) / 6.0
        p0x, p0y = x1, y1
        for s in range(samples_per_seg + 1):
            if i > 0 and s == 0:
                continue
            t = s / samples_per_seg
            mt = 1.0 - t
            x = mt**3 * p0x + 3 * mt**2 * t * cx1 + 3 * mt * t**2 * cx2 + t**3 * x2
            y = mt**3 * p0y + 3 * mt**2 * t * cy1 + 3 * mt * t**2 * cy2 + t**3 * y2
            out.append((x, y))
    return out


def _clamp_curve_xy_x(
    curve_xy: list[tuple[float, float]],
    x_min: float,
    x_max: float,
) -> list[tuple[float, float]]:
    lo, hi = float(x_min), float(x_max)
    return [(min(hi, max(lo, float(x))), float(y)) for x, y in curve_xy]


def _clamp_curve_y_floor(
    curve_xy: list[tuple[float, float]],
    y_floor: float,
) -> list[tuple[float, float]]:
    """Evita que Bézier/Catmull cuelgue por debajo del eje X (ventas en 0)."""
    yf = float(y_floor)
    return [(float(x), max(yf, float(y))) for x, y in curve_xy]


def _area_fill_under_curve_polygon(
    d,
    curve_xy: list[tuple[float, float]],
    y_base: float,
    hex_color: str,
    *,
    alpha: float = 1.0,
) -> None:
    from reportlab.graphics.shapes import Polygon
    from reportlab.lib import colors as rl_colors

    if len(curve_xy) < 2:
        return
    pr, pg, pb = _hex_to_rgb01(hex_color)
    flat: list[float] = []
    for x, y in curve_xy:
        flat.extend([float(x), float(y)])
    x_last, _y_last = curve_xy[-1]
    x_first, _y_first = curve_xy[0]
    flat.extend([float(x_last), float(y_base), float(x_first), float(y_base)])
    d.add(
        Polygon(
            flat,
            fillColor=rl_colors.Color(pr, pg, pb, alpha=float(alpha)),
            strokeColor=None,
            strokeWidth=0,
        )
    )


def _area_fill_yoy_purple_volume(
    d,
    curve_xy: list[tuple[float, float]],
    y_base: float,
) -> None:
    """Solo entre la curva muestreada y el eje; capas para volumen suave."""
    _area_fill_under_curve_polygon(d, curve_xy, y_base, _AREA_FILL_TOP_HEX, alpha=0.88)
    _area_fill_under_curve_polygon(d, curve_xy, y_base, _AREA_FILL_DEEP_HEX, alpha=0.45)
    _area_fill_under_curve_polygon(d, curve_xy, y_base, _REPORTE_LINE_PRIMARY_HEX, alpha=0.16)


def _path_catmull_stroke(
    xs: list[float],
    ys: list[float],
    *,
    stroke_hex: str,
    stroke_width: float,
    stroke_dash: list[float] | None = None,
):
    from reportlab.graphics.shapes import Path
    from reportlab.lib import colors as rl_colors

    n = len(xs)
    if n < 2:
        return None
    p = Path(
        strokeColor=rl_colors.HexColor(stroke_hex),
        strokeWidth=stroke_width,
        fillColor=None,
    )
    if stroke_dash:
        p.strokeDashArray = list(stroke_dash)
    p.moveTo(xs[0], ys[0])
    for i in range(n - 1):
        x0 = xs[i - 1] if i > 0 else xs[0]
        y0 = ys[i - 1] if i > 0 else ys[0]
        x1, y1 = xs[i], ys[i]
        x2, y2 = xs[i + 1], ys[i + 1]
        x3 = xs[i + 2] if i + 2 < n else xs[i + 1]
        y3 = ys[i + 2] if i + 2 < n else ys[i + 1]
        cx1 = x1 + (x2 - x0) / 6.0
        cy1 = y1 + (y2 - y0) / 6.0
        cx2 = x2 - (x3 - x1) / 6.0
        cy2 = y2 - (y3 - y1) / 6.0
        p.curveTo(cx1, cy1, cx2, cy2, x2, y2)
    return p


def _path_dense_polyline_stroke(
    curve_xy: list[tuple[float, float]],
    *,
    stroke_hex: str,
    stroke_width: float,
    stroke_dash: list[float] | None = None,
):
    """Trazo siguiendo la misma polilínea densa que la cima del área (onda suave, sin ‘picos’)."""
    from reportlab.graphics.shapes import Path
    from reportlab.lib import colors as rl_colors

    if len(curve_xy) < 2:
        return None
    p = Path(
        strokeColor=rl_colors.HexColor(stroke_hex),
        strokeWidth=stroke_width,
        fillColor=None,
    )
    if stroke_dash:
        p.strokeDashArray = list(stroke_dash)
    p.moveTo(curve_xy[0][0], curve_xy[0][1])
    for x, y in curve_xy[1:]:
        p.lineTo(x, y)
    return p


def reporte_pdf_draw_line(labels: list[str], vals: list[float]):
    """Serie única (ingresos diarios): fondo lila + área morada + curva Bézier."""
    from reportlab.graphics.shapes import Drawing, Line, Rect, String
    from reportlab.lib import colors

    if not vals or len(labels) != len(vals):
        return None
    n = len(vals)
    try:
        fv = [float(x) for x in vals]
    except (TypeError, ValueError):
        return None
    d_w, d_h = 480, 252
    ml, mr, mb, mt = 52, 14, 58, 36
    x0, y0 = ml, mb
    cw = d_w - ml - mr
    ch = d_h - mb - mt
    m = max(fv) if fv and max(fv) > 0 else 1.0
    if n == 1:
        xs = [x0 + cw / 2]
        ys = [y0 + ch * 0.92 * (fv[0] / m)]
    else:
        xs = [x0 + i * cw / (n - 1) for i in range(n)]
        ys = [y0 + ch * 0.92 * (fv[i] / m) for i in range(n)]
    y_base = y0
    ys = [max(y_base, float(y)) for y in ys]

    c_grid = colors.HexColor(_GRID_LINE_HEX)
    c_axis = colors.HexColor("#e2e6ec")
    d = Drawing(d_w, d_h)
    plot_h = ch * 0.92 + 1.0
    d.add(
        Rect(
            x0,
            y0,
            cw,
            plot_h,
            fillColor=colors.HexColor(_PLOT_BG_HEX),
            strokeColor=colors.HexColor(_PLOT_STROKE_HEX),
            strokeWidth=0.45,
        )
    )

    for gj in range(5):
        gy = y0 + (ch * 0.92) * (gj / 4.0)
        d.add(
            Line(
                x0,
                gy,
                x0 + cw,
                gy,
                strokeColor=c_grid,
                strokeWidth=0.35,
            )
        )

    d.add(
        Line(
            x0,
            y_base,
            x0 + cw,
            y_base,
            strokeColor=c_axis,
            strokeWidth=0.55,
        )
    )

    curve_top = _sample_catmull_area_top(xs, ys, samples_per_seg=64)
    curve_top = _clamp_curve_xy_x(curve_top, x0, x0 + cw)
    curve_top = _clamp_curve_y_floor(curve_top, y_base)
    _area_fill_yoy_purple_volume(d, curve_top, y_base)
    ln_main = _path_dense_polyline_stroke(
        curve_top,
        stroke_hex=_REPORTE_LINE_PRIMARY_HEX,
        stroke_width=2.0,
        stroke_dash=None,
    )
    if ln_main:
        d.add(ln_main)

    lbl_step = 2 if n >= 10 else 1
    fs_x = 5.5 if n >= 10 else 7.0
    shown = set()
    for i in range(0, n, lbl_step):
        shown.add(i)
    if n > 1 and (n - 1) not in shown:
        shown.add(n - 1)
    for i in sorted(shown):
        tx = _reporte_label_corta(str(labels[i]), 8)
        d.add(
            String(
                xs[i],
                y_base - 18,
                tx,
                textAnchor="middle",
                fontName="Helvetica",
                fontSize=fs_x,
                fillColor=colors.HexColor("#475569"),
            )
        )

    x_lbl_left = x0 - 10
    seen_ytxt: set[str] = set()
    for gj in range(5):
        gy = y0 + (ch * 0.92) * (gj / 4.0)
        tick_val = m * (gj / 4.0)
        txt = _format_cop_axis_short(tick_val)
        if txt in seen_ytxt:
            continue
        seen_ytxt.add(txt)
        d.add(
            String(
                x_lbl_left,
                gy - 3,
                txt,
                textAnchor="end",
                fontName="Helvetica",
                fontSize=7,
                fillColor=colors.HexColor("#64748b"),
            )
        )
    return d


def reporte_pdf_draw_multi_area(labels: list[str], series: list[tuple[str, list[float]]]):
    """YoY u otras multiseries: área morada (curva) + línea año anterior punteada sin relleno."""
    from reportlab.graphics.shapes import Drawing, Line, Rect, String
    from reportlab.lib import colors

    if len(series) < 2 or not labels:
        return None
    data_rows = [list(map(float, s[1])) for s in series]
    if any(len(r) != len(labels) for r in data_rows):
        return None
    n = len(labels)
    m = max((max(r) if r else 0) for r in data_rows) or 1.0

    lbl_series = [str(s[0]) for s in series]
    is_yoy = len(series) == 2 and any("anterior" in lb.lower() for lb in lbl_series)
    idx_prev = next((i for i, lb in enumerate(lbl_series) if "anterior" in lb.lower()), 1)
    idx_curr = next((i for i, lb in enumerate(lbl_series) if "actual" in lb.lower()), 0)
    if not is_yoy:
        idx_curr, idx_prev = 0, 1

    d_w, d_h = 480, 268
    ml, mr, mb, mt = 56, 18, 56, 40
    x0, y0 = ml, mb
    cw = d_w - ml - mr
    ch = d_h - mb - mt
    if n == 1:
        xs = [x0 + cw / 2]
    else:
        xs = [x0 + i * cw / (n - 1) for i in range(n)]
    y_base = y0

    serie_hex = [_REPORTE_LINE_PRIMARY_HEX, _REPORTE_LINE_SECONDARY_HEX]
    extra_hex = list(_REPORTE_CHART_COLORS_HEX[2:])
    while len(serie_hex) < len(data_rows):
        serie_hex.append(extra_hex[(len(serie_hex) - 2) % len(extra_hex)])

    ys_by_row: list[list[float]] = []
    for row in data_rows:
        ys_by_row.append([y0 + ch * 0.92 * (row[i] / m) for i in range(n)])
    ys_by_row = [[max(y_base, float(y)) for y in row] for row in ys_by_row]

    c_line_soft = colors.HexColor(_GRID_LINE_HEX)
    c_line_axis = colors.HexColor("#e2e6ec")
    c_purple = colors.HexColor(_REPORTE_LINE_PRIMARY_HEX)
    c_prev_line = colors.HexColor("#94a3b8")
    d = Drawing(d_w, d_h)
    plot_h = ch * 0.92 + 1.0
    d.add(
        Rect(
            x0,
            y0,
            cw,
            plot_h,
            fillColor=colors.HexColor(_PLOT_BG_HEX),
            strokeColor=colors.HexColor(_PLOT_STROKE_HEX),
            strokeWidth=0.45,
        )
    )

    for gj in range(5):
        gy = y0 + (ch * 0.92) * (gj / 4.0)
        d.add(
            Line(
                x0,
                gy,
                x0 + cw,
                gy,
                strokeColor=c_line_soft,
                strokeWidth=0.35,
            )
        )

    d.add(
        Line(
            x0,
            y_base,
            x0 + cw,
            y_base,
            strokeColor=c_line_axis,
            strokeWidth=0.55,
        )
    )

    if is_yoy:
        curve_top_curr = _sample_catmull_area_top(xs, ys_by_row[idx_curr], samples_per_seg=64)
        curve_top_curr = _clamp_curve_xy_x(curve_top_curr, x0, x0 + cw)
        curve_top_curr = _clamp_curve_y_floor(curve_top_curr, y_base)
        curve_top_prev = _sample_catmull_area_top(xs, ys_by_row[idx_prev], samples_per_seg=64)
        curve_top_prev = _clamp_curve_xy_x(curve_top_prev, x0, x0 + cw)
        curve_top_prev = _clamp_curve_y_floor(curve_top_prev, y_base)
        _area_fill_yoy_purple_volume(d, curve_top_curr, y_base)
        ln_behind = _path_dense_polyline_stroke(
            curve_top_prev,
            stroke_hex="#64748b",
            stroke_width=1.0,
            stroke_dash=[4, 3],
        )
        if ln_behind:
            d.add(ln_behind)
        ln_main = _path_dense_polyline_stroke(
            curve_top_curr,
            stroke_hex=_REPORTE_LINE_PRIMARY_HEX,
            stroke_width=2.0,
            stroke_dash=None,
        )
        if ln_main:
            d.add(ln_main)
    else:
        for si in range(len(data_rows)):
            curve_top = _sample_catmull_area_top(xs, ys_by_row[si], samples_per_seg=64)
            curve_top = _clamp_curve_xy_x(curve_top, x0, x0 + cw)
            curve_top = _clamp_curve_y_floor(curve_top, y_base)
            hx = serie_hex[si]
            _area_fill_under_curve_polygon(d, curve_top, y_base, hx, alpha=0.35)
            _area_fill_under_curve_polygon(d, curve_top, y_base, hx, alpha=0.45)
        for si in range(len(data_rows)):
            curve_ln = _sample_catmull_area_top(xs, ys_by_row[si], samples_per_seg=64)
            curve_ln = _clamp_curve_xy_x(curve_ln, x0, x0 + cw)
            curve_ln = _clamp_curve_y_floor(curve_ln, y_base)
            ln_s = _path_dense_polyline_stroke(
                curve_ln,
                stroke_hex=serie_hex[si],
                stroke_width=2.0,
                stroke_dash=None,
            )
            if ln_s:
                d.add(ln_s)

    lbl_fs = 7.0 if n > 10 else 7.5
    for i, lab in enumerate(labels):
        tx = _reporte_label_corta(str(lab), 14 if n > 10 else 16)
        d.add(
            String(
                xs[i],
                y_base - 16,
                tx,
                textAnchor="middle",
                fontName="Helvetica",
                fontSize=lbl_fs,
                fillColor=colors.HexColor("#334155"),
            )
        )

    x_lbl_left = x0 - 10
    seen_ytxt: set[str] = set()
    for gj in range(5):
        gy = y0 + (ch * 0.92) * (gj / 4.0)
        tick_val = m * (gj / 4.0)
        txt = _format_cop_axis_short(tick_val)
        if txt in seen_ytxt:
            continue
        seen_ytxt.add(txt)
        d.add(
            String(
                x_lbl_left,
                gy - 3,
                txt,
                textAnchor="end",
                fontName="Helvetica",
                fontSize=7,
                fillColor=colors.HexColor("#64748b"),
            )
        )

    leg_y = 18
    lx = 44
    for si, (sname, _) in enumerate(series):
        col = c_prev_line if (is_yoy and si == idx_prev) else (
            c_purple if (is_yoy and si == idx_curr) else colors.HexColor(serie_hex[si])
        )
        prefix = "– – " if (is_yoy and si == idx_prev) else "● "
        d.add(
            String(
                lx + si * 132,
                leg_y,
                prefix + _reporte_label_corta(str(sname), 18),
                fontName="Helvetica-Bold",
                fontSize=7.5,
                fillColor=col,
            )
        )
    return d
