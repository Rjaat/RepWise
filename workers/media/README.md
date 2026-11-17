# Media worker

The worker image includes FFmpeg/ffprobe for integrity checks and normalization.
`repwise_api.media_cli` validates the source checksum and media metadata, applies
display rotation, removes audio and metadata, preserves variable presentation
timestamps, and writes a source-to-normalized frame map.

```bash
uv run --project apps/api python -m repwise_api.media_cli input.mov normalized.mp4 \
  --sha256 <lowercase-sha256> --manifest normalized.json
```

Rejected media returns a stable failure code without exposing signed URLs or
media bytes in logs. Fixture videos must be generated or explicitly licensed;
customer recordings never belong in the repository.
