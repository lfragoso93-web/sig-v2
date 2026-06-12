.PHONY: up down logs restart migrate test lint

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

restart: down up

migrate:
	docker compose exec backend alembic upgrade head

# Roda a suite de testes dentro do container backend
test:
	docker compose exec backend bash -c \
	  "pip install -q -r requirements-test.txt && pytest tests/ -v --tb=short"

# Lint com ruff (opcional, instale com pip install ruff)
lint:
	docker compose exec backend ruff check app/
