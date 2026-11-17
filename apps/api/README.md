# RepWise API

The RepWise API is a FastAPI service responsible for authentication,
authorization, upload coordination, analysis status, report feedback, history,
privacy operations, usage limits, and administrative controls.

## Run and verify

From the repository root:

```bash
make dev-api
make check
```

`GET /health` reports process liveness without querying PostgreSQL. `GET /ready`
checks required dependencies and returns `503` when the service should not
receive new traffic. Every response includes a validated or generated
`x-request-id` header.

Interactive OpenAPI documentation is available at `/docs` in development.
The route implementation and generated OpenAPI document are authoritative for
request and response fields.

## Authentication and authorization

The API exchanges a signed identity assertion for short-lived access tokens and
rotating refresh sessions through `/v1/auth/exchange` and `/v1/auth/refresh`.
Logout supports one session or all sessions. Owner, reviewer, support, and
administrator boundaries are enforced by route dependencies and covered by
authorization tests.

`REPWISE_ALLOW_LEGACY_BEARER_IDENTITY` exists only for controlled development
compatibility. Production configuration rejects startup while that setting is
enabled. Production authentication secrets must contain at least 32 characters.

## Direct uploads

`POST /v1/uploads` accepts MP4, QuickTime, or WebM media up to 250 MiB and
returns a 15-minute private-storage PUT URL. The request supplies the expected
byte size and lowercase SHA-256. The storage PUT must repeat that digest in
`x-amz-meta-sha256`.

`POST /v1/uploads/{upload_id}/complete` verifies stored size and checksum before
creating one analysis job and dispatching media preflight. Reusing the same
`Idempotency-Key` returns the existing resource instead of creating duplicate
work. `DELETE /v1/uploads/{upload_id}` cancels an incomplete upload. Upload and
analysis resources are owner-scoped.

## Database migrations

Apply or roll back migrations from the repository root:

```bash
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api alembic -c apps/api/alembic.ini downgrade -1
```

Staging and production use `postgresql+psycopg`. The
`sqlite+aiosqlite` driver is limited to isolated repository and migration tests.
Deploy migrations before application instances that depend on the new schema;
verify downgrade compatibility in the pull request that introduces a migration.

## Configuration

Settings use the `REPWISE_` prefix and are validated at process startup. Copy
`.env.example` to `.env` for local development. Do not commit `.env`, access
tokens, signing secrets, private media URLs, or storage credentials.
