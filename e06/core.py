"""Pure categorical SVG charts with bounded inputs and inspectable semantics."""
from __future__ import annotations

from fractions import Fraction
import hashlib
import json
import math
from types import MappingProxyType

VERSION = "0.1.2a1"
__version__ = VERSION
W, H = 640, 400
MARGIN = MappingProxyType({"left": 96, "right": 24, "top": 40, "bottom": 50})
REQUIRED = frozenset(("kind", "title", "x_label", "y_label", "y_unit", "series"))
MAX_POINTS = 256
MAX_TEXT_BYTES = 16384


class SpecError(Exception):
    pass


def _json(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, allow_nan=False,
                      separators=(",", ":"))


def _digest(obj):
    return "sha256:" + hashlib.sha256(_json(obj).encode()).hexdigest()


def _text(value, field, maximum=256, empty=False):
    if type(value) is not str or (not empty and not value.strip()) or len(value) > maximum:
        raise SpecError(field + " must be bounded text")
    # XML 1.0 legal characters, with line/control/bidi formatting excluded.
    for c in value:
        n = ord(c)
        if (n < 32 or 0x7f <= n <= 0x9f or 0xd800 <= n <= 0xdfff
                or n & 0xffff in (0xfffe, 0xffff)
                or 0x202a <= n <= 0x202e or 0x2066 <= n <= 0x2069):
            raise SpecError(field + " contains an unsupported text control")
    return value


def _validate(spec):
    if type(spec) is not dict or not REQUIRED <= spec.keys() or spec.keys() - REQUIRED - {"aggregation"}:
        raise SpecError("spec needs exactly kind/title/x_label/y_label/y_unit/series and optional aggregation")
    if type(spec["kind"]) is not str or spec["kind"] not in ("bar", "line"):
        raise SpecError("kind must be bar or line")
    aggregation = spec.get("aggregation", "raw")
    if type(aggregation) is not str or aggregation not in ("raw", "sum", "mean", "median"):
        raise SpecError("aggregation must be raw, sum, mean or median")
    clean = {"kind": spec["kind"], "aggregation": aggregation}
    for field in ("title", "x_label", "y_label", "y_unit"):
        clean[field] = _text(spec[field], field, 32 if field == "y_unit" else 256,
                             empty=field == "y_unit")
    series = spec["series"]
    if type(series) is not list or not 1 <= len(series) <= MAX_POINTS:
        raise SpecError("series must contain 1..256 points")
    clean["series"] = []
    size = sum(len(clean[field].encode()) for field in ("title", "x_label", "y_label", "y_unit"))
    for point in series:
        if type(point) is not dict or point.keys() != {"label", "value"}:
            raise SpecError("each point needs exactly label and value")
        label = _text(point["label"], "point label", 128)
        value = point["value"]
        if type(value) not in (int, float):
            raise SpecError("value must be an exact int or float")
        if type(value) is int and abs(value) > 2**53 - 1:
            raise SpecError("integer values must fit the exact JSON number range")
        if type(value) is float and not math.isfinite(value):
            raise SpecError("value must be finite")
        size += len(label.encode())
        clean["series"].append({"label": label, "value": value})
    if size > MAX_TEXT_BYTES:
        raise SpecError("combined label text exceeds 16 KiB UTF-8")
    return clean


def _scale(spec):
    values = [p["value"] for p in spec["series"]]
    lo, hi = min(values), max(values)
    if spec["kind"] == "bar":
        lo, hi = min(0, lo), max(0, hi)
    if lo == hi:
        if lo == 0:
            lo, hi = (0, 1) if spec["kind"] == "bar" else (-1, 1)
        else:
            # Pad constants, with a representable floor and finite endpoint clamp.
            delta = max(abs(float(lo)) * 0.05, math.ulp(float(lo)))
            lower = float(lo) - delta
            upper = float(hi) + delta
            lo = lower if math.isfinite(lower) else lo
            hi = upper if math.isfinite(upper) else hi
    low, high = Fraction(lo), Fraction(hi)
    plot_height = H - MARGIN["top"] - MARGIN["bottom"]

    def y_of(value):
        fraction = (Fraction(value) - low) / (high - low)
        # Fraction keeps ±max-float spans and subnormal differences well defined.
        return round(float(MARGIN["top"] + plot_height * (1 - fraction)), 2)

    return {"domain": [lo, hi], "plot_height": plot_height,
            "mapping": "y = round(top + plot_height * (1 - (v - lo)/(hi - lo)), 2)",
            "y_of": y_of}


def _esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _short(text, length):
    return text if len(text) <= length else text[:length - 1] + "…"


def _number(value):
    return str(value) if type(value) is int else repr(value)


