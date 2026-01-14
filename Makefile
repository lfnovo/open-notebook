# Prior Notebook - Makefile
# Military-grade RAG for quantitative trading

.PHONY: all build release test clean docker run dev

# Default target
all: build

# Development build
build:
	cargo build

# Release build (optimized)
release:
	cargo build --release

# Build with Julia support
release-julia:
	cargo build --release --features julia

# Run tests
test:
	cargo test

# Run tests with coverage
test-coverage:
	cargo llvm-cov --html

# Run linter
lint:
	cargo clippy -- -D warnings

# Format code
fmt:
	cargo fmt

# Check formatting
fmt-check:
	cargo fmt -- --check

# Clean build artifacts
clean:
	cargo clean

# Start development services
dev-services:
	docker compose up -d qdrant redis questdb

# Stop development services
dev-services-down:
	docker compose down

# Run API in development mode
dev:
	RUST_LOG=debug cargo run --bin prior-api

# Run CLI
cli:
	cargo run --bin prior -- $(ARGS)

# Docker build
docker:
	docker build -t prior-notebook:latest .

# Docker build with Julia
docker-julia:
	docker build -t prior-notebook:julia --target with-julia .

# Docker push to GHCR
docker-push:
	docker tag prior-notebook:latest ghcr.io/prior-systems/prior-notebook:latest
	docker push ghcr.io/prior-systems/prior-notebook:latest

# Start all services
up:
	docker compose up -d

# Stop all services
down:
	docker compose down

# View logs
logs:
	docker compose logs -f prior-api

# Generate JWT secret
generate-secret:
	cargo run --bin prior -- security generate-secret

# Run benchmarks
bench:
	cargo bench

# Documentation
docs:
	cargo doc --open

# Install CLI globally
install:
	cargo install --path .

# Nomad deployment
deploy:
	nomad job run prior-notebook.nomad

# Nomad stop
undeploy:
	nomad job stop prior-notebook

# Security audit
audit:
	cargo audit

# Update dependencies
update:
	cargo update

# Help
help:
	@echo "Prior Notebook - Available targets:"
	@echo ""
	@echo "  build          - Development build"
	@echo "  release        - Optimized release build"
	@echo "  release-julia  - Release with Julia support"
	@echo "  test           - Run tests"
	@echo "  lint           - Run clippy linter"
	@echo "  fmt            - Format code"
	@echo "  clean          - Clean build artifacts"
	@echo ""
	@echo "  dev-services   - Start dev services (Qdrant, Redis, QuestDB)"
	@echo "  dev            - Run API in development mode"
	@echo "  cli ARGS=...   - Run CLI with arguments"
	@echo ""
	@echo "  docker         - Build Docker image"
	@echo "  up             - Start all services"
	@echo "  down           - Stop all services"
	@echo "  logs           - View API logs"
	@echo ""
	@echo "  deploy         - Deploy to Nomad"
	@echo "  undeploy       - Stop Nomad job"
