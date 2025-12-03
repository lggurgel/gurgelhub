.PHONY: up down restart logs shell create-admin test migrate migrate-down

# Docker Compose commands
up:
	docker-compose -f docker/docker-compose.yml up -d

down:
	docker-compose -f docker/docker-compose.yml down

restart: down up

logs:
	docker-compose -f docker/docker-compose.yml logs -f

shell:
	docker-compose -f docker/docker-compose.yml exec web bash

# Application commands
create-admin:
	@echo "Running create_admin script inside web container..."
	@docker-compose -f docker/docker-compose.yml exec web python scripts/create_admin.py

test:
	docker-compose -f docker/docker-compose.yml exec web pytest

# Database migrations
migrate:
	@echo "Applying database migrations..."
	@docker-compose -f docker/docker-compose.yml exec web alembic upgrade head

migrate-down:
	@echo "Rolling back last migration..."
	@docker-compose -f docker/docker-compose.yml exec web alembic downgrade -1