def render(spec):
    """No file/network I/O; deterministic for an identical validated spec."""
    spec = _validate(spec)
    scale = _scale(spec)
    y_of = scale["y_of"]
    n = len(spec["series"])
    plot_width = W - MARGIN["left"] - MARGIN["right"]
    visible = sorted({round(i * (n - 1) / min(n - 1, 7)) for i in range(min(n, 8))}) if n > 1 else [0]
    summary = "; ".join(p["label"] + ": " + _number(p["value"]) + spec["y_unit"] for p in spec["series"])
    prefix = "chart-" + _digest(spec)[7:23]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-labelledby="{prefix}-title {prefix}-desc">',
        f'<title id="{prefix}-title">{_esc(spec["title"])}</title>',
        f'<desc id="{prefix}-desc">{_esc(spec["kind"] + " chart; categorical x-axis; declared aggregation " + spec["aggregation"] + "; " + summary)}</desc>',
        '<rect x="0" y="0" width="640" height="400" fill="white"/>',
    ]
    anchors = []

    def text(x, y, value, size=11, anchor="middle", transform=None, full=None, fill="#172b3a"):
        anchors.append({"x": x, "y": y})
        extra = f' transform="{transform}"' if transform else ""
        title = f"<title>{_esc(full)}</title>" if full is not None else ""
        parts.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="sans-serif" font-size="{size}" fill="{fill}"{extra}>{title}{_esc(value)}</text>')

    text(320, 24, _short(spec["title"], 36), 16, full=spec["title"])
    lo, hi = scale["domain"]
    ticks = []
    for i in range(5):
        exact = Fraction(lo) + (Fraction(hi) - Fraction(lo)) * Fraction(i, 4)
        value = float(exact)
        y = round(350 - 310 * i / 4, 2)
        ticks.append({"value": value, "exact_ratio": [str(exact.numerator), str(exact.denominator)], "y": y})
        parts.append(f'<line x1="96" y1="{y}" x2="616" y2="{y}" stroke="#dce3e8" stroke-width="1"/>')
        text(91, round(y + 3, 2), format(value, ".4g"), 9, anchor="end", full=_number(value))
    rounded_tick_labels = len({format(t["value"], ".4g") for t in ticks}) < len(ticks)
    if rounded_tick_labels:
        text(356, 36, "Rounded ticks; exact scale in metadata", 9)
    parts.append('<line x1="96" y1="40" x2="96" y2="350" stroke="#526675"/>')
    if lo <= 0 <= hi:
        parts.append(f'<line x1="96" y1="{y_of(0)}" x2="616" y2="{y_of(0)}" stroke="#526675"/>')
    elements, points = [], []
    for i, point in enumerate(spec["series"]):
        value, label = point["value"], point["label"]
        y = y_of(value)
        tip = _esc(label + ": " + _number(value) + spec["y_unit"])
        if spec["kind"] == "bar":
            slot = plot_width / n
            x = round(96 + (i + 0.15) * slot, 2)
            width = round(0.7 * slot, 2)
            center = round(x + width / 2, 2)
            baseline = y_of(0)
            top, height = min(y, baseline), round(abs(y - baseline), 2)
            elements.append({"x": x, "y": top, "w": width, "h": height})
            parts.append(f'<rect x="{x}" y="{top}" width="{width}" height="{height}" fill="#4477aa"><title>{tip}</title></rect>')
            if i in visible:
                inside = value < 0 and y > 330 and height > 15
                label_y = y - 5 if value >= 0 or inside else min(y + 13, 343)
                text(center, round(label_y, 2), format(value, ".4g"), 9,
                     anchor="end" if center > 570 else "middle",
                     fill="white" if inside else "#172b3a",
                     full=label + ": " + _number(value) + spec["y_unit"])
        else:
            center = round(96 + (plot_width / 2 if n == 1 else i * plot_width / (n - 1)), 2)
            elements.append({"x": center, "y": y, "w": 0, "h": 0, "radius": 3})
            points.append(f"{center},{y}")
            parts.append(f'<circle cx="{center}" cy="{y}" r="3" fill="#4477aa"><title>{tip}</title></circle>')
        if i in visible:
            text(center, 369, _short(label, 8), 10,
                 anchor="end" if center > 590 else "middle", full=label)
    if points:
        parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="#4477aa" stroke-width="2" stroke-linejoin="round"/>')
    text(320, 392, _short(spec["x_label"], 48), 12, full=spec["x_label"])
    axis_title = spec["y_label"] + (" (" + spec["y_unit"] + ")" if spec["y_unit"] else "")
    text(16, 200, _short(axis_title, 32), 12, transform="rotate(-90 16 200)", full=axis_title)
    parts.append("</svg>")
    svg = "\n".join(parts)
    result = {
        "schema": "e06/render/v2", "engine_version": VERSION, "spec": spec,
        "svg": svg, "output_digest": "sha256:" + hashlib.sha256(svg.encode()).hexdigest(),
        "semantics": {
            "kind": spec["kind"], "title": spec["title"], "x_label": spec["x_label"], "y_label": spec["y_label"],
            "scale": {"domain": scale["domain"], "mapping": scale["mapping"],
                      "top": 40, "plot_height": 310, "round_digits": 2,
                      "arithmetic": "exact rational inputs, then binary float and round",
                      "zero_based": spec["kind"] == "bar", "ticks": ticks,
                      "repeated_tick_labels": rounded_tick_labels},
            "labels": [p["label"] for p in spec["series"]],
            "values": [p["value"] for p in spec["series"]],
            "unit": spec["y_unit"], "aggregation": spec["aggregation"],
            "aggregation_performed": False, "x_spacing": "equal categorical positions",
            "plot": {"left": 96, "right": 616, "top": 40, "bottom": 350},
            "number_display": "4 significant digits; full values in metadata/tooltips",
            "visible_label_indices": visible, "hidden_category_labels": n - len(visible),
        },
        "elements": elements, "text_anchors": anchors, "ephemeral": True,
        "note": "deterministic SVG; unsigned integrity, no certification or text-glyph bounds claim",
    }
    result["render_digest"] = _digest(result)
    return result


