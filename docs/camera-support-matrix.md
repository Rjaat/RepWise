# Camera capability matrix

Validated 2026-11-17 against the automated capability harness. Physical-device
validation remains required in PR-18 before declaring a browser supported.

| Browser family | Preview request | Preferred recording | Degraded path |
| --- | --- | --- | --- |
| Chromium desktop/Android | `getUserMedia`, environment preference | VP9 WebM, then VP8 WebM | Generic WebM, MP4, then replay-only/upload |
| Safari macOS/iOS | `getUserMedia`, environment preference | MP4 when exposed | Replay-only/upload when no MIME candidate is supported |
| Firefox desktop/Android | `getUserMedia`, environment preference | VP9/VP8 WebM | Generic WebM, then replay-only/upload |

The application queries `MediaRecorder.isTypeSupported`; it does not infer
support from the user-agent string. Permission denial, missing devices, busy
devices and unsupported APIs have separate recovery copy. Device labels are
shown only after permission. Telemetry records the result category, selected
MIME type and camera count, never frames, device labels or device identifiers.
