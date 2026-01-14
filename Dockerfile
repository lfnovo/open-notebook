# Prior Notebook - Multi-stage Rust build
# Military-grade RAG for quantitative trading

# ============ Builder Stage ============
FROM rust:1.84-bookworm AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    libclang-dev \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Copy manifests
COPY Cargo.toml Cargo.lock ./

# Create dummy src for dependency caching
RUN mkdir src && \
    echo "fn main() {}" > src/main.rs && \
    mkdir -p src/bin && \
    echo "fn main() {}" > src/bin/api.rs && \
    echo "fn main() {}" > src/bin/cli.rs

# Build dependencies only
RUN cargo build --release && rm -rf src target/release/deps/prior*

# Copy actual source
COPY src ./src

# Build actual application
RUN cargo build --release --no-default-features

# ============ Runtime Stage ============
FROM debian:bookworm-slim AS runtime

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 prior

# Copy binaries
COPY --from=builder /app/target/release/prior-api /usr/local/bin/
COPY --from=builder /app/target/release/prior /usr/local/bin/

# Copy config
COPY config.toml.example /app/config.toml

# Create data directories
RUN mkdir -p /app/data/pdfs /app/data/embeddings && \
    chown -R prior:prior /app

USER prior

# Expose API port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command
CMD ["prior-api"]

# ============ Julia Stage (optional) ============
FROM runtime AS with-julia

USER root

# Install Julia
RUN curl -fsSL https://julialang-s3.julialang.org/bin/linux/x64/1.10/julia-1.10.0-linux-x86_64.tar.gz | \
    tar xz -C /opt && \
    ln -s /opt/julia-1.10.0/bin/julia /usr/local/bin/julia

# Copy Julia project
COPY --chown=prior:prior julia_lib /app/julia_lib

# Precompile Julia packages
RUN julia --project=/app/julia_lib -e 'using Pkg; Pkg.instantiate(); Pkg.precompile()'

USER prior

ENV JULIA_PROJECT=/app/julia_lib