def _bounded_json(value):
    """Refuse malformed/cyclic/oversized inspection input before serialization."""
    stack = [(value, 0)]
    count = total = 0
    while stack:
        item, depth = stack.pop()
        count += 1
        if depth > 12 or count > 30000:
            return False
        kind = type(item)
        if kind is str:
            if len(item) > 524288:
                return False
            total += len(item)
            if total > 1048576:
                return False
        elif kind in (dict, list):
            if len(item) > 30000:
                return False
            if kind is dict:
                if any(type(k) is not str or len(k) > 256 for k in item):
                    return False
                stack.extend((v, depth + 1) for v in item.values())
            else:
                stack.extend((v, depth + 1) for v in item)
        elif kind is float:
            if not math.isfinite(item):
                return False
        elif kind is int:
            if item.bit_length() > 1024:
                return False
        elif item is not None and kind is not bool:
            return False
    return True


def inspect_clipping(rendered):
    """Check canonical render integrity, primitive extents and text anchors only.

    Arbitrary SVG is never parsed or trusted. This does not measure text glyph
    boxes, label overlap, font substitution, readability or source truth.
    """
    report = {"schema": "e06/inspection/v2", "verdict": "FAIL",
              "clipped_elements": [], "out_of_bounds_anchors": [],
              "integrity": "FAIL", "text_glyph_bounds": "NOT_CHECKED",
              "label_overlap": "NOT_CHECKED", "errors": []}
    if type(rendered) is not dict or not _bounded_json(rendered):
        report["errors"].append("malformed or over-budget render")
        report["clipped_elements"].append({"element": "unverified"})
        return report
    try:
        expected = render(rendered["spec"])
        if _json(rendered) != _json(expected):
            report["errors"].append("render differs from canonical rendering of its spec")
        else:
            report["integrity"] = "PASS"
        for i, element in enumerate(rendered.get("elements", [])):
            if type(element) is not dict or not {"x", "y", "w", "h"} <= element.keys():
                report["clipped_elements"].append({"element": i})
                continue
            coords = [element[k] for k in ("x", "y", "w", "h")]
            radius = element.get("radius", 0)
            if (any(type(v) not in (int, float) for v in coords + [radius])
                    or element["w"] < 0 or element["h"] < 0 or radius < 0
                    or element["x"] - radius < 0 or element["y"] - radius < 0
                    or element["x"] + element["w"] + radius > W
                    or element["y"] + element["h"] + radius > H):
                report["clipped_elements"].append({"element": i})
        for i, anchor in enumerate(rendered.get("text_anchors", [])):
            if (type(anchor) is not dict or set(anchor) != {"x", "y"}
                    or any(type(v) not in (int, float) for v in anchor.values())
                    or not 0 <= anchor["x"] <= W or not 0 <= anchor["y"] <= H):
                report["out_of_bounds_anchors"].append(i)
    except (SpecError, KeyError, TypeError, ValueError, OverflowError):
        report["errors"].append("invalid render structure or spec")
    if report["integrity"] == "PASS" and not report["clipped_elements"] and not report["out_of_bounds_anchors"]:
        report["verdict"] = "PASS"
    return report
