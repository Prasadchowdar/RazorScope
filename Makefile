.PHONY: up down migrate ch-schema seed test-e2e logs build

# Copy .env.example to .env if it doesn't exist
.env:
	cp .env.example .env

up: .env
	docker compose up -d --wait

down:
	docker compose down -v

migrate:
	docker compose run --rm flyway migrate

ch-schema:
	bash scripts/apply-clickhouse-schema.sh

seed:
	@export $$(cat .env | xargs) && psql "$$DATABASE_URL" -f scripts/seed-dev-merchant.sql

test-e2e:
	bash scripts/test-e2e.sh

logs:
	docker compose logs -f webhook-receiver

logs-worker:
	docker compose logs -f metric-worker

logs-api:
	docker compose logs -f api

test-api:
	cd services/api && python -m pytest tests/ -v

build:
	cd services/webhook-receiver && go build -o webhook-receiver ./cmd/server

dev:
	@export $$(cat .env | xargs) && cd services/webhook-receiver && go run ./cmd/server
