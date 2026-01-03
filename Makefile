COMPOSE = docker compose -f infra/docker-compose.yml

.PHONY: up down logs clean

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

clean:
	$(COMPOSE) down -v
