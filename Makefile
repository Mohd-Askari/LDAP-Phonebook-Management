# Makefile for CoreIP LDAP Phonebook Management
.PHONY: help run stop logs build clean test install-base

help:
	@echo "=================================================================="
	@echo "CoreIP LDAP & Phonebook Management - Command Reference"
	@echo "=================================================================="
	@echo "  make run          - Start centralized LDAP & Phonebook (Docker)"
	@echo "  make stop         - Stop running containers"
	@echo "  make restart      - Restart containers"
	@echo "  make logs         - Stream container logs"
	@echo "  make build        - Rebuild Docker image"
	@echo "  make test         - Run Phase 1 & regression test suite"
	@echo "  make install-base - Run native Linux installer (Debian/Ubuntu)"
	@echo "=================================================================="

# --- Primary Docker Commands (All-In-One Centralized) ---
run:
	docker compose up -d
	@echo "✅ CoreIP LDAP & Phonebook running!"
	@echo "🌐 Web GUI:  http://localhost:5004"
	@echo "📇 LDAP Port: localhost:389"

stop:
	docker compose down

restart: stop run

logs:
	docker compose logs -f

build:
	docker compose build

clean:
	docker compose down -v
	docker rmi coreip-ldap-phonebook:latest 2>/dev/null || true

# --- Testing ---
test:
	./venv/bin/python3 -m unittest discover -s tests

# --- Base Server Installation ---
install-base:
	@sudo bash install-base-server.sh
