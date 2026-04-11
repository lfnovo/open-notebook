# Build stage
FROM python:3.12-slim-bookworm AS builder

# Install uv using the official method
COPY --from=ghcr.io/astral-sh/uv:0.6.6 /uv /uvx /bin/

# Install system dependencies required for building certain Python packages
# Add Node.js 20.x LTS for building frontend
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set build optimization environment variables
ENV MAKEFLAGS="-j$(nproc)"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Set the working directory in the container to /app
WORKDIR /app

# Copy dependency files and minimal package structure first for better layer caching
COPY pyproject.toml uv.lock ./
COPY open_notebook/__init__.py ./open_notebook/__init__.py

# Install dependencies with optimizations
RUN uv sync --no-dev

# Install easyocr with specified torch build (CUDA or CPU depending on target)
RUN .venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121 --quiet && \
    .venv/bin/pip install easyocr --no-deps && \
    .venv/bin/pip install Pillow scikit-image python-bidi PyYAML ninja

# Pre-download tiktoken encoding
ENV TIKTOKEN_CACHE_DIR=/app/tiktoken-cache
RUN mkdir -p /app/tiktoken-cache && \
    .venv/bin/python -c "import tiktoken; tiktoken.get_encoding('o200k_base')"

# Copy the rest of the application code
COPY . /app

# Install frontend dependencies and build
# Note: Using npm install instead of ci for better cross-platform binary resolution
WORKDIR /app/frontend
ARG NPM_REGISTRY=https://registry.npmjs.org/
COPY frontend/package.json frontend/package-lock.json ./
RUN npm config set registry ${NPM_REGISTRY}
RUN npm install && npm install @next/swc-linux-x64-gnu
COPY frontend/ ./
RUN npm run build

# Return to app root
WORKDIR /app

# Runtime stage
FROM python:3.12-slim-bookworm AS runtime

# Install only runtime system dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    ffmpeg \
    supervisor \
    curl \
    git \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv using the official method
COPY --from=ghcr.io/astral-sh/uv:0.6.6 /uv /uvx /bin/

# Set the working directory in the container to /app
WORKDIR /app

# Copy the virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy the source code
COPY . /app

# Copy pre-downloaded tiktoken encoding
COPY --from=builder /app/tiktoken-cache /app/tiktoken-cache

# Ensure uv uses the existing venv
ENV UV_NO_SYNC=1
ENV VIRTUAL_ENV=/app/.venv
ENV TIKTOKEN_CACHE_DIR=/app/tiktoken-cache

# Bind Next.js to all interfaces
ENV HOSTNAME=0.0.0.0

# Copy built frontend from builder stage
COPY --from=builder /app/frontend/.next/standalone /app/frontend/
COPY --from=builder /app/frontend/.next/static /app/frontend/.next/static
COPY --from=builder /app/frontend/public /app/frontend/public
COPY --from=builder /app/frontend/start-server.js /app/frontend/start-server.js

# Expose ports for Frontend (8502, mapped to 3001) and API (5055)
EXPOSE 3001 8502 5055

RUN mkdir -p /app/data

# Download spaCy model and NLTK data
RUN /app/.venv/bin/python -m spacy download en_core_web_sm && \
    /app/.venv/bin/python -c "\
import nltk; \
nltk.download('punkt', quiet=True); \
nltk.download('averaged_perceptron_tagger', quiet=True); \
nltk.download('maxent_ne_chunker', quiet=True); \
nltk.download('words', quiet=True)"

# Copy and make executable the wait-for-api script
COPY scripts/wait-for-api.sh /app/scripts/wait-for-api.sh
RUN chmod +x /app/scripts/wait-for-api.sh

# Copy supervisord configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create log directories
RUN mkdir -p /var/log/supervisor

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

