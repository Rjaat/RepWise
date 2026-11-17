# Exercise contracts

Versioned, immutable definitions describe what RepWise may measure for one
exercise, variant and camera view. A contract remains disabled until its checks
have coach review and evaluation evidence.

The catalog includes side-view bodyweight squat and push-up contracts. The
push-up contract has independent synthetic held-out evidence and cautious report
cues, but every check remains disabled until real coach sign-off is attached.
It explicitly excludes pain, injury-risk, tissue-load and precise 3D claims.

Run `make contracts-validate`. The validator checks structural fields and domain
rules: known landmarks, ordered numeric ranges, non-overlapping capabilities and
checks supported by the selected view.

Contract versions are append-only once referenced by an analysis. Publish a new
version instead of changing the meaning of a historical version.
