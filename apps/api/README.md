# RepWise API

FastAPI application for RepWise. Run from the repository root with
`make dev-api`; verify with `make check`.

`/health` is process liveness and never depends on PostgreSQL. `/ready` checks
the database and returns `503` when the API should receive no new traffic.
Every response carries a validated or generated `x-request-id`.

Run migrations from the repository root:

```bash
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api alembic -c apps/api/alembic.ini downgrade -1
```

Production and staging use `postgresql+psycopg`. The `sqlite+aiosqlite` driver is
accepted only for isolated migration and repository tests.
