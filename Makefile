.PHONY: up down build restart logs migrate shell-backend shell-db

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build --no-cache

restart:
	docker compose restart backend

logs:
	docker compose logs -f backend

logs-all:
	docker compose logs -f

migrate:
	docker compose exec backend alembic upgrade head

migration:
	docker compose exec backend alembic revision --autogenerate -m "$(MSG)"

shell-backend:
	docker compose exec backend sh

shell-db:
	docker compose exec postgres psql -U sig_user -d sig_v2

redis-cli:
	docker compose exec redis redis-cli

test:
	docker compose exec backend pytest -v
