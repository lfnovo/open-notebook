# Projekt Anforderungen & Status

## 🎯 Projektübersicht

**Name**: Open Notebook  
**Beschreibung**: Open source, privacy-focused alternative to Google's Notebook LM  
**Repository**: https://github.com/lfnovo/open-notebook  
**Aktueller Branch**: main  
**Letzter Commit**: 23ba65b (2026-06-20)

---

## 📋 Aktuelle Anforderungen

### ✅ Erfüllt (2026-06-20)

#### Issue #893: Sequential processing mode for single-GPU setups
**Status**: ✅ Implementiert, PR #933 erstellt

**Anforderungen**:
- ✅ Environment Variable OPEN_NOTEBOOK_WORKER_MAX_TASKS
- ✅ Input validation mit graceful fallback
- ✅ Default value: 5 (backward compatible)
- ✅ Single-GPU support (set to 1)
- ✅ Documentation in environment-reference.md
- ✅ Warnings in .env.example
- ✅ Automated tests (33 tests)
- ✅ CI/CD integration

**Implementierung**:
- 7 Dateien modifiziert
- 33 Tests erstellt
- PR #933 submitted
- Issue #893 kommentiert

---

## 🔄 Offene Anforderungen

### Pending Reviews
- **PR #933**: Waiting for maintainer review
  - Link: https://github.com/lfnovo/open-notebook/pull/933
  - Expected: Merge into main branch

---

## 🏗️ Technische Anforderungen

### Development Environment
- ✅ Python 3.11+
- ✅ uv package manager
- ✅ Docker & Docker Compose
- ✅ Git

### Testing
- ✅ pytest framework
- ✅ Unit tests (19 tests)
- ✅ Integration tests (14 tests)
- ✅ 100% test coverage for new features

### Documentation
- ✅ environment-reference.md
- ✅ .env.example
- ✅ Inline code documentation
- ✅ Commit messages (conventional commits)

---

## 📊 Quality Metrics

### Code Quality
- **Test Coverage**: 100% (33/33 tests passing)
- **Documentation**: Complete
- **Code Style**: Consistent
- **Security**: No secrets in commits

### Performance
- **Default max-tasks**: 5 (multi-GPU optimized)
- **Single-GPU**: Can be set to 1
- **Validation**: Prevents invalid configurations

---

## 🚀 Roadmap

### Completed
- ✅ Issue #893 implementation
- ✅ Input validation
- ✅ Comprehensive testing
- ✅ Documentation update

### In Progress
- ⏳ PR #933 review (waiting)

### Future
- 📋 Monitor for new feature requests
- 📋 Community PR reviews
- 📋 Documentation updates as needed

---

**Letzte Aktualisierung**: 2026-06-20  
**Nächster Review**: After PR #933 merge

---

## 🤝 Contributing Guidelines

### Issue-First Workflow (CRITICAL)

**MUST FOLLOW**: Before any code changes:

1. ✅ **Create an issue first** - Describe bug/feature
2. ✅ **Propose your solution** - Explain implementation approach
3. ✅ **Wait for assignment** - Maintainer reviews and assigns
4. ✅ **Only then start coding** - Ensures alignment with project vision

**Why**: Prevents duplicate work, ensures architectural alignment, saves time

> ⚠️ **PRs without assigned issues may be closed** - Even if code is good!

### Contribution Areas (Current Priorities)

1. ✅ **Frontend Enhancement** - Next.js/React UI with real-time updates
2. ✅ **Testing** - Expand test coverage (we're at 100% for new features!)
3. ✅ **Performance** - Async processing and caching improvements
4. ✅ **Documentation** - API examples and user guides
5. ✅ **Integrations** - New content sources and AI providers

### Git Workflow

**Branch Strategy**:
- `main` - Production-ready code
- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates

**Commit Messages**:
- Present tense: "Add feature" not "Added feature"
- Imperative mood: "Move cursor" not "Moves cursor"
- Max 72 chars first line
- Reference issues/PRs liberally

### Testing Requirements

All contributions MUST include:
- ✅ Unit tests for new functionality
- ✅ Integration tests for API changes
- ✅ Documentation updates if behavior changes
- ✅ Follow code standards (ruff, mypy)

**Run tests**:
```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```

**PR Requirements**:
- Link to approved issue
- Clear description of changes
- Test evidence (screenshots, logs)
- Focused scope (one issue per PR)

---

**Community**:
- 📱 Discord: https://discord.gg/37XJPXfz2w
- 📚 Documentation: docs/7-DEVELOPMENT/
- 🐛 Issues: https://github.com/lfnovo/open-notebook/issues
