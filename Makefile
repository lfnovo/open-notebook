.PHONY: run check ruff database lint docker-build docker-push docker-buildx-prepare docker-release api

# Get version from pyproject.toml
VERSION := $(shell grep -m1 version pyproject.toml | cut -d'"' -f2)
IMAGE_NAME := lfnovo/open_notebook

PLATFORMS=linux/amd64,linux/arm64

database:
	docker compose up -d surrealdb

run:
	uv run --env-file .env streamlit run app_home.py

lint:
	uv run python -m mypy .

ruff:
	ruff check . --fix

# buildx config for multi-plataform
docker-buildx-prepare:
	docker buildx create --use --name multi-platform-builder || true

# multi-plataform build with buildx
docker-build: docker-buildx-prepare
	docker buildx build --pull \
		--platform $(PLATFORMS) \
		-t $(IMAGE_NAME):$(VERSION) \
		--push \
		.

# Build and push combined
docker-release: docker-build

# Check supported platforms
docker-check-platforms:
	docker manifest inspect $(IMAGE_NAME):$(VERSION)

docker-update-latest: docker-buildx-prepare
	docker buildx build \
		--platform $(PLATFORMS) \
		-t $(IMAGE_NAME):latest \
		--push \
		.

# Release with latest
docker-release-all: docker-release docker-update-latest

tag:
	@version=$$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'); \
	echo "Creating tag v$$version"; \
	git tag "v$$version"; \
	git push origin "v$$version"


dev:
	docker compose -f docker-compose.dev.yml up --build 

full:
	docker compose -f docker-compose.full.yml up --build 


api:
	uv run run_api.py

.PHONY: worker worker-start worker-stop worker-restart

worker: worker-start

worker-start:
	@echo "Starting surreal-commands worker..."
	uv run --env-file .env surreal-commands-worker --import-modules commands

worker-stop:
	@echo "Stopping surreal-commands worker..."
	pkill -f "surreal-commands-worker" || true

worker-restart: worker-stop
	@sleep 2
	@$(MAKE) worker-start