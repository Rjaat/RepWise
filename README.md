# RepWise

RepWise is a privacy-first web application that analyzes exercise recordings and
links supported movement feedback to visible evidence. The product emphasizes
controlled capture, explicit assessment coverage, immutable analysis versions,
and honest uncertainty.

## Project status

The repository contains the web application, API, database migrations, private
media storage, asynchronous workers, MediaPipe pose inference, versioned
exercise contracts, evidence reports, privacy workflows, operational controls,
and release-readiness gates.

RepWise has not completed the real-world evaluation and legal approval required
for a public validated-beta release. The
[validated-beta runbook](docs/releases/validated-beta-runbook.md) defines the
remaining evidence and approval requirements.

## Run RepWise

The portable Docker environment is the recommended evaluation path:

```bash
git clone https://github.com/Rjaat/RepWise.git
cd RepWise
./scripts/repwise setup
```

Open <http://127.0.0.1:8180> after all containers report healthy. Setup creates
local secrets, applies database migrations, and starts the web, API, database,
queue, private storage, and worker services. See [SETUP.md](SETUP.md) for
configuration, lifecycle commands, network access, and data removal.

## Native development

Required toolchains:

- Node.js 22.22 and pnpm 10.12.1
- Python 3.13 and uv 0.9 or newer
- Docker with Compose v2 for service integration

Install dependencies and create local configuration:

```bash
cp .env.example .env
corepack enable
make setup
```

Replace every `change-me` value in `.env`. Run the frontend and API in separate
terminals:

```bash
make dev-web
make dev-api
```

The web application is available at <http://127.0.0.1:5173>. API liveness is
available at <http://127.0.0.1:8010/health>; dependency readiness is available
at <http://127.0.0.1:8010/ready>.

## Quality gate

Run the repository-wide pull-request gate with:

```bash
make check
```

This validates exercise contracts, lints TypeScript and Python, performs strict
type checking, runs frontend, API, and contract tests, and builds production
frontend assets. See [CONTRIBUTING.md](CONTRIBUTING.md) for review and identity
requirements.

## Repository structure

| Path | Responsibility |
| --- | --- |
| `apps/web` | React application, guided capture, uploads, reports, and account workflows |
| `apps/api` | FastAPI routes, persistence, authentication, authorization, and job coordination |
| `workers/media` | FFmpeg normalization and MediaPipe pose-inference runtime |
| `workers/analysis` | Pose artifact validation, segmentation, and report publication |
| `packages/ui` | Shared design tokens and accessible UI primitives |
| `packages/exercise-contracts` | Versioned assessment definitions and validation tools |
| `packages/contracts` | Generated cross-process API contracts |
| `infra` | Local service orchestration and infrastructure configuration |
| `tests/e2e` | Cross-service acceptance journeys and test guidance |
| `docs` | Operational, evaluation, model, device, and release documentation |

## Documentation

- [Documentation index](docs/README.md): audience, authority, and purpose of each document
- [Product and engineering specification](RepWise_E2E_Plan.md): scope, architecture, evidence policy, and delivery history
- [Interface specification](RepWise_UI_UX_README.md): visual system, responsive behavior, accessibility, and screen requirements
- [API guide](apps/api/README.md): service behavior, authentication, uploads, and migrations
- [Pose model operations](docs/pose-model.md): model provenance, configuration, and inference behavior
- [Release evaluation runbook](docs/evaluation/release-evaluation-runbook.md): real-world evidence and pass criteria

If documents disagree, executable contracts and migrations define runtime
behavior; approved release evidence determines whether a capability may be
enabled or advertised.

## Privacy and product boundaries

- Recordings and derived artifacts are private by default.
- Customer media and credentials must never be committed to the repository.
- Reports distinguish assessed, uncertain, and not-assessable outcomes.
- Historical reports remain pinned to source, model, rule, and schema versions.
- RepWise does not provide medical diagnosis, injury prediction, safety
  certification, or a universal form score.
