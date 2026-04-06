#!/bin/bash
# Development environment setup for Open Notebook
# This script installs dependencies and starts all required services

set -e

echo "=== Open Notebook Development Setup ==="

# 1. Install Python dependencies
echo "Installing Python dependencies..."
uv sync

# 2. Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend && npm install && cd ..

# 3. Start services using Makefile
echo ""
echo "=== Starting Services ==="
echo "Use 'make start-all' to start all services (DB + API + Worker + Frontend)"
echo "Or start individually:"
echo "  make database     - Start SurrealDB"
echo "  make api          - Start FastAPI backend (port 5055)"
echo "  make worker-start - Start background worker"
echo "  make frontend     - Start Next.js frontend (port 3000)"
echo ""
echo "Access points:"
echo "  Frontend: http://localhost:3000"
echo "  API:      http://localhost:5055"
echo "  API Docs: http://localhost:5055/docs"
echo ""
echo "To check status: make status"
echo "To stop all:     make stop-all"
