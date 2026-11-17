# Media worker

The media worker image contains FFmpeg, ffprobe, and the optional MediaPipe
runtime. It validates uploaded media, creates a normalized private video, and
runs checksum-pinned pose inference.

`repwise_api.media_cli` validates the source checksum and media metadata, applies
display rotation, removes audio and container metadata, preserves variable
presentation timestamps, and writes a source-to-normalized frame map:

```bash
uv run --project apps/api python -m repwise_api.media_cli input.mov normalized.mp4 \
  --sha256 <lowercase-sha256> --manifest normalized.json
```

Rejected media returns a stable failure code without exposing signed URLs or
media bytes in logs. Fixture videos must be generated or explicitly licensed;
customer recordings never belong in the repository.

Pose inference requires an operator-supplied model mounted read-only into the
worker. Configuration and provenance requirements are defined in
[`docs/pose-model.md`](../../docs/pose-model.md). The worker refuses inference
when the model is missing or its SHA-256 differs from the configured value.
