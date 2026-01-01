up:
	docker compose -f infra/docker-compose.yml up -d

down:
	docker compose -f infra/docker-compose.yml down

reset-db:
	docker compose -f infra/docker-compose.yml down -v
