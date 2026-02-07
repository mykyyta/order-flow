PROJECT_ID ?= orderflow-451220
REPO ?= my-repo
APP_NAME ?= my-app
SERVICE_NAME ?= orderflow-app
REGION ?= us-central1
IMAGE ?= us-central1-docker.pkg.dev/$(PROJECT_ID)/$(REPO)/$(APP_NAME)
PYTHON ?= ./.venv/bin/python

TAILWIND ?= bin/tailwindcss

.PHONY: dev dev-detached down logs migrate shell test check lint format ruff-check ruff-format build push deploy tw-install tw-watch tw-build

dev:
	docker compose up --build

dev-detached:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f web

migrate:
	docker compose run --rm web python manage.py migrate

shell:
	docker compose run --rm web python manage.py shell

test:
	$(PYTHON) manage.py test orders

check:
	$(PYTHON) manage.py check

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

# Use ruff from PATH (activate your venv with ruff first)
ruff-check:
	ruff check .

ruff-format:
	ruff format .

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
	$(TAILWIND) -i static/css/input.css -o static/css/app.css --watch

tw-build:
	@test -f $(TAILWIND) || (echo "Run: make tw-install" && exit 1)
	$(TAILWIND) -i static/css/input.css -o static/css/app.css --minify
