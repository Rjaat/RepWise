# Pose model operations

RepWise runs pose estimation only in the media worker. The API image does not
contain MediaPipe or a model binary.

Provide a MediaPipe Pose Landmarker `.task` model from an approved source and set:

```text
REPWISE_POSE_MODEL_PATH=/models/pose_landmarker.task
REPWISE_POSE_MODEL_SHA256=<lowercase SHA-256 of that exact file>
REPWISE_POSE_MODEL_NAME=MediaPipe Pose Landmarker Full
REPWISE_POSE_MODEL_VERSION=<internal immutable model release ID>
REPWISE_POSE_SAMPLE_FPS=10
```

Mount the model read-only into the worker. Do not commit model binaries. Record the
source URL, retrieval date, license review, checksum, and approver in the release
record. The worker fails closed if the file is absent or its checksum differs.

Inference samples normalized video at a fixed rate, uses MediaPipe VIDEO mode, and
stores private adapter output containing all 33 landmarks. Frames without a pose
are retained with missing landmarks; a video with no detected pose fails instead
of producing a misleading report.
