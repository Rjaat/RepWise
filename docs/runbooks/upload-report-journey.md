# Upload-to-report journey

This integration check exercises Redis, private MinIO storage, FFmpeg
normalization, Celery task execution, pose artifact validation, squat
segmentation, and immutable report publication. It uses generated black video
and generated landmarks; it never reads participant or customer media.

```bash
make services-up
make journey-smoke
make services-down
```

The runner uploads a synthetic source, verifies and normalizes it, persists a
versioned pose artifact, segments one squat and publishes an immutable report.
It then injects an invalid segmentation checksum and requires a rejection. The
report task is retried with the same analysis ID and must return the same key,
checksum and rep count rather than creating a duplicate.

If interrupted, run `make services-down`. Named development volumes remain.
Objects under `e2e/` contain only generated fixtures and may be removed through
the MinIO console. Do not run this check with customer recordings.

## Failure triage

- `checksum mismatch`: confirm the prior artifact completed and its file hash,
  not its embedded semantic checksum, was passed downstream.
- `task timeout`: inspect `docker compose -f infra/compose.yaml logs media-worker`
  and confirm Redis and MinIO are healthy.
- `decoder failure`: run `ffmpeg -version` in the worker and rebuild services.
- `changed retry result`: stop release work; deterministic report publication is
  required before retrying production jobs.
