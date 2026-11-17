# Analysis pipeline

The `repwise.pose.persist` worker task validates pose inference output before it
becomes a downstream analysis artifact. Every artifact pins the normalized media
checksum, model name/version/checksum, landmark schema, preprocessing settings,
per-landmark visibility/presence, and explicit missingness.

Inference output remains private object-storage data. The supported adapter
accepts MediaPipe Pose Landmarker output with 33 landmarks. An alternative
estimator requires a separately named, versioned adapter that maps its native
keypoints explicitly; incompatible keypoints must never be relabelled as
MediaPipe landmarks.

Large frame arrays are stored as canonical, versioned JSON artifacts. Their
deterministic checksum is returned to the job coordinator for indexed database
metadata; raw arrays are not copied into PostgreSQL.

The `repwise.squat.segment` task verifies the pose artifact checksum, converts
normalized coordinates to aspect-correct pixel geometry, and publishes a
versioned segmentation artifact. Complete repetitions require a full return to
standing. Partial depth and incomplete returns remain separate, while low pose
coverage, long observation gaps, and recordings without squat motion produce an
explicit `not_assessable` result. Phase tempo always uses presentation
timestamps rather than an assumed frame rate.
