.PHONY: dev seed test lint typecheck sync down up logs ps clean

# Boot all containers locally (api + worker + redis + postgres + frontend)
dev:
	docker compose up --build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps

# Seed the parquet cache with the NIFTY-50 universe (needs worker stack up)
seed:
	docker compose run --rm worker python -m scripts.seed_universe

# Daily incremental sync (append new trading days)
sync:
	docker compose run --rm worker python -m scripts.sync_daily

# Cross-source data integrity check
validate-data:
	docker compose run --rm worker python -m scripts.validate_data

# Test / quality
test:
	uv run pytest

lint:
	uv run ruff check app tests scripts

format:
	uv run ruff format app tests scripts

typecheck:
	uv run mypy app

# Locks + installs
install:
	uv sync

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache
