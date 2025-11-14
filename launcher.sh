#!/bin/bash

# Open Notebook Launcher Script
# This script launches all required services for Open Notebook

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Banner
echo -e "${BLUE}"
cat << "EOF"
 ___                   _   _       _       _                 _
/ _ \ _ __   ___ _ __ | \ | | ___ | |_ ___| |__   ___   ___ | | __
| | | | '_ \ / _ \ '_ \|  \| |/ _ \| __/ _ \ '_ \ / _ \ / _ \| |/ /
| |_| | |_) |  __/ | | | |\  | (_) | ||  __/ |_) | (_) | (_) |   <
\___/| .__/ \___|_| |_|_| \_|\___/ \__\___|_.__/ \___/ \___/|_|\_\
     |_|
EOF
echo -e "${NC}"
echo "Open Notebook Launcher"
echo "======================"
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_error "Please run this script from the Open Notebook root directory"
    exit 1
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required tools
print_info "Checking for required tools..."

if ! command_exists uv; then
    print_error "uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
print_success "uv found"

if ! command_exists node; then
    print_error "Node.js is not installed. Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi
print_success "Node.js found ($(node --version))"

if ! command_exists npm; then
    print_error "npm is not installed. Please install Node.js which includes npm."
    exit 1
fi
print_success "npm found ($(npm --version))"

# Check for SurrealDB
if ! command_exists surreal; then
    print_warning "SurrealDB is not installed. Installing SurrealDB..."
    curl -sSf https://install.surrealdb.com | sh
    export PATH="/usr/local/bin:$PATH"
    print_success "SurrealDB installed"
else
    print_success "SurrealDB found ($(surreal version | head -1))"
fi

# Check for .env file
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success ".env file created"
        print_warning "Please edit .env and add your API keys before continuing"
        read -p "Press Enter to continue or Ctrl+C to exit and edit .env..."
    else
        print_error ".env.example not found"
        exit 1
    fi
else
    print_success ".env file found"
fi

# Install frontend dependencies if needed
if [ ! -d "frontend/node_modules" ]; then
    print_info "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
    print_success "Frontend dependencies installed"
else
    print_success "Frontend dependencies already installed"
fi

# Create data directories if they don't exist
mkdir -p notebook_data surreal_data

# Function to cleanup on exit
cleanup() {
    echo ""
    print_info "Shutting down Open Notebook services..."
    pkill -f "surreal start" 2>/dev/null || true
    pkill -f "run_api.py" 2>/dev/null || true
    pkill -f "uvicorn api.main:app" 2>/dev/null || true
    pkill -f "surreal-commands-worker" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    sleep 2
    print_success "All services stopped"
    exit 0
}

# Register cleanup function
trap cleanup EXIT INT TERM

# Start services
echo ""
print_info "Starting Open Notebook services..."
echo ""

# Start SurrealDB
print_info "Starting SurrealDB..."
surreal start --log info --user root --pass root memory > /tmp/surrealdb.log 2>&1 &
SURREAL_PID=$!
sleep 2

if ps -p $SURREAL_PID > /dev/null; then
    print_success "SurrealDB started (PID: $SURREAL_PID, Port: 8000)"
else
    print_error "Failed to start SurrealDB"
    exit 1
fi

# Start API
print_info "Starting API backend..."
uv run run_api.py > /tmp/api.log 2>&1 &
API_PID=$!
sleep 5

if ps -p $API_PID > /dev/null; then
    print_success "API backend started (PID: $API_PID, Port: 5055)"
else
    print_error "Failed to start API backend. Check /tmp/api.log for details"
    exit 1
fi

# Start background worker
print_info "Starting background worker..."
uv run --env-file .env surreal-commands-worker --import-modules commands > /tmp/worker.log 2>&1 &
WORKER_PID=$!
sleep 2

if ps -p $WORKER_PID > /dev/null; then
    print_success "Background worker started (PID: $WORKER_PID)"
else
    print_error "Failed to start background worker. Check /tmp/worker.log for details"
    exit 1
fi

# Start frontend
print_info "Starting Next.js frontend..."
cd frontend
npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
sleep 5

if ps -p $FRONTEND_PID > /dev/null; then
    # Try to detect the port
    FRONTEND_PORT=$(grep -oP "localhost:\K\d+" /tmp/frontend.log | head -1)
    if [ -z "$FRONTEND_PORT" ]; then
        FRONTEND_PORT="3000"
    fi
    print_success "Next.js frontend started (PID: $FRONTEND_PID, Port: $FRONTEND_PORT)"
else
    print_error "Failed to start frontend. Check /tmp/frontend.log for details"
    exit 1
fi

# Display success message
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Open Notebook is now running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Access the application at:"
echo -e "  ${BLUE}➜${NC} Frontend:  ${GREEN}http://localhost:${FRONTEND_PORT}${NC}"
echo -e "  ${BLUE}➜${NC} API:       ${GREEN}http://localhost:5055${NC}"
echo -e "  ${BLUE}➜${NC} API Docs:  ${GREEN}http://localhost:5055/docs${NC}"
echo ""
echo "Process IDs:"
echo "  • SurrealDB: $SURREAL_PID"
echo "  • API:       $API_PID"
echo "  • Worker:    $WORKER_PID"
echo "  • Frontend:  $FRONTEND_PID"
echo ""
echo "Logs are available in /tmp/:"
echo "  • /tmp/surrealdb.log"
echo "  • /tmp/api.log"
echo "  • /tmp/worker.log"
echo "  • /tmp/frontend.log"
echo ""
print_warning "Press Ctrl+C to stop all services"
echo ""

# Keep script running and display logs
tail -f /tmp/frontend.log
