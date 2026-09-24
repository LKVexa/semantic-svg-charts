# 0.1.2a1 — 2026-09-23

- Validate bounded detached specs and XML-safe text; reject unknown fields.
- Use robust rational scales and finite constant-domain padding.
- Match rounded geometry to SVG; add ticks and accessible full data values.
- Disclose text truncation, label thinning and rounded tick collisions.
- Verify complete canonical renders, primitive extents and text anchors.
- Add 39 regressions, browser sample review, packaging and cross-platform CI.
- Include README and Apache 2.0 LICENSE/NOTICE; original certification remains open.

# Changelog — E06 Visualization Engine (JY-S027-P001)

## 0.1.1-partial — 2026-09-14 (maintenance audit A023)

Baseline fingerprint: build-0001 product.zip
sha256 db96e9a1acfadef87ea099a0e262c3b2dbbb4757eac3f685ec39714428d04f41
(6820 bytes), code version 0.1.0-partial. All 14 baseline tests passed
before patching; every finding below was reproduced on the baseline
with live probes before any fix was written.

### Fixed (all reproduced on baseline)

- **A023-F1** NaN series values accepted. Observed: `render()` returned a
  certified result whose SVG contained literal `nan` coordinates and whose
  clipping inspector still reported PASS. Expected: refusal. Now raises
  `SpecError` ("value must be finite").
- **A023-F2** Infinite series values accepted. Observed: inf/-inf produced
  nonsense geometry in a certified render. Now raises `SpecError`.
- **A023-F3** `bool` accepted as a numeric value (`True` rendered as a bar
  of height 1 labelled "True..."). Now refused as non-numeric.
- **A023-F4** Non-dict spec (e.g. `render(None)`) leaked a bare
  `TypeError: argument of type 'NoneType' is not iterable` instead of the
  documented `SpecError`. Now `SpecError("spec must be a dict")`.
- **A023-F5** Non-dict series item (e.g. `series=[5]`) leaked a bare
  `TypeError`. Now `SpecError("series[i] must be a dict ...")`.
- **A023-F6** `inspect_clipping()` returned PASS for elements tampered
  with non-finite geometry (NaN comparisons are all False). Non-finite
  x/y/w/h are now flagged as clipped and the verdict is FAIL.

### Added
- `e06.core.__version__` alias of `VERSION` (now "0.1.1-partial").
- 7 focused tests (positive + negative) covering F1–F6.

### Compatibility
- No public API removed or renamed. All valid 0.1.0-partial specs render
  byte-identically (renderer geometry untouched); only previously
  undefined/misleading inputs now refuse with `SpecError`, and
  `engine_version` in the certified output naturally reads
  "0.1.1-partial". No baseline test asserted the old weaker behavior;
  none were weakened.

### Rollback
- Restore build-0001 product.zip
  (sha256 db96e9a1acfadef87ea099a0e262c3b2dbbb4757eac3f685ec39714428d04f41).
