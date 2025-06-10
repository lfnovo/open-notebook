# Use Python 3.11 slim image as base
FROM python:3.11-slim-bookworm

# Install uv using the official method
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/


# Install system dependencies required for building certain Python packages
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    gcc git \
    libmagic-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container to /app
WORKDIR /app

COPY . /app

RUN uv sync


EXPOSE 8502

RUN mkdir -p /app/data

CMD ["uv", "run", "streamlit", "run", "app_home.py"]
