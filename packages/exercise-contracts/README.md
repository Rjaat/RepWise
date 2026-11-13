# Exercise contracts

Versioned, immutable definitions describe what RepWise may measure for one
exercise, variant and camera view. A contract remains disabled until its checks
have coach review and evaluation evidence.

The first seed is a side-view bodyweight squat contract. It intentionally marks
frontal knee tracking, internal loading and precise 3D mechanics as unavailable.

Run `make contracts-validate`. The validator checks structural fields and domain
rules: known landmarks, ordered numeric ranges, non-overlapping capabilities and
checks supported by the selected view.

Contract versions are append-only once referenced by an analysis. Publish a new
version instead of changing the meaning of a historical version.
