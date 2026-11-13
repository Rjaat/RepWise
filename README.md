# RepWise

RepWise is a private-by-default exercise video analysis application that links
supported movement feedback to visible evidence. The initial product focuses
on controlled capture, explicit assessment coverage and honest uncertainty.

Read the [end-to-end plan](RepWise_E2E_Plan.md) and
[UI/UX specification](RepWise_UI_UX_README.md) before changing product scope.

## Prerequisites

- Node.js 22.22 and pnpm 10.12.1
- Python 3.13 and uv 0.9+
- Docker with Compose (required when local services arrive in PR-05)

## Setup

```bash
cp .env.example .env
corepack enable
pnpm install
uv sync --project apps/api
```

No value in `.env.example` is a credential. Keep all local secrets in `.env`,
which Git ignores.

## Run the shells

In separate terminals:

```bash
make dev-web
make dev-api
```

- Web: <http://localhost:5173>
- API health: <http://127.0.0.1:8010/health>

The browser shell intentionally contains no simulated analysis data. The API
health response reports only process readiness until real dependencies are
introduced.

## Verify a change

```bash
make check
```

This runs formatting-independent lint checks, static type checks, unit tests
and the production web build. Pull requests must keep this command green.

## Workspace

```text
apps/web                 React and browser capture
apps/api                 FastAPI HTTP application
workers/media            Media jobs (introduced in PR-09)
workers/analysis         Analysis jobs (introduced in PR-10)
packages/contracts       Shared/generated contracts
packages/ui              RepWise design system
packages/exercise-contracts  Versioned assessment definitions
infra                    Local and deployment configuration
tests/e2e                Cross-service browser journeys
```

Empty future workspace directories are represented by README files so their
intended ownership remains clear without shipping placeholder runtime code.
