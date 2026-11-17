# Exercise contracts

Versioned, immutable definitions describe what RepWise may measure for one
exercise, variant and camera view. A contract remains disabled until its checks
have coach review and evaluation evidence.

The catalog includes side-view bodyweight squat, push-up and standing-curl
contracts. Push-up and curl have independent synthetic held-out fixtures and
cautious report cues, but every check remains disabled until real coach sign-off
is attached. They explicitly exclude pain, injury-risk, tissue-load, muscle and
precise 3D claims.

Run `make contracts-validate`. The validator checks structural fields and domain
rules: known landmarks, ordered numeric ranges, non-overlapping capabilities and
checks supported by the selected view.

Contract versions are append-only once referenced by an analysis. Publish a new
version instead of changing the meaning of a historical version.
