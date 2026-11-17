# Camera capability matrix

The automated capability harness was last executed on 17 November 2026.
Physical-device results remain pending; no browser or device in this document
is approved for validated beta until the
[guided-capture checklist](guided-capture-device-checklist.md) records a signed
result with exact hardware, operating-system, and browser versions.

| Browser family | Requested preview | Recorder selection order | Degraded behavior |
| --- | --- | --- | --- |
| Chromium desktop/Android | `getUserMedia` with rear-camera preference | VP9 WebM, then VP8 WebM | Generic WebM, MP4, then replay-only or file upload |
| Safari macOS/iOS | `getUserMedia` with rear-camera preference | MP4 when the browser exposes it | Replay-only or file upload when no candidate MIME type is supported |
| Firefox desktop/Android | `getUserMedia` with rear-camera preference | VP9 WebM, then VP8 WebM | Generic WebM, then replay-only or file upload |

The application queries `MediaRecorder.isTypeSupported`; it does not infer
support from the user-agent string. Permission denial, missing devices, busy
devices and unsupported APIs have separate recovery copy. Device labels are
shown only after permission. Telemetry records the result category, selected
MIME type and camera count, never frames, device labels or device identifiers.
