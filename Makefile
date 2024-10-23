.PHONY: run check ruff database lint docker-build docker-push docker-buildx-prepare docker-release

# Get version from pyproject.toml
VERSION := $(shell grep -m1 version pyproject.toml | cut -d'"' -f2)
IMAGE_NAME := lfnovo/open_notebook

PLATFORMS=linux/amd64,linux/arm64
#,linux/arm/v7,linux/386

database:
	docker compose up -d

run:
	poetry run streamlit run app_home.py

lint:
	poetry run python -m mypy .

ruff:
	ruff check . --fix

# Configuração do buildx para multi-plataforma
docker-buildx-prepare:
	docker buildx create --use --name multi-platform-builder || true

# Build multi-plataforma com buildx
docker-build: docker-buildx-prepare
	docker buildx build \
		--platform $(PLATFORMS) \
		-t $(IMAGE_NAME):$(VERSION) \
		--push \
		.

# O push já é feito durante o build com buildx
docker-push:
	@echo "Push já foi realizado durante o build com buildx"

# Build e push combinados
docker-release: docker-build

# Comando útil para verificar as plataformas suportadas após o build
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
