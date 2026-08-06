# Development

Welcome to the Open Notebook development documentation! Whether you're contributing code, understanding our architecture, or maintaining the project, you'll find guidance here.

## 🎯 Pick Your Path

### 👨‍💻 I Want to Contribute Code

Start with **[Contributing Guide](contributing.md)** for the workflow, then check:
- **[Quick Start](quick-start.md)** - Clone, install, verify in 5 minutes
- **[Development Setup](development-setup.md)** - Complete local environment guide
- **[Code Standards](code-standards.md)** - How to write code that fits our style
- **[Testing](testing.md)** - How to write and run tests

**First time?** Check out our [Contributing Guide](contributing.md) for the Discussions → Issues → PRs workflow.

### 🔒 I Want to Understand Security Practices

**[Security Guidelines](security.md)** covers:
- Database query safety (preventing SurrealQL injection)
- Template rendering safety (preventing SSTI)
- File handling safety (preventing path traversal and LFI)
- Secrets management and CORS configuration
- Code review security checklist

---

### 🏗️ I Want to Understand the Architecture

**[Architecture Overview](architecture.md)** covers:
- 3-tier system design
- Tech stack and rationale
- Key components and workflows
- Design patterns we use

For deeper dives into specific subsystems:
- **[Credentials](credentials.md)** - Provider credential storage, encryption, provisioning
- **[Content Processing](content-processing.md)** - Chunking, embedding, context building, encryption
- **[Podcasts](podcasts.md)** - Profile system, model registry, job lifecycle
- **[Prompts](prompts.md)** - Prompt engineering patterns
- **[Frontend](frontend.md)** - Next.js layers and data flows

Normative rules for coding agents (and humans in a hurry) live in the `AGENTS.md` files at the
repo root, `open_notebook/`, and `frontend/`.

### 🧭 Why Is It Like This?

- **[VISION.md](../../VISION.md)** - Product identity and current posture
- **[Decision Records](decisions/README.md)** - ADRs and PDRs: the durable "why" behind structural choices

---

### 👨‍🔧 I'm a Maintainer

**[Maintainer Guide](maintainer-guide.md)** covers:
- Issue triage and management
- Pull request review process
- Communication templates
- Best practices

---

## 📚 Quick Links

| Document | For | Purpose |
|---|---|---|
| [Quick Start](quick-start.md) | New developers | Clone, install, and verify setup (5 min) |
| [Development Setup](development-setup.md) | Local development | Complete environment setup guide |
| [Contributing](contributing.md) | Community & code contributors | Workflow: Discussion → Issue → PR |
| [Code Standards](code-standards.md) | Writing code | Style guides for Python, FastAPI, DB |
| [Testing](testing.md) | Testing code | How to write and run tests |
| [Architecture](architecture.md) | Understanding system | System design, tech stack, workflows |
| [Credentials](credentials.md) | Understanding system | Provider credential subsystem |
| [Content Processing](content-processing.md) | Understanding system | Chunking, embedding, context building |
| [Podcasts](podcasts.md) | Understanding system | Podcast profiles and job lifecycle |
| [Prompts](prompts.md) | Understanding system | Prompt engineering patterns |
| [Frontend](frontend.md) | Understanding system | Next.js architecture and data flows |
| [Design Principles](design-principles.md) | All developers | Engineering practices and anti-patterns |
| [VISION.md](../../VISION.md) | All developers | Product identity and current posture |
| [Decision Records](decisions/README.md) | All developers | ADRs/PDRs — why things are the way they are |
| [Change Playbooks](change-playbooks.md) | Contributors & agents | Step-by-step recipes for common changes |
| [API Reference](api-reference.md) | Building integrations | Complete REST API documentation |
| [Security](security.md) | All developers | Security practices and vulnerability prevention |
| [Maintainer Guide](maintainer-guide.md) | Maintainers | Managing issues, PRs, labels |

---

## 🚀 Current Development Priorities

We're actively looking for help with:

1. **Frontend Enhancement** - Improve Next.js/React UI with real-time updates
2. **Performance** - Async processing and caching optimizations
3. **Testing** - Expand test coverage across components
4. **Documentation** - API examples and developer guides
5. **Integrations** - New content sources and AI providers

See GitHub Issues labeled `good first issue` or `help wanted`.

---

## 💬 Getting Help

- **Discord**: [Join our server](https://discord.gg/37XJPXfz2w) for real-time discussions
- **GitHub Discussions**: For questions, ideas, features, product direction, design, and architecture
- **GitHub Issues**: For reproducible bugs and approved work items

Don't be shy! We're here to help new contributors succeed.

---

## 📖 Additional Resources

### External Documentation
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SurrealDB Docs](https://surrealdb.com/docs)
- [LangChain Docs](https://python.langchain.com/)
- [Next.js Docs](https://nextjs.org/docs)

### Our Libraries
- [Esperanto](https://github.com/lfnovo/esperanto) - Multi-provider AI abstraction
- [Content Core](https://github.com/lfnovo/content-core) - Content processing
- [Podcast Creator](https://github.com/lfnovo/podcast-creator) - Podcast generation

---

Ready to get started? Head over to **[Quick Start](quick-start.md)**! 🎉
