# Use an official Python runtime as a base image
FROM python:3.11.7-slim-bullseye 

# Install system dependencies required for building certain Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    curl wget libmagic-dev ffmpeg \ 
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container to /app
WORKDIR /app

RUN pip install poetry --no-cache-dir 
RUN poetry self add poetry-plugin-dotenv
RUN poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock /app/
RUN poetry install --only main

COPY . /app
EXPOSE 8502

RUN mkdir -p /app/data

CMD ["poetry", "run", "streamlit", "run", "app_home.py"]
