# Analysis worker

The `repwise.pose.persist` worker task validates pose inference output before it
becomes a downstream analysis artifact. Every artifact pins the normalized media
checksum, model name/version/checksum, landmark schema, preprocessing settings,
per-landmark visibility/presence, and explicit missingness.

Inference output remains private object-storage data. The adapter currently
accepts MediaPipe Pose's 33-landmark schema; another estimator must provide its
own named adapter instead of pretending that incompatible keypoints exist.

Large frame arrays are stored as canonical, versioned JSON artifacts. Their
deterministic checksum is returned to the job coordinator for indexed database
metadata; raw arrays are not copied into PostgreSQL.
