# Local infrastructure

RepWise runs PostgreSQL, Redis, private S3-compatible media storage and a CPU
media worker as isolated containers. Ports bind to loopback only; the media
bucket denies anonymous access.

Copy `.env.example` to `.env` and replace every `change-me` value before use.
The checked-in fallbacks are development-only and must never be used outside a
local machine.

```bash
make services-up
make services-smoke
make services-down
```

`services-up` builds the worker, waits for dependency health checks and creates
the private bucket idempotently. `services-smoke` submits a JSON-only Celery job,
waits for the result and deletes that result. Named volumes preserve local data;
ordinary shutdown does not delete them.

Local endpoints:

- PostgreSQL: `127.0.0.1:55432`
- Redis: `127.0.0.1:56379`
- Media API: `http://127.0.0.1:59000`
- Media console: `http://127.0.0.1:59001`

To remove local data intentionally, run `docker compose -f infra/compose.yaml
down --volumes` after confirming no needed local recordings or metadata remain.
