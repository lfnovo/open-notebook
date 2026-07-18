# Developer Guide

**📍 This file has moved!**

Developer documentation now lives in the development docs structure.

👉 **[Read the Development Setup Guide](docs/7-DEVELOPMENT/development-setup.md)**

---

## Quick Links

- **Setting up your environment?** → [Development Setup](docs/7-DEVELOPMENT/development-setup.md) (includes the make-workflow matrix)
- **New developer?** → [Quick Start](docs/7-DEVELOPMENT/quick-start.md)
- **Want to contribute?** → [Contributing Guide](docs/7-DEVELOPMENT/contributing.md)
- **Making a common change?** → [Change Playbooks](docs/7-DEVELOPMENT/change-playbooks.md)
- **Publishing Docker images?** → [Release Process](.github/RELEASE_PROCESS.md)
- **Coding-agent rules?** → [AGENTS.md](AGENTS.md)

---

## TL;DR

```bash
git clone https://github.com/lfnovo/open-notebook.git && cd open-notebook
cp .env.example .env
uv sync
make start-all    # SurrealDB + API + worker + frontend
```

For everything else, see **[docs/7-DEVELOPMENT/](docs/7-DEVELOPMENT/index.md)**.
