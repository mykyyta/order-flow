PROJECT_ID ?= orderflow-451220
REPO ?= my-repo
APP_NAME ?= my-app
SERVICE_NAME ?= pult-app
REGION ?= us-central1
IMAGE ?= us-central1-docker.pkg.dev/$(PROJECT_ID)/$(REPO)/$(APP_NAME)
PYTHON ?= ./.venv/bin/python
MANAGE ?= $(PYTHON) src/manage.py

TAILWIND ?= bin/tailwindcss

.PHONY: dev dev-detached down down-clean logs migrate bootstrap-local init-local dev-bootstrap shell test check lint format ruff-check ruff-format build push deploy tw-install tw-watch tw-build dev-refresh

dev:
	docker compose up --build

dev-detached:
	docker compose up -d --build

down:
	docker compose down

down-clean:
	docker compose down --remove-orphans

logs:
	docker compose logs -f web

migrate:
	docker compose run --rm web python src/manage.py migrate --run-syncdb

bootstrap-local:
	docker compose run --rm web python src/manage.py bootstrap_local \
		--username "$${LOCAL_BOOTSTRAP_USERNAME:-local_admin}" \
		--password "$${LOCAL_BOOTSTRAP_PASSWORD:-local-pass-12345}" \
		--orders "$${LOCAL_BOOTSTRAP_ORDERS:-10}"

init-local: migrate bootstrap-local

dev-bootstrap: down-clean dev-detached init-local

shell:
	docker compose run --rm web python src/manage.py shell

test:
	PYTHONPATH=src $(PYTHON) -m pytest 2>/dev/null || PYTHONPATH=src $(MANAGE) test apps.production apps.catalog apps.accounts apps.materials

check:
	PYTHONPATH=src $(MANAGE) check

lint:
	$(PYTHON) -m ruff check src

format:
	$(PYTHON) -m ruff format .

# Use ruff from PATH (activate your venv with ruff first)
ruff-check:
	ruff check src

ruff-format:
	ruff format src

build:
	docker build --platform=linux/amd64 -t $(IMAGE) .

push: build
	docker push $(IMAGE)

deploy: push
	gcloud run deploy $(SERVICE_NAME) \
		--image=$(IMAGE) \
		--region=$(REGION) \
		--allow-unauthenticated

# Tailwind CSS (standalone CLI). Run make tw-install once to download the binary.
TAILWIND_VERSION ?= v4.1.18
tw-install:
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

tw-watch: tw-build
	$(TAILWIND) -i frontend/assets/tailwind/input.css -o frontend/static/css/app.css --watch

tw-build:
	@test -f $(TAILWIND) || (echo "Run: make tw-install" && exit 1)
	$(TAILWIND) -i frontend/assets/tailwind/input.css -o frontend/static/css/app.css --minify

# Full refresh: restart containers, rebuild CSS, run migrations.
dev-refresh: down dev-detached tw-build migrate
