# Semantic SVG Charts

**0.1.2a1 — experimental partial candidate, JY-S027-P001 / E06**

A pure Python renderer for categorical bar and line charts. A bounded, validated
specification produces deterministic SVG, exact input values, scale metadata and
unsigned integrity hashes. Rendering and inspection perform no file/network I/O.
Python 3.10+; no third-party runtime dependencies.

## Use

~~~sh
python -m pip install .
python -m unittest discover -s tests -t .
~~~

~~~python
from e06.core import render, inspect_clipping

chart = render({
    "kind": "bar", "title": "Weekly deploys",
    "x_label": "Week", "y_label": "Deploys", "y_unit": "",
    "aggregation": "sum",
    "series": [{"label": "W1", "value": 4}, {"label": "W2", "value": 9}],
})
assert inspect_clipping(chart)["verdict"] == "PASS"
svg_text = chart["svg"]  # The caller decides whether/where to display or save it.
~~~

## Inputs and data semantics

Required fields are kind, title, x_label, y_label, y_unit and series. Only the
optional aggregation field is additionally accepted; unknown fields are refused.
Kinds are bar and line. Aggregation is raw (default), sum, mean or median;
it is a caller declaration, never an operation performed by this renderer.
Supply already-computed values. A declared aggregation is not independently verified.

Series contains 1..256 exact dictionaries with label and value. Labels are
nonblank strings up to 128 characters. Titles/axis labels are nonblank strings
up to 256 characters; units up to 32, with the empty string meaning unitless.
Combined text is capped at 16 KiB UTF-8. Control characters, XML-invalid code
points, surrogate code points and explicit bidi embedding/isolate controls are
refused. Unicode text is otherwise retained, not normalized or linguistically
validated. Inputs must use exact built-in dict/list/str/int/float types.

Values are finite floats or integers in -(2**53-1)..(2**53-1); booleans and custom
numeric objects are refused. The integer cap preserves exact JSON interoperability.
Float values represent the caller's binary floating-point numbers, not exact
decimal measurements. All finite float magnitudes, including subnormals, are
supported without scale-span overflow.

The x-axis represents equally spaced categories in supplied order, including
duplicate labels. It is not a numeric/time axis; a line connects that category
order and does not establish interpolation, causality or temporal spacing.
Bar domains include zero and both signs. Line domains fit data; constant lines
receive finite padding (5% where representable, at least one ULP). All-zero bars
use [0,1]; all-zero lines use [-1,1]. No caller axis override is accepted.

Scale mapping uses exact Fraction conversions of accepted numbers, then converts
the bounded pixel coordinate to float and rounds to two decimals. Metadata exposes
domain, top, plot height, formula and rounding. Tick exact_ratio pairs preserve
their rational positions; numeric tick values and four-significant-digit labels
are approximations. Repeated displayed tick labels trigger a visible note and
repeated_tick_labels=true. Do not infer tiny differences from rounded text alone.

## SVG and layout

The viewBox is 640x400, with the data plot at x=96..616 and y=40..350.
Rounded bar/circle coordinates match the returned elements exactly. Circle bounds
include radius; line segments remain inside the plot. Positive/negative bars share
the zero line. A single line point is horizontally centered.

At most eight category labels are shown, retaining the first/last categories.
Category text truncates to eight code points, the title to 36, horizontal axis
title to 48 and vertical axis title to 32. Full text stays in metadata, accessible
description and element tooltips. Visible bar values use four significant digits;
full values and units are in tooltips and metadata. Shortening is by code point,
not grapheme cluster; combined-script text may need caller-specific presentation.
Thinning/truncation may make labels visually ambiguous: inspect full labels.

SVG contains fixed passive shapes/text, escaped caller text, a white background,
visible axes/ticks, role=img, title and a description containing all data values.
No scripts, event handlers, embedded HTML, external resources or caller attributes
are generated. Accessibility IDs derive from the spec digest. Prefer isolated
image/object documents when embedding identical SVGs to avoid duplicate IDs;
host CSS, fonts and accessibility software affect presentation.

Text fitting is a bounded heuristic. Font shaping, glyph extents, label overlap,
tiny marks and readability require visual review, particularly at 256 points or
with multilingual/long labels. There is no browser-independent guarantee that
every glyph fits or that every chart is accessible. Only SVG bytes are deterministic;
raster pixels depend on the renderer, fonts, scale and environment.

## Integrity and inspection

The e06/render/v2 response includes a detached canonical spec, SVG, semantics,
rounded mark geometry, text anchors, output_digest and render_digest.
output_digest hashes SVG UTF-8 bytes. render_digest hashes all other response
fields as sorted compact ASCII-escaped strict JSON. Identical normalized input
is byte stable; omitted aggregation and explicit raw normalize identically.
ephemeral=true means the library itself does not persist, not that a caller
cannot save or transmit returned data.

inspect_clipping retains its original API name but reports a narrower, explicit
scope. It checks bounded input, re-renders the included spec, compares the entire
canonical response, and checks data-mark extents and both text-anchor coordinates.
SVG is never parsed as arbitrary active content. Missing/changed fields, altered
SVG, rehashed noncanonical output, negative extents and invalid numbers fail.

A PASS establishes consistency with this renderer and those geometry checks.
text_glyph_bounds and label_overlap remain NOT_CHECKED. It does not certify
source truth, accessibility, text containment, authorization or provenance.
Hashes are unkeyed: anyone can substitute a new spec and valid rendering.
Malformed inspection inputs return FAIL; invalid render specs raise SpecError.
Inspection caps depth at 12, values at 30000, individual strings at 512 Ki
characters and aggregate string values at 1 Mi characters.

## Validation and migration

60 tests: 21 inherited checks plus 39 new regressions for strict types/budgets,
extreme/constant/subnormal values, rational mappings, XML escaping, exact mark
coordinates, detached input and complete render/geometry tamper detection.
Source and installed-wheel evidence: [CHECK_RUNS](docs/CHECK_RUNS.json).
CI covers Linux Python 3.10/3.12/3.14 and Windows 3.12.

Five chart samples were reviewed in a browser. A negative-bar value/category
overlap found there was repaired and rechecked. This sample review does not
establish exhaustive font/layout qualification. See [AUDIT](docs/AUDIT.md).

0.1.1-partial -> 0.1.2a1 changes SVG bytes, layout, stricter accepted specs,
constant scales, inspector scope and response schema/digests. Regenerate earlier
renders from source specs; do not compare v1/v2 digests. Certification terminology
has been removed. The original 172-unit certification program, governance,
signing/attestation, additional chart kinds and gate decisions remain open.

## License

Copyright 2026 **RUSSELL PHILIP SMITHSON**.
[Apache License 2.0](LICENSE), with [NOTICE](NOTICE).
No third-party source is vendored; see [THIRD-PARTY-NOTICES](THIRD-PARTY-NOTICES.md).
