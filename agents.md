# 🎯 Projekt- und Agenten-Spezifikation

## 1. Projektübersicht

**Name**: Open Notebook  
**Beschreibung**: Open source, privacy-focused alternative to Google's Notebook LM  
**Repository**: https://github.com/lfnovo/open-notebook  
**Tech Stack**: Python/FastAPI (Backend), Next.js/React (Frontend), SurrealDB (Database)  
**Aktueller Branch**: main  
**Letzter Commit**: 23ba65b (2026-06-20)

### Kern-Features
- 🔒 Privacy-first (self-hosted option)
- 📚 Multi-modal content (PDFs, audio, video, web)
- 🤖 Multi-model AI support (18+ providers)
- 🎙️ Professional podcast generation
- 🔍 Semantic search & chat
- 🌐 Multi-language UI

### Lokale Entwicklungsumgebung (Dieses System)
- **Working Directory**: `/mnt/c/Users/T11/SynologyDrive/LLM/open-notebook` (WSL2)
- **Host System**: Windows 11 mit WSL2 (Ubuntu)
- **Git Repo**: `lfnovo/open-notebook` (main branch)
- **Hot-Reload**: ✅ Next.js Frontend (Port 3000), FastAPI Backend (Port 5055)
- **Database**: SurrealDB in Docker (Port 8000)
- **Entwicklungsmode**: Manuelle Startskripte für Hot-Reload

**WSL2 Setup** (2026-06-22 eingerichtet):
- **Python**: 3.12.3 (system) + `uv` package manager
- **Node.js**: v20.20.2 (via nvm)
- **Docker**: Desktop mit WSL2 Integration
- **Konfiguration**: `.wslconfig` optimiert (2 CPUs, 4GB RAM, mirrored networking)

**Hot-Reload Start** (manuell, da `make start-all` docker-compose.dev.yml fehlt):
```bash
# Terminal 1 - SurrealDB (Docker)
wsl --exec bash -c "cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook && make database"

# Terminal 2 - API Backend (Hot-Reload)
wsl --exec bash -c "cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook && .venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 5055"

# Terminal 3 - Frontend (Hot-Reload)
wsl --exec bash -c "export NVM_DIR=/home/t11/.nvm && [ -s \$NVM_DIR/nvm.sh ] && . \$NVM_DIR/nvm.sh && nvm use 20 && cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook/frontend && npm run dev"
```

**Alternative**: Startskripte verwenden:
```bash
# API starten
wsl --exec bash -c "/tmp/start_api.sh"

# Frontend starten  
wsl --exec bash -c "/tmp/start_frontend.sh"
```

**Status prüfen**:
```bash
wsl --exec bash -c "cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook && docker ps --filter 'name=open-notebook'"
wsl --exec bash -c "ps aux | grep -E 'uvicorn|next|node' | grep -v grep"
```

**Stoppen**:
```bash
wsl --exec bash -c "cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook && make stop-all"
# Oder alle WSL Prozesse beenden
wsl --shutdown
```

**Ports**:
- Frontend: http://localhost:3000 (Next.js Dev Server)
- API: http://localhost:5055 (FastAPI, /docs verfügbar)
- Database: http://localhost:8000 (SurrealDB)

**Startskripte** (in `/tmp/` unter WSL):
- `/tmp/start_api.sh` - Startet API Backend mit Hot-Reload
- `/tmp/start_frontend.sh` - Startet Frontend mit Hot-Reload

### Produktives Setup (Docker Host .142)
- **Host**: Docker Host mit IP .142
- **Deployment**: Docker Compose mit production images
- **Image**: `lfnovo/open_notebook:v1-latest`
- **Volumes**: `./notebook_data:/app/data`, `./surreal_data:/mydata`

**Ports**:
- GUI: http://docker-host-142:8502
- API: http://docker-host-142:5055
- Database: http://docker-host-142:8000

