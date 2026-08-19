# Makefile
.PHONY: help build run stop logs clean shell

help:
	@echo "Available commands:"
	@echo "  make build    - Build Docker image"
	@echo "  make run      - Run container in background"
	@echo "  make stop     - Stop container"
	@echo "  make logs     - View container logs"
	@echo "  make clean    - Remove container and image"
	@echo "  make shell    - Open shell in container"

build:
	docker-compose build

run:
	docker-compose up -d
	@echo "✅ Application running at http://localhost:5004"

stop:
	docker-compose down

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	docker rmi ldap-phonebook-app 2>/dev/null || true

shell:
	docker-compose exec ldap-phonebook /bin/bash

restart: stop run