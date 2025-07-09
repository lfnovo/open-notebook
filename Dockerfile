# Use Python 3.11 slim image as base
FROM python:3.11-slim-bookworm

# Install uv using the official method
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/


# Install system dependencies required for building certain Python packages
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    gcc g++ git make \
    libmagic-dev \
    ffmpeg \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container to /app
WORKDIR /app

COPY . /app

RUN uv sync


# Expose ports for Streamlit and API
EXPOSE 8502 5055

RUN mkdir -p /app/data

# Copy supervisord configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create log directories
RUN mkdir -p /var/log/supervisor

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
