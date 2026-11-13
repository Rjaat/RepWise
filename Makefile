.PHONY: setup dev-web dev-api services-up services-down services-smoke contracts-validate format lint typecheck test build check

export UV_CACHE_DIR := .cache/uv

setup:
	pnpm install --frozen-lockfile
	uv sync --project apps/api --frozen

dev-web:
	pnpm dev

dev-api:
	uv run --project apps/api uvicorn repwise_api.main:app --host 127.0.0.1 --port $${REPWISE_API_PORT:-8010} --reload

services-up:
	docker compose -f infra/compose.yaml up -d --build --wait

services-down:
	docker compose -f infra/compose.yaml down

services-smoke:
	uv run --project apps/api python -m repwise_api.smoke

contracts-validate:
	PYTHONPATH=packages/exercise-contracts/src uv run --project apps/api python -m repwise_exercise_contracts.cli packages/exercise-contracts/contracts/*.json

format:
	pnpm --filter @repwise/web format
	uv run --project apps/api ruff format .

lint:
	pnpm lint
	uv run --project apps/api ruff check apps/api

typecheck:
	pnpm typecheck
	uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src
	PYTHONPATH=packages/exercise-contracts/src uv run --project apps/api mypy --strict packages/exercise-contracts/src packages/exercise-contracts/tests

test:
	pnpm test
	uv run --project apps/api pytest apps/api/tests
	PYTHONPATH=packages/exercise-contracts/src uv run --project apps/api pytest -o addopts='--strict-markers --strict-config' packages/exercise-contracts/tests

build:
	pnpm build

check: contracts-validate lint typecheck test build
