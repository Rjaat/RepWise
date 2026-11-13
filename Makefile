.PHONY: setup dev-web dev-api format lint typecheck test build check

export UV_CACHE_DIR := .cache/uv

setup:
	pnpm install --frozen-lockfile
	uv sync --project apps/api --frozen

dev-web:
	pnpm dev

dev-api:
	uv run --project apps/api uvicorn repwise_api.main:app --host 127.0.0.1 --port $${REPWISE_API_PORT:-8010} --reload

format:
	pnpm --filter @repwise/web format
	uv run --project apps/api ruff format .

lint:
	pnpm lint
	uv run --project apps/api ruff check apps/api

typecheck:
	pnpm typecheck
	uv run --project apps/api mypy apps/api/src

test:
	pnpm test
	uv run --project apps/api pytest apps/api/tests

build:
	pnpm build

check: lint typecheck test build