**Docker Compose**:
```yaml
services:
  surrealdb:
    image: surrealdb/surrealdb:v2
    ports:
      - "8000:8000"
    volumes:
      - ./surreal_data:/mydata
  
  open_notebook:
    image: lfnovo/open_notebook:v1-latest
    ports:
      - "8502:8502"
      - "5055:5055"
    environment:
      - OPEN_NOTEBOOK_ENCRYPTION_KEY=...
      - SURREAL_URL=ws://surrealdb:8000/rpc
    volumes:
      - ./notebook_data:/app/data
```

---

## 2. Architektur

### Three-Tier Architecture
```
┌─────────────────────────────────────────────────────────┐
│              Frontend (Next.js/React)                    │
│              frontend/ @ port 3000                       │
├────────────────────────────────────────────────────────┤
│ - Zustand state management, TanStack Query              │
│ - Shadcn/ui component library with Tailwind CSS         │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP REST
┌────────────────────────▼────────────────────────────────┐
│              API (FastAPI)                              │
│              api/ @ port 5055                           │
├────────────────────────────────────────────────────────┤
│ - REST endpoints for notebooks, sources, notes, chat    │
│ - LangGraph workflow orchestration                      │
│ - Job queue for async operations (podcasts)             │
│ - Multi-provider AI provisioning via Esperanto          │
└────────────────────────┬────────────────────────────────┘
                         │ SurrealQL
┌────────────────────────▼────────────────────────────────┐
│         Database (SurrealDB)                            │
│         Graph database @ port 8000                      │
└────────────────────────────────────────────────────────┘
```

### Key Components
- **LangGraph Workflows**: source.py, chat.py, ask.py, transformation.py
- **AI Providers**: Esperanto library (8+ providers)
- **Database**: SurrealDB with vector embeddings
- **Content Processing**: content-core library
- **Podcast Generation**: podcast-creator library

---

## 3. Aktive Issues & Projekte

### ✅ Completed (2026-06-20)

#### Issue #893: Sequential processing mode for single-GPU setups
**Status**: ✅ Implemented, PR #933 submitted  
**PR**: https://github.com/lfnovo/open-notebook/pull/933

**Problem**: All sources processed simultaneously caused LLM rate limits even with proper retry logic.

**Solution**: Added `OPEN_NOTEBOOK_WORKER_MAX_TASKS` environment variable to control worker concurrency.

**Changes**:
- 7 files modified (dev-init.sh, Makefile ×2, supervisord.conf, supervisord.single.conf, .env.example, test files)
- 33 tests created (19 unit + 14 integration)
- Input validation with graceful fallback to default 5
- Single-GPU warning and recommended ranges documented
- Comprehensive documentation in environment-reference.md

**Files Modified**:
1. `dev-init.sh:32` - Added validation and max-tasks flag
2. `Makefile:145` - worker-start target with validation
3. `Makefile:165` - start-all target with validation
4. `supervisord.conf:18` - ENV pass-through with $$ escaping
5. `supervisord.single.conf:30` - ENV pass-through with $$ escaping
6. `.env.example:54-60` - Documentation with warnings
7. `docs/5-CONFIGURATION/environment-reference.md` - Complete documentation

**Test Coverage**: 100% (33/33 tests passing)

#### Issue #776: Custom models in transformations
**Status**: 📋 Ready for implementation
**Linked Issue**: https://github.com/lfnovo/open-notebook/issues/776

**Problem**: Aktuell wird für alle Transformationen ein globaler Default-LLM verwendet. Nutzer möchten verschiedene LLMs für verschiedene Transformationen nutzen können (z.B. kleines Modell für Zusammenfassung, großes für komplexe Extraktionen).

**Lösung**: `model_id` Feld zu Transformation hinzufügen, das den LLM pro Transformation überschreibt.

**Änderungen nötig**:
- **Database**: SurrealQL Migration (`ALTER TABLE transformation ADD COLUMN model_id`)
- **Backend**: 5 Dateien (domain, models.py, router, service, graph)
- **Frontend**: 3 Dateien (types, editor dialog, card component)
- **Tests**: Integration tests für Model-Priority

**Komplexität**: Mittel (~11-12 Stunden)
**Empfohlener Ansatz**: Lokale Entwicklung mit Hot-Reload (`make start-all`)

**Implementierungs-Reihenfolge**:
1. Database Migration erstellen
2. Backend Domain Model erweitern
3. API Schemas aktualisieren
4. Router CRUD-Endpoints anpassen
5. Graph Logic für Model-Priority implementieren
6. Frontend Editor Dialog mit ModelSelector erweitern
7. Integration tests schreiben
8. Documentation aktualisieren

### ⏳ In Progress

#### PR #933: Waiting for maintainer review
**Status**: Awaiting merge  
**Linked Issue**: #893  
**Expected**: Review and merge into main

---

## 4. Offene Aufgaben

### Immediate (Next 7 days)
1. Monitor PR #933 status
2. Address maintainer feedback (if any)
3. Verify merge completion

### Short-term (Next 30 days)
1. Monitor issue tracker for new feature requests
2. Review and respond to community PRs
3. Update project documentation if needed

### Future Opportunities
1. Frontend Enhancement - Real-time UI updates
2. Async Processing - Improve background task handling
3. Performance - Caching optimizations
4. Documentation - API examples and user guides
5. Integrations - New content sources and AI providers

---

## 5. Technische Anforderungen

### Development Environment
- Python 3.11+
- uv package manager
- Docker & Docker Compose
- Git

### Testing Requirements
- pytest framework
- Unit tests (19 tests for Issue #893)
- Integration tests (14 tests for Issue #893)
- Code standards: ruff, mypy

### Code Standards
- **Python**: ruff check, ruff format, mypy
- **JavaScript/TypeScript**: ESLint, Prettier
- **Commits**: Conventional commits (feat:, fix:, docs:, etc.)
- **Branches**: feature/, fix/, docs/ naming

---

## 6. Development Pipeline

### Complete Workflow: Issue → Development → PR

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐     ┌──────────────┐
│  Issue      │ ──▶ │  Development     │ ──▶ │   Commit    │ ──▶ │    Push      │
│  Selection  │     │  with Hot-Reload │     │  & Tests    │     │  to Fork     │
└─────────────┘     └──────────────────┘     └─────────────┘     └──────────────┘
                                                                  │
                                                                  ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  Deploy     │ ◀── │   Merge      │ ◀── │   Review    │ ◀── │   PR         │
│  to Docker  │     │  to main     │     │  & Feedback │     │  Creation    │
│  Host       │     │              │     │             │     │              │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
```

### Step 1: Issue Selection

**Options:**
- Existing issue in GitHub Fork (`D-revv/open-notebook`)
- New issue creation (required before coding)

### Step 2: Feature Branch Creation

```bash
# Update main branch
git checkout main
git pull origin-fork main

# Create feature branch (named after issue)
git checkout -b fix/893-worker-max-tasks-env
# or: git checkout -b feature/neues-feature
```

**Branch Naming Convention:**
- `fix/<issue-number>-description` - Bug fixes
- `feature/<issue-number>-description` - New features
- `docs/<issue-number>-description` - Documentation

### Step 3: Development with Hot-Reload

**Start Services** (3 separate terminals):

```powershell
# Terminal 1 - SurrealDB
wsl --exec bash -c "cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook && make database"

# Terminal 2 - API Backend (Hot-Reload, Port 5055)
wsl --exec bash -c "cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook && .venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 5055"

# Terminal 3 - Frontend (Hot-Reload, Port 3000)
wsl --exec bash -c "export NVM_DIR=/home/t11/.nvm && [ -s \$NVM_DIR/nvm.sh ] && . \$NVM_DIR/nvm.sh && nvm use 20 && cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook/frontend && npm run dev"
```

**Development Loop:**
1. Edit code in IDE
2. Changes auto-reload (API + Frontend)
3. Test live in browser: http://localhost:3000
4. API docs: http://localhost:5055/docs

### Step 4: Testing & Linting

**Before Commit:**
```bash
# Check status
git status
git diff

# Run linter
wsl --exec bash -c "uv run ruff check ."

# Run tests
wsl --exec bash -c "uv run pytest tests/"
```

### Step 5: Commit

**Commit Message Format:**
```bash
git add .
git commit -m "[type] Short description (Issue #XYZ)"

# Types: feat, fix, docs, style, refactor, test, chore
```

**Examples:**
- `[feat] Add worker concurrency control (Issue #893)`
- `[fix] Resolve TTS audio playback bug (Issue #776)`
- `[docs] Update API documentation`

### Step 6: Push to Fork

```bash
git push origin-fork fix/893-worker-max-tasks-env
```

### Step 7: Create Pull Request

**Via GitHub Web UI:**
1. Go to: `https://github.com/D-revv/open-notebook`
2. Click "Compare & pull request"
3. PR Configuration:
   - **Base repository**: `lfnovo/open-notebook`
   - **Base branch**: `main`
   - **Head repository**: `D-revv/open-notebook`
   - **Head branch**: `fix/893-worker-max-tasks-env`

**PR Description Template:**
```markdown
## Description
Brief description of changes

## Related Issue
Closes #893 (if applicable)

## Changes
- [x] Feature implemented
- [x] Tests added
- [x] Documentation updated

## Testing
- [x] Local tests passed
- [ ] Code review required
```

### Step 8: Synchronization (if needed)

**Update from Upstream:**
```bash
# Fetch upstream
git fetch upstream

# Merge upstream main into your branch
git checkout fix/893-worker-max-tasks-env
git merge upstream/main

# Resolve conflicts if any
# Then push
git push origin-fork fix/893-worker-max-tasks-env
```

### Step 9: After Merge

**Clean up branches:**
```bash
# Delete local branch
git checkout main
git branch -d fix/893-worker-max-tasks-env

# Delete remote branch
git push origin-fork --delete fix/893-worker-max-tasks-env
```

**Deploy to Docker Host** (optional):
```powershell
# On Docker Host (.142)
ssh opencode@192.168.178.142
docker compose pull
docker compose up -d
```

---

## 7. Git Workflow

### Branch Strategy
- `main` - Production-ready code
- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates

### Commit Messages
- Present tense: "Add feature" not "Added feature"
- Imperative mood: "Move cursor" not "Moves cursor"
- Max 72 characters first line
- Reference issues/PRs liberally

### Issue-First Workflow (CRITICAL)
1. Create issue BEFORE coding
2. Propose solution approach
3. Wait for maintainer assignment
4. Only then start implementing

> ⚠️ **PRs without assigned issues may be closed** - Even if code is good!

---

## 8. Test Status

### ⚠️ Test Requirement (CRITICAL)

**Alle Änderungen MÜSSEN durch automatisierte Tests bestätigt werden:**

- ✅ **Neue Features**: Unit tests + Integration tests
- ✅ **Bugfixes**: Regression tests + Unit tests
- ✅ **API Änderungen**: Integration tests für Endpoints
- ✅ **Datenbankänderungen**: Migration tests + Query tests
- ✅ **Frontend Änderungen**: Component tests + E2E tests (wenn anwendbar)

**Vor jedem Commit:**
```bash
# Alle Tests laufen lassen
wsl --exec bash -c "uv run pytest tests/ -v"

# Linting prüfen
wsl --exec bash -c "uv run ruff check ."
wsl --exec bash -c "uv run mypy ."
```

**PR-Voraussetzung:**
- ✅ Alle Tests müssen grün sein (0 failures)
- ✅ Neue Code Coverage ≥ 80% für neue Funktionen
- ✅ Keine Linting-Warnings
- ✅ Tests dokumentieren erwartetes Verhalten

### Latest Verification (2026-06-20)

| Component | Tests | Passed | Failed | Coverage |
|-----------|-------|--------|--------|----------|
| Unit Tests (test_worker_config.py) | 19 | 19 | 0 | 100% |
| Integration Tests (test_worker_integration.py) | 14 | 14 | 0 | 100% |
| Input Validation | - | ✅ | - | All edge cases |
| Documentation | - | ✅ | - | Complete |
| Git History | - | ✅ | - | Clean, no secrets |

### Test Commands
```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test files
uv run pytest tests/test_worker_config.py -v
uv run pytest tests/test_worker_integration.py -v

# Linting
uv run ruff check .
uv run ruff format .

# Type checking
uv run mypy .
```

---

## 8. Known Issues & Blockers

### Current Blockers
- None

### Pending Reviews
- PR #933: Waiting for maintainer (lfnovo) review and merge

### Technical Debt
- No FIXMEs in project code
- No TODOs in project code
- Clean implementation

---

## 9. Agenten-Rollen

### Primary Agent: Sisyphus
**Role**: Power user agent for development tasks  
**Capabilities**:
- Code implementation and refactoring
- Issue tracking and task management
- Test creation and verification
- Documentation updates
- Git operations (commits, PRs)

**Workflow**:
1. Parse requirements from issues
2. Create detailed task breakdown
3. Implement changes with tests
4. Verify with automated tests
5. Document changes and create PR

### Specialized Agents
- **Metis**: Pre-planning and gap analysis
- **Momus**: Plan review and validation
- **Oracle**: Architecture and debugging consultation
- **Explore**: Codebase pattern discovery
- **Librarian**: External documentation and examples

---

## 10. Qualitätsmetriken

### Code Quality
- **Test Coverage**: 100% for Issue #893 (33/33 tests)
- **Documentation**: Complete
- **Code Style**: Consistent (ruff, mypy)
- **Security**: No secrets in commits

### Performance
- **Default max-tasks**: 5 (multi-GPU optimized)
- **Single-GPU**: Can be set to 1
- **Validation**: Prevents invalid configurations

### Development Velocity
- **Issue #893**: Completed in 1 day
- **Implementation**: 5 commits, 7 files, 33 tests
- **Review**: PR submitted, awaiting merge

---

## 11. Projekt-Roadmap

### Completed Milestones
- ✅ Issue #893 implementation (2026-06-20)
- ✅ Input validation framework
- ✅ Comprehensive testing suite
- ✅ Documentation update

### Upcoming Milestones
- 📋 PR #933 merge completion
- 📋 New feature implementation (per issue-first workflow)
- 📋 Community contributions integration

### Long-term Goals
- 🎯 Frontend real-time updates
- 🎯 Async processing improvements
- 🎯 Performance optimizations
- 🎯 Expanded documentation
- 🎯 New integrations

---

## 12. Contributing Guidelines

### Issue-First Workflow
**MUST FOLLOW**: Before any code changes:
1. Create issue describing bug/feature
2. Propose implementation approach
3. Wait for maintainer assignment
4. Only then start coding

> ⚠️ PRs without assigned issues may be closed

### Current Priority Areas
1. **Frontend Enhancement** - Next.js/React UI improvements
2. **Testing** - Expand test coverage
3. **Performance** - Async processing & caching
4. **Documentation** - API examples & user guides
5. **Integrations** - New content sources & AI providers

### PR Requirements
- ✅ Link to approved issue
- ✅ Clear change description
- ✅ Test evidence (screenshots/logs)
- ✅ Focused scope (one issue per PR)

### Testing Requirements
All contributions MUST include:
- Unit tests (pytest)
- Integration tests for API changes
- Documentation updates if behavior changes
- Code standards compliance (ruff, mypy)

---

## 13. Community & Support

### Communication Channels
- 📱 **Discord**: https://discord.gg/37XJPXfz2w (real-time help)
- 🐛 **Issues**: https://github.com/lfnovo/open-notebook/issues (bug reports & features)
- 💬 **Discussions**: GitHub Discussions (questions & ideas)
- 📚 **Documentation**: docs/ (user & developer guides)

### Documentation References
- [Design Principles](docs/7-DEVELOPMENT/design-principles.md)
- [Code Standards](docs/7-DEVELOPMENT/code-standards.md)
- [Testing Guide](docs/7-DEVELOPMENT/testing.md)
- [Development Setup](docs/7-DEVELOPMENT/development-setup.md)
- [Contributing Guide](docs/7-DEVELOPMENT/contributing.md)

---

## 14. Monitoring & Logging

### Issue Tracking
- **Active Issues**: Monitor GitHub Issues
- **PR Status**: Track Pull Requests
- **CI/CD**: GitHub Actions workflows

### Test Monitoring
- **Coverage**: Track test coverage per component
- **Results**: Document in test_status.md
- **Broken Tests**: Track in problems.md

### Performance Monitoring
- **Worker Config**: OPEN_NOTEBOOK_WORKER_MAX_TASKS (default: 5)
- **Rate Limits**: Monitor LLM provider limits
- **Resource Usage**: Track GPU/memory usage

---

## 15. Next Steps

### Immediate (Today)
1. ✅ Issue #893 implementation complete
2. ✅ PR #933 submitted
3. ⏳ Wait for maintainer review

### Short-term (This Week)
1. Monitor PR #933 status
2. Address any review feedback
3. Prepare for next issue

### Long-term (This Month)
1. Complete PR #933 merge
2. Identify new feature opportunities
3. Expand test coverage

## 16. GitHub Integration

### Personal Access Token (PAT)

**GitHub PAT** wird für die API-Integration verwendet, um Issues, PRs und Repository-Informationen direkt abzurufen.

**Token-Speicher**: `.github_pat` (im Repository, nicht in Git)

**Verwendung**:
```powershell
$PAT = Get-Content .github_pat
curl -H "Authorization: token $PAT" "https://api.github.com/repos/lfnovo/open-notebook/issues?state=open"
```

**Berechtigungen**:
- `repo` - Vollzugriff auf private Repositories
- `read:org` - Lesen von Organisationsdaten

**Aktuelle Offene Issues** (über API abgerufen):
- **#945** - Mypy Type-Checking (ready)
- **#942** - Test Coverage (ready)
- **#940** - CI Lint + Type-Check (ready)
- **#941** - Branch Protection (ready)
- **#938** - Release Tooling (ready)

**Aktuelle Offene PRs**:
- **#961** - refactor(types): type-check domain base model
- **#960** - docs: document flow-driven release process

### Workflow mit GitHub API

**Issues abrufen**:
```powershell
$PAT = Get-Content .github_pat
curl -H "Authorization: token $PAT" "https://api.github.com/repos/lfnovo/open-notebook/issues?state=open&per_page=20" | ConvertFrom-Json
```

**PRs abrufen**:
```powershell
curl -H "Authorization: token $PAT" "https://api.github.com/repos/lfnovo/open-notebook/pulls?state=open" | ConvertFrom-Json
```

**Commit status prüfen**:
```powershell
curl -H "Authorization: token $PAT" "https://api.github.com/repos/lfnovo/open-notebook/commits/main/status" | ConvertFrom-Json
```

---

## 17. Planungs-Pipeline (.sisyphus)

### Überblick

**Zweck**: Jeder Plan im Ordner `.sisyphus/plans/` MUSS die vollständige Pipeline dokumentieren, bevor die Implementierung beginnt.

**Kern-Prinzip**: **Plan First, Implement Later** - Prometheus (Planer) schreibt Pläne, Sisyphus (Implementer) führt aus.

**Mandatory Rule**: Kein Plan darf Implementierungsschritte enthalten, ohne die Pipeline-Schritte vorher zu dokumentieren.

---

### Mandatory Plan Sections

Jeder Plan in `.sisyphus/plans/` MUSS folgende 6 Sections enthalten:

```markdown
# Plan: [Title]

## TL;DR
> Quick Summary
> Deliverables (bullet list)
> Estimated Effort
> Parallel Execution: YES/NO
> Critical Path: [description]

## Context
### Original Request
### Interview Summary
### Research Findings

## Work Objectives
### Core Objective
### Concrete Deliverables
### Definition of Done
### Must Have
### Must NOT Have (Guardrails)

## Verification Strategy (MANDATORY)
> ZERO HUMAN INTERVENTION - ALL verification is agent-executed
### Test Decision
### QA Policy

## Execution Strategy
### Parallel Execution Waves
```
Wave 1 (Discovery):
├── Task 1A: [explore] description [category]
└── Task 1B: [librarian] description [category]

Wave 2 (Implementation):
├── Task 2A: [deep] description [category]
├── Task 2B: [deep] description [category]
└── Task 2C: [deep] description [category]

Wave FINAL (Verification):
└── Task FINAL: [oracle] Final Review [category]
```

**Critical Path**: [description]
**Parallel Speedup**: [estimated]
**Max Concurrent**: [number]

## TODOs

- [ ] 1. [Task title]

  **What to do**:
  - [Specific action 1]
  - [Specific action 2]

  **Must NOT do**:
  - [Forbidden action 1]

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `[category]`
    - Reason: [justification]
  - **Skills**: `["skill-1", "skill-2"]`
    - Why each skill: [justification]

  **Parallelization**:
  - **Can Run In Parallel**: YES/NO
  - **Parallel Group**: [group name]
  - **Blocks**: [list]
  - **Blocked By**: [list]

  **References**:
  - `path/to/file:line-range` - [why this matters]

  **WHY Each Reference Matters**:
  - [explanation]

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: [description]
    Tool: [tool name]
    Preconditions: [state]
    Steps:
      1. [step]
    Expected Result: [outcome]
    Failure Indicators: [what fails]
    Evidence: .sisyphus/evidence/[filename]
  ```

  **Evidence to Capture**:
  - [ ] [evidence item 1]

  **Commit**: YES/NO
  - Message: `[type]: [description]`
  - Files: `file1`, `file2`
  - Pre-commit: [checks]

---

## Commit Strategy

- `1`: `[type]: [description]` - [files]

---

## Success Criteria

### Verification Commands
```bash
# [verification command]
```

### Final Checklist
- [ ] [criteria 1]
- [ ] [criteria 2]

---

**Plan Created**: [date]  
**Related Issue**: [issue number]  
**Status**: Ready for Implementation
```

---

### Pipeline Workflow

#### Phase 1: Pre-Generation (MANDATORY)

**Step 1: Metis Consultation**

BEFORE writing any plan, Metis MUST be consulted for:

- Identifying hidden intentions in user requests
- Detecting ambiguities that require clarification
- Finding AI failure points and edge cases
- Determining if user clarification is needed

**When to skip Metis**:
- Trivial single-file changes (typo fixes, simple edits)
- Direct user instructions with no ambiguity

**Example**:
```
task(subagent_type="metis", run_in_background=false, prompt="User wants to implement test coverage. Analyze for hidden complexities, ambiguities, and AI failure points. Should we ask clarifying questions first?")
```

#### Phase 2: Plan Generation

**Step 2: Plan with Self-Clearance Check**

When writing the plan, include:

1. **Explicit clearance check**:
   ```
   ### Pre-Implementation Gate
   - [ ] Metis consultation completed (if complex)
   - [ ] All ambiguities resolved
   - [ ] User clarification obtained (if needed)
   - [ ] Oracle consulted (if architecture decision)
   ```

2. **Mandatory TODO structure**:
   - Atomic tasks (1-3 tool calls each)
   - Clear acceptance criteria
   - Evidence requirements
   - Parallelization strategy

#### Phase 3: Post-Generation (MANDATORY)

**Step 3: Self-Review**

BEFORE marking plan as 'Ready', self-review:

- [ ] All 6 mandatory sections present?
- [ ] TODOs are atomic and specific?
- [ ] Verification Strategy defined?
- [ ] Parallel execution waves clear?
- [ ] Evidence requirements specified?

**Step 4: High Accuracy Mode (Optional)**

For complex implementations, trigger Momus review:

```
task(subagent_type="momus", run_in_background=false, prompt="Review plan at .sisyphus/plans/[plan-name].md for clarity, verifiability, and completeness. Identify gaps, ambiguities, and missing context.")
```

**Momus Feedback Loop**:
1. Momus identifies issues
2. Revise plan based on feedback
3. Re-run Momus (max 3 iterations)
4. If issues persist → consult Oracle

#### Phase 4: Execution

**Step 5: Parallel Execution Waves**

Follow the execution strategy in the plan:

```
Wave 1: Discovery (parallel explore/librarian)
Wave 2: Implementation (parallel deep agents)
Wave FINAL: Verification (oracle review)
```

**Critical Rules**:
- Never wait for sequential completion
- End response after launching parallel agents
- Wait for `<system-reminder>` before collecting results
- Use `task(task_id="ses_...")` for continuation

#### Phase 5: Final Verification (MANDATORY)

**Step 6: Oracle Final Review**

BEFORE declaring task complete, run final verification:

```
task(subagent_type="oracle", run_in_background=false, prompt="Final verification for [task]. Check: 1) All acceptance criteria met, 2) Evidence captured, 3) No regressions, 4) Code quality standards followed. Return PASS/FAIL with detailed report.")
```

**Verification Checklist**:
- [ ] All TODOs marked completed
- [ ] Evidence files captured in `.sisyphus/evidence/`
- [ ] LSP diagnostics clean on changed files
- [ ] Tests passing (if applicable)
- [ ] No pre-existing issues introduced
- [ ] Commit created (if required)

---

### Draft Management

**Draft Location**: `.sisyphus/drafts/`

**Draft Lifecycle**:
1. Create draft: `.sisyphus/drafts/[issue-number]-[description].md`
2. Iterate with user feedback
3. Once approved → move to `.sisyphus/plans/`
4. Mark draft as `ARCHIVED` or delete

**Draft vs Plan**:
| Aspect | Draft | Plan |
|--------|-------|------|
| Location | `.sisyphus/drafts/` | `.sisyphus/plans/` |
| Status | Working document | Ready for execution |
| Pipeline | Optional sections | ALL mandatory sections |
| Changes | Frequent iterations | Fixed (new version if major changes) |

---

### Plan Completion Checklist

BEFORE marking any plan as 'Complete':

```
## Final Verification

- [ ] All TODOs marked `completed`
- [ ] Evidence captured:
    - [ ] `.sisyphus/evidence/[task-id]-[description].txt`
    - [ ] Screenshots/logs as needed
- [ ] Code quality:
    - [ ] `lsp_diagnostics` clean on changed files
    - [ ] `ruff check .` (Python)
    - [ ] `eslint` (Frontend)
- [ ] Tests:
    - [ ] `pytest tests/` passing
    - [ ] New tests for new functionality
- [ ] Documentation:
    - [ ] Code comments where needed
    - [ ] AGENTS.md updated (if behavior changed)
- [ ] Git:
    - [ ] Changes committed (if required)
    - [ ] Commit message follows convention
    - [ ] Pushed to fork

## Oracle Final Sign-off

Consult Oracle for final verification:

```
task(subagent_type="oracle", prompt="Final verification: [task description]. Return PASS/FAIL with evidence.")
```

- [ ] Oracle verification PASSED
```

---

**Letzte Aktualisierung**: 2026-06-23  
**Verantwortlich**: Prometheus (Planer) → Sisyphus (Implementer)  
**Status**: Mandatory für alle .sisyphus/plans/ Pläne
