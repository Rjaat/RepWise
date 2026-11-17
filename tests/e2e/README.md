# End-to-end verification

Cross-service acceptance coverage verifies user outcomes across the browser,
API, queue, private object storage, media processing, analysis, and report
publication boundaries.

The executable synthetic upload-to-report check is documented in
[`docs/runbooks/upload-report-journey.md`](../../docs/runbooks/upload-report-journey.md).
Guided-camera physical-device requirements are documented in
[`docs/guided-capture-device-checklist.md`](../../docs/guided-capture-device-checklist.md).

Test media must be generated or explicitly approved for repository and CI use.
Customer recordings, signed URLs, access tokens, and production-derived data are
prohibited. Automated browser emulation does not satisfy physical-device or
real-participant release evidence.
