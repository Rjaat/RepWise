# RepWise API

FastAPI application for RepWise. Run from the repository root with
`make dev-api`; verify with `make check`.

`/health` is process liveness and never depends on PostgreSQL. `/ready` checks
the database and returns `503` when the API should receive no new traffic.
Every response carries a validated or generated `x-request-id`.

## Direct uploads

`POST /v1/uploads` accepts MP4, QuickTime or WebM objects up to 250 MiB and
returns a 15-minute private-storage PUT URL. Send the expected byte size and a
lowercase SHA-256 value, then include the same checksum as
`x-amz-meta-sha256` on the storage PUT. `POST /v1/uploads/{id}/complete`
verifies both stored values before creating one analysis job. Repeating either
initiation with the same `Idempotency-Key` or completion returns the existing
resource. `DELETE /v1/uploads/{id}` cancels an incomplete upload.

These proof-stage endpoints use `Authorization: Bearer <user-uuid>` as an
internal identity boundary. It provides ownership isolation but is not a
production authentication mechanism. PR-19 replaces it with verified accounts
and secure sessions before private alpha.

Run migrations from the repository root:

```bash
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api alembic -c apps/api/alembic.ini downgrade -1
```

Production and staging use `postgresql+psycopg`. The `sqlite+aiosqlite` driver is
accepted only for isolated migration and repository tests.
