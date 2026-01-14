# Prior Notebook

**Military-grade RAG system for quantitative trading research.**

```
  ╔═══════════════════════════════════════════════════════════╗
  ║   ██████╗ ██████╗ ██╗ ██████╗ ██████╗                     ║
  ║   ██╔══██╗██╔══██╗██║██╔═══██╗██╔══██╗                    ║
  ║   ██████╔╝██████╔╝██║██║   ██║██████╔╝                    ║
  ║   ██╔═══╝ ██╔══██╗██║██║   ██║██╔══██╗                    ║
  ║   ██║     ██║  ██║██║╚██████╔╝██║  ██║                    ║
  ║   ╚═╝     ╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═╝                    ║
  ║                                                           ║
  ║   NOTEBOOK - Military-Grade RAG for Quant Trading         ║
  ╚═══════════════════════════════════════════════════════════╝
```

## Features

- **RAG Engine**: Semantic search across papers, PDFs, and trading data
- **arXiv Integration**: Search and ingest academic papers
- **Trading Data**: GEX, Vanna, and options flow analysis via QuestDB
- **Zero Trust Security**: WireGuard IP validation, JWT auth, encrypted data
- **High Performance**: Written in Rust with Actix-web
- **Julia Integration**: Quantitative analysis (GEX calculation, Greeks, etc.)
- **CLI**: Dynamic command-line interface for automation

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          PRIOR NOTEBOOK                              │
├─────────────────┬─────────────────┬─────────────────┬───────────────┤
│   Data Sources  │   Backend       │   Frontend      │   Security    │
├─────────────────┼─────────────────┼─────────────────┼───────────────┤
│ - Google        │ - RAG Engine    │ - UI (planned)  │ - Zero Trust  │
│ - arXiv         │   (Rust)        │ - Markdown      │ - WireGuard   │
│ - QuestDB       │ - Julia FFI     │   render        │ - Vault       │
│ - PDFs          │ - Redis cache   │ - Code blocks   │ - ZFS crypto  │
│ - ThetaData     │ - Qdrant        │                 │ - mTLS        │
└─────────────────┴─────────────────┴─────────────────┴───────────────┘
```

## Quick Start

### Prerequisites

- Rust 1.84+
- Docker & Docker Compose
- (Optional) Julia 1.10+ for quantitative analysis

### Installation

```bash
# Clone repository
git clone https://github.com/prior-systems/prior-notebook.git
cd prior-notebook

# Copy config
cp config.toml.example config.toml
# Edit config.toml with your API keys

# Start services (Qdrant, Redis, QuestDB)
docker compose up -d

# Build and run
cargo build --release
./target/release/prior-api
```

### CLI Usage

```bash
# Search the knowledge base
prior search "GEX SPY 0DTE"

# Search arXiv and ingest papers
prior arxiv "gamma exposure options market" --ingest

# Ingest PDF documents
prior ingest pdf ./papers/trading/

# Get GEX data
prior trading gex SPY --days 7

# Start API server
prior serve --host 0.0.0.0 --port 8080
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/search` | POST | Search knowledge base |
| `/api/v1/search/arxiv` | POST | Search arXiv papers |
| `/api/v1/documents` | POST | Ingest document |
| `/api/v1/trading/gex` | GET | Get GEX data |
| `/api/v1/auth/login` | POST | Get JWT token |

### Example: Search

```bash
curl -X POST http://localhost:8080/api/v1/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"query": "gamma exposure market impact", "limit": 10}'
```

## Security

### Zero Trust Architecture

- **WireGuard VPN**: Only accept connections from authorized IPs
- **JWT Authentication**: Short-lived tokens with role-based access
- **Vault Integration**: Secrets management (optional)
- **Encrypted Storage**: ZFS with encryption at rest

### Configuration

```toml
[security]
jwt_secret = "your-256-bit-secret"
allowed_wireguard_ips = ["10.0.0.0/24"]
enable_zero_trust = true
```

## Deployment

### Docker

```bash
docker compose up -d
```

### Nomad

```bash
nomad job run prior-notebook.nomad
```

## Development

```bash
# Run tests
cargo test

# Run with logging
RUST_LOG=debug cargo run --bin prior-api

# Format code
cargo fmt

# Lint
cargo clippy
```

## License

MIT License - see [LICENSE](LICENSE)

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request
