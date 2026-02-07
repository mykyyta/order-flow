PROJECT_ID ?= orderflow-451220
REPO ?= my-repo
APP_NAME ?= my-app
SERVICE_NAME ?= orderflow-app
REGION ?= us-central1
IMAGE ?= us-central1-docker.pkg.dev/$(PROJECT_ID)/$(REPO)/$(APP_NAME)
PYTHON ?= ./.venv/bin/python

.PHONY: dev dev-detached down logs migrate shell test check lint format build push deploy

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

build:
	docker build --platform=linux/amd64 -t $(IMAGE) .

push: build
	docker push $(IMAGE)

deploy: push
	gcloud run deploy $(SERVICE_NAME) \
		--image=$(IMAGE) \
		--region=$(REGION) \
		--allow-unauthenticated
