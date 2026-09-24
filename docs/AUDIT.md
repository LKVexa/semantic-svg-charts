# Audit and hardening — 0.1.2a1

Date: 2026-09-23. Source: JY-S027-P001 / 0.1.1-partial / run-0001 / product.
Reviewed validation, numeric scaling, SVG encoding/layout and clipping claims.
Original source remains separate from the release checkout.

## Repaired findings

- Text fields accepted arbitrary objects, missing-content strings, XML controls
  and unbounded lengths; specs/series also lacked budgets. Exact detached input
  validation, control checks, unknown-field refusal and byte/point limits apply.
- Large constant domains collapsed when adding 1.0; opposite extreme finite
  floats overflowed their span. Fraction arithmetic, finite constant padding and
  bounded safe integers fix the mapping while preserving finite float extremes.
- Unrounded geometry metadata differed from rendered bar positions. Shared
  rounded values now match SVG, and circle radius is explicit.
- The inspector trusted caller metadata and used a regex that missed vertical
  anchors, signs/exponents, missing elements and arbitrary SVG changes. It now
  validates bounded input, re-renders the canonical spec and compares the complete
  response before reporting geometry/anchor checks. Negative extents fail.
- Output hashes did not bind semantics/spec/metadata. A whole-render digest now
  binds all fields, without claiming authenticity or certification.
- Charts lacked visible scale ticks, line values were inaccessible, and dense
  labels/long text overlapped. Added ticks, full accessible data/tooltips, bounded
  visible text and disclosed category thinning. Four-digit display precision and
  repeated rounded ticks are explicit; original values remain in metadata.

## Verification and visual review

21 baseline tests passed (the original README's 14-test count was stale).
60 source/installed-wheel tests pass after changes, including 39 new checks for
input budgets, extreme/subnormal/constant domains, rational mapping/ticks,
XML structure/escaping, passive markup, exact geometry, detached values and
tampering of SVG, hashes, semantics, dimensions, radius and both text coordinates.
Only the inherited version assertion changed; original behavior checks remain.

Browser-reviewed five samples: ordinary bars, mixed signs, 40-point line,
opposite maximum finite floats and long/dense labels. Review found the minimum
negative bar value overlapping its category; moved it inside the bar with white
text, then visually rechecked. Removed empty unit parentheses. Extreme numeric
labels and dense line categories were legible in the reviewed browser samples.
No exhaustive font, multilingual, accessibility or visual regression claim.

CHECK_RUNS.json records current evidence; BASELINE_CHECK_RUNS.json preserves
historical evidence. CI runs Linux 3.10/3.12/3.14 and Windows 3.12.
Version/schema advanced to 0.1.2a1 / e06/render/v2. Added packaging, pinned-action
CI, README, security guidance, and Apache 2.0 LICENSE/NOTICE naming
RUSSELL PHILIP SMITHSON. No vendored code or third-party runtime dependencies.
The 172-unit program and governed certification services remain outside scope.

## Primary references

- [SVG 2 text](https://www.w3.org/TR/SVG2/text.html): glyph metrics, shaping,
  anchors and renderer-dependent text layout motivate the limited inspection claim.
- [Python fractions](https://docs.python.org/3/library/fractions.html):
  exact rational conversion of stored integer/binary float values.
