PROJECT_ID ?= orderflow-451220
REPO ?= my-repo
APP_NAME ?= my-app
SERVICE_NAME ?= pult-app
REGION ?= us-central1
IMAGE ?= us-central1-docker.pkg.dev/$(PROJECT_ID)/$(REPO)/$(APP_NAME)
PYTHON ?= ./.venv/bin/python
MANAGE ?= $(PYTHON) src/manage.py

TAILWIND ?= bin/tailwindcss
TAILWIND_VERSION ?= v4.1.18

.PHONY: help dev dev-detached down down-clean down-reset ps logs logs-db shell manage migrate createsuperuser bootstrap-local init-local dev-bootstrap dev-refresh dev-refresh-ui test check lint format ruff-check ruff-format build push deploy tw-install tw-watch tw-build

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*##"; printf "\nAvailable commands:\n\n"} /^[a-zA-Z0-9_.-]+:.*##/ { printf "  %-18s %s\n", $$1, $$2 } END { print "" }' $(MAKEFILE_LIST)

dev: ## Start Docker Compose in foreground
	docker compose up --build

dev-detached: ## Start Docker Compose in background
	docker compose up -d --build

down: ## Stop Docker Compose services
	docker compose down

down-clean: ## Stop services and remove orphan containers
	docker compose down --remove-orphans

down-reset: ## Full reset: stop services and remove DB volume (destructive)
	docker compose down -v --remove-orphans

ps: ## Show Docker Compose services status
	docker compose ps

logs: ## Follow web service logs
	docker compose logs -f web

logs-db: ## Follow database logs
	docker compose logs -f db

shell: ## Open Django shell in container
	docker compose run --rm web python src/manage.py shell

manage: ## Run arbitrary Django command in container: make manage cmd="check"
	@test -n "$(cmd)" || (echo 'Usage: make manage cmd="check --deploy"'; exit 1)
	docker compose run --rm web python src/manage.py $(cmd)

migrate: ## Apply migrations and sync apps without migrations (user_settings/ui)
	docker compose run --rm web python src/manage.py migrate --run-syncdb

createsuperuser: ## Create Django superuser (interactive)
	docker compose run --rm web python src/manage.py createsuperuser

bootstrap-local: ## Seed local admin + base catalog + sample production orders
	docker compose run --rm web python src/manage.py bootstrap_local \
		--username "$${LOCAL_BOOTSTRAP_USERNAME:-local_admin}" \
		--password "$${LOCAL_BOOTSTRAP_PASSWORD:-local-pass-12345}" \
		--orders "$${LOCAL_BOOTSTRAP_ORDERS:-10}"

init-local: migrate bootstrap-local ## Prepare database and local test data

dev-bootstrap: down-clean dev-detached init-local ## Clean boot for local development

dev-refresh: dev-bootstrap ## Recommended full local refresh (backend flow)

dev-refresh-ui: down-clean dev-detached tw-build init-local ## Full refresh including Tailwind build

test: ## Run tests in local virtualenv
	PYTHONPATH=src $(PYTHON) -m pytest 2>/dev/null || PYTHONPATH=src $(MANAGE) test apps.production apps.catalog apps.accounts apps.materials

check: ## Run Django checks in local virtualenv
	PYTHONPATH=src $(MANAGE) check

lint: ## Run Ruff lint in local virtualenv
	$(PYTHON) -m ruff check src

format: ## Format code with Ruff formatter in local virtualenv
	$(PYTHON) -m ruff format .

# Use ruff from PATH (activate your venv first).
ruff-check: ## Run Ruff lint from PATH
	ruff check src

ruff-format: ## Run Ruff format from PATH
	ruff format src

build: ## Build deployment image
	docker build --platform=linux/amd64 -t $(IMAGE) .

push: build ## Push deployment image
	docker push $(IMAGE)

deploy: push ## Deploy to Cloud Run
	gcloud run deploy $(SERVICE_NAME) \
		--image=$(IMAGE) \
		--region=$(REGION) \
		--allow-unauthenticated

# Tailwind CSS (standalone CLI). Run make tw-install once to download the binary.
tw-install: ## Download Tailwind standalone binary
	@mkdir -p bin && \
	U=$$(uname -s) && A=$$(uname -m) && \
	if [ "$$U" = "Darwin" ]; then \
		[ "$$A" = "arm64" ] && F=tailwindcss-macos-arm64 || F=tailwindcss-macos-x64; \
	elif [ "$$U" = "Linux" ]; then \
		[ "$$A" = "aarch64" ] || [ "$$A" = "arm64" ] && F=tailwindcss-linux-arm64 || F=tailwindcss-linux-x64; \
	else echo "Unsupported OS: $$U"; exit 1; fi && \
	echo "Downloading $$F..." && \
	curl -fsSL "https://github.com/tailwindlabs/tailwindcss/releases/download/$(TAILWIND_VERSION)/$$F" -o $(TAILWIND) && \
	chmod +x $(TAILWIND) && echo "Installed $(TAILWIND)"

tw-watch: tw-build ## Watch and rebuild CSS on changes
	$(TAILWIND) -i frontend/assets/tailwind/input.css -o frontend/static/css/app.css --watch

tw-build: ## Build production CSS once
	@test -f $(TAILWIND) || (echo "Run: make tw-install" && exit 1)
	$(TAILWIND) -i frontend/assets/tailwind/input.css -o frontend/static/css/app.css --minify
