# Pose model operations

This guide defines the deployment and provenance requirements for the pose
model used by the RepWise media worker. The API image does not contain the
MediaPipe runtime or a model binary.

## Required model record

The release owner must approve one MediaPipe Pose Landmarker `.task` file and
record the following information in the release evidence:

- exact source URL and publisher;
- retrieval timestamp;
- original filename and byte size;
- lowercase SHA-256 of the stored file;
- model variant and an immutable internal release identifier;
- license and redistribution review;
- approver identity and approval timestamp.

Do not commit or redistribute the model through this repository. A filename,
marketing name, or mutable download URL is not a model identity; the SHA-256 and
internal release identifier are mandatory.

## Worker configuration

Mount the approved model read-only into the media worker and configure:

```text
REPWISE_POSE_MODEL_PATH=/models/pose_landmarker.task
REPWISE_POSE_MODEL_SHA256=<64-character lowercase SHA-256>
REPWISE_POSE_MODEL_NAME=MediaPipe Pose Landmarker Full
REPWISE_POSE_MODEL_VERSION=<immutable internal release identifier>
REPWISE_POSE_SAMPLE_FPS=10
```

The configured path must resolve inside the worker container. The sampling rate
must be greater than zero and no greater than 30 frames per second. Changing the
model file, checksum, model identifier, sampling rate, or adapter behavior
requires a new evaluation record and rollout decision.

## Processing behavior

The `repwise.pose.infer` task performs the following operations:

1. Download the normalized private video into an isolated temporary directory.
2. Verify that the model exists and matches `REPWISE_POSE_MODEL_SHA256`.
3. Sample frames at `REPWISE_POSE_SAMPLE_FPS` with FFmpeg.
4. Run MediaPipe Pose Landmarker in `VIDEO` mode for one person.
5. Write deterministic private JSON containing timestamps and all 33 landmarks.
6. Upload the inference artifact to private object storage and return its
   SHA-256, frame counts, and model identity.

Frames without a detected pose remain in the sequence with all landmarks marked
missing. If no sampled frame contains a pose, the task fails and no evidence
report is produced.

## Failure behavior

| Code | Meaning | Required operator response |
| --- | --- | --- |
| `model_not_configured` | Model path or checksum is absent | Configure both values and redeploy the worker |
| `model_not_found` | The configured path is not a readable file | Correct the read-only mount or configured path |
| `model_checksum_mismatch` | File content differs from the approved digest | Stop processing and restore the approved model artifact |
| `runtime_unavailable` | MediaPipe is not installed in the worker image | Deploy the worker image built with the `inference` dependency |
| `frame_extraction_failed` | FFmpeg could not decode or sample the video | Inspect media preflight output and worker diagnostics |
| `no_frames` | Sampling produced no frames | Reject the media and retain the stable failure reason |
| `inference_failed` | MediaPipe returned an unexpected runtime failure | Quarantine the job, record model/runtime versions, and investigate |
| `no_pose_detected` | No sampled frame contained a person pose | Mark the analysis not assessable and request a new recording |

Errors must not include media bytes, signed URLs, access tokens, customer names,
or storage credentials.

## Rollout and rollback

Deploy a new model to a canary worker cohort with an immutable image and model
record. Compare coverage, abstention, latency, resource use, and every enabled
exercise check against the approved evaluation baseline. Promote only after the
release owner signs the comparison.

Rollback restores the last-known-good worker image and matching model mount.
Historical reports remain unchanged because each artifact records its source,
model, schema, and rule identity.
