.PHONY: dev prod logs stop shell migrate test

dev:
	docker compose -f docker-compose.yml -f docker-compose.override.yml up --build

prod:
	docker compose up -d --build

logs:
	docker compose logs -f

stop:
	docker compose down

shell:
	docker compose exec backend bash

migrate:
	docker compose exec backend python -m alembic upgrade head

test:
	docker compose -f docker-compose.test.yml up -d
	pytest tests/backend/ --cov=backend --cov-report=term-missing
	npx playwright test tests/e2e/
	docker compose -f docker-compose.test.yml down
