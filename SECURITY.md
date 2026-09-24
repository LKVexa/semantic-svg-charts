# Security boundaries

The core computes over supplied data with no file/network access. Returned SVG
uses fixed passive markup and escapes validated caller text. This renderer is not
a general SVG sanitizer; never bypass integrity checks to trust arbitrary SVG.
Do not execute or treat chart labels as instructions.

Source values and aggregation labels are unverified caller claims. SVG metadata,
tooltips and accessible descriptions retain full text/data even when visible
labels are shortened. Manage sensitive data, access and retention in the caller.

Digests detect consistency differences, not authorship or source truth. Re-render
inspection can be satisfied by anyone generating a new valid chart. It is not a
signature, certification, authorization or governed audit log.

Input/inspection budgets limit normal work but do not provide process isolation
or a hard time/memory quota. Text glyph bounds, overlap, font behavior, embedded
host CSS and full accessibility are not certified. Visually review outputs.
No runtime dependency upgrade or build-tool vulnerability scan is claimed.
