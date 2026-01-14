# Prior Notebook - CLAUDE.md

Military-grade RAG system for quantitative trading research, written in Rust.

## Project Overview

**Prior Notebook** is a high-performance RAG (Retrieval Augmented Generation) system designed for quantitative trading research. It enables semantic search across academic papers, PDFs, and trading data with military-grade security.

**Key Values**: Performance, Security, Quantitative Focus

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          PRIOR NOTEBOOK                              │
├─────────────────┬─────────────────┬─────────────────┬───────────────┤
│   Data Sources  │   Backend       │   Storage       │   Security    │
├─────────────────┼─────────────────┼─────────────────┼───────────────┤
│ - arXiv API     │ - Actix-web     │ - Qdrant        │ - Zero Trust  │
│ - Google/SerpAPI│ - RAG Engine    │ - Redis         │ - WireGuard   │
│ - PDF files     │ - Julia FFI     │ - QuestDB       │ - JWT/Argon2  │
│ - QuestDB       │ - Embeddings    │                 │ - AES-256-GCM │
└─────────────────┴─────────────────┴─────────────────┴───────────────┘
```

## Tech Stack

- **Language**: Rust 1.84+ (Edition 2024)
- **Web Framework**: Actix-web 4.9
- **Vector Database**: Qdrant
- **Time-Series DB**: QuestDB (trading data)
- **Cache**: Redis
- **Embeddings**: fastembed (BAAI/bge-small-en-v1.5)
- **Quantitative Analysis**: Julia (optional, via FFI)

## Directory Structure

```
prior-notebook/
├── src/
│   ├── lib.rs              # Library root
│   ├── bin/
│   │   ├── api.rs          # API server binary
│   │   └── cli.rs          # CLI binary
│   ├── api/                # Actix-web API
│   │   ├── handlers.rs     # Request handlers
│   │   ├── middleware.rs   # JWT auth, rate limiting
│   │   ├── routes.rs       # Route configuration
│   │   └── state.rs        # App state
│   ├── cli/                # CLI implementation
│   │   ├── mod.rs          # Clap definitions
│   │   └── commands.rs     # Command handlers
│   ├── config/             # Configuration
│   ├── core/               # Core RAG engine
│   │   ├── document.rs     # Document types
│   │   ├── embedding.rs    # Embedding service
│   │   ├── rag.rs          # RAG engine
│   │   └── vector_store.rs # Qdrant integration
│   ├── search/             # External data sources
│   │   ├── arxiv.rs        # arXiv API
│   │   ├── google.rs       # SerpAPI
│   │   └── pdf.rs          # PDF processing
│   ├── security/           # Security module
│   │   ├── auth.rs         # JWT authentication
│   │   ├── crypto.rs       # AES-256-GCM encryption
│   │   └── zero_trust.rs   # IP validation middleware
│   ├── storage/            # Storage backends
│   │   ├── questdb.rs      # QuestDB client
│   │   └── redis_cache.rs  # Redis caching
│   └── julia/              # Julia FFI (optional)
├── julia_lib/              # Julia quantitative code
├── tests/                  # Integration tests
├── docker-compose.yml      # Docker services
├── Dockerfile              # Multi-stage build
├── prior-notebook.nomad    # Nomad deployment
└── config.toml.example     # Config template
```

## Key Modules

### RAG Engine (`src/core/rag.rs`)
- Document chunking with overlap
- Batch embedding generation
- Vector similarity search
- Context building for LLM

### Security (`src/security/`)
- **Zero Trust**: WireGuard IP validation middleware
- **Auth**: JWT with Argon2 password hashing
- **Crypto**: AES-256-GCM for data at rest

### Storage (`src/storage/`)
- **QuestDB**: GEX, Vanna, and trading data
- **Redis**: Response caching, rate limiting
- **Qdrant**: Vector embeddings

### Search (`src/search/`)
- **arXiv**: Academic paper search
- **Google**: Web search via SerpAPI
- **PDF**: Local document processing

## CLI Commands

```bash
prior search "query"              # Search knowledge base
prior arxiv "query" --ingest      # Search arXiv, optionally ingest
prior ingest pdf ./path/          # Ingest PDF documents
prior trading gex SPY             # Get GEX data
prior serve                       # Start API server
prior security generate-secret    # Generate JWT secret
```

## API Endpoints

```
GET  /health                      # Health check
POST /api/v1/search               # Search knowledge base
POST /api/v1/search/arxiv         # Search arXiv
POST /api/v1/documents            # Ingest document
GET  /api/v1/trading/gex          # Get GEX data
POST /api/v1/auth/login           # Authentication
```

## Development

### Build

```bash
cargo build --release                    # Production build
cargo build --release --features julia   # With Julia support
```

### Test

```bash
cargo test                    # Unit tests
cargo test --test integration # Integration tests
```

### Run

```bash
# Start dependencies
docker compose up -d

# Run API
RUST_LOG=debug cargo run --bin prior-api

# Run CLI
cargo run --bin prior -- search "GEX"
```

## Configuration

Environment variables override `config.toml`:

| Variable | Description |
|----------|-------------|
| `PRIOR_HOST` | API bind host |
| `PRIOR_PORT` | API bind port |
| `QDRANT_URL` | Qdrant connection |
| `REDIS_URL` | Redis connection |
| `JWT_SECRET` | JWT signing key |
| `ANTHROPIC_API_KEY` | Claude API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `SERPAPI_KEY` | Google search key |

## Gotchas

1. **Embedding model**: First run downloads ~100MB model
2. **Julia feature**: Requires Julia 1.10+ installed
3. **Zero Trust**: Disable for local dev (`enable_zero_trust = false`)
4. **QuestDB**: Tables must be created manually for trading data
