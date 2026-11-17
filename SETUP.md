# Run RepWise on any machine

The portable stack runs the web application, API, migration job, PostgreSQL,
Redis, private media storage, and analysis worker in Docker. Use it for local
evaluation and trusted self-hosted development. It is not approved for an
internet-facing production deployment.

## Requirements

- Git
- Docker Engine or Docker Desktop with Compose v2
- At least 4 GB free memory and 8 GB free disk space

## Start

```bash
git clone https://github.com/Rjaat/RepWise.git
cd RepWise
./scripts/repwise setup
```

The first build downloads container images and can take several minutes. Open
`http://127.0.0.1:8180` after every service reports healthy. Setup creates an
ignored `.env.portable` file with random local secrets and applies database
migrations automatically.

Useful commands:

```bash
./scripts/repwise status
./scripts/repwise logs
./scripts/repwise down
./scripts/repwise update
```

Data persists in named Docker volumes across ordinary restarts. To delete all
local RepWise data, first stop the stack and then explicitly run:

```bash
docker compose --env-file .env.portable -f compose.portable.yaml down --volumes
```

## Access from another device

Edit `.env.portable`, set `REPWISE_PUBLIC_HOST` to the host machine's LAN IP, and
set `REPWISE_BIND_ADDRESS=0.0.0.0`; then run `./scripts/repwise up`. Allow the
configured web and media ports through the host firewall only on a trusted
private network. The configured internal development identity does not provide
an acceptable authentication boundary for public exposure.

## Configuration

`portable.env.example` documents every portable setting. Payments remain
disabled, candidate exercise checks remain disabled, media stays private, and
the beta release evidence gate remains blocked until its real approvals exist.
