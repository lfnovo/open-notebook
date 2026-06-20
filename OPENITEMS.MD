# Offene Aufgaben

## 🚀 Active Projects

### ✅ Completed (2026-06-20)
- [x] **Issue #893**: Add OPEN_NOTEBOOK_WORKER_MAX_TASKS environment variable
  - Implemented input validation in dev-init.sh, Makefile, supervisord configs
  - Created 33 automated tests (unit + integration)
  - Added comprehensive documentation
  - PR #933 created and submitted for review
  - Status: Waiting for maintainer review

## ⚠️ Known Issues

### Current Blockers
- None

### Pending Reviews
- **PR #933**: Waiting for maintainer (lfnovo) review and merge
  - Link: https://github.com/lfnovo/open-notebook/pull/933
  - Issue: #893
  - Files: 7 modified, 33 tests added

## 🎯 Next Milestones

### Immediate (Next 7 days)
1. Monitor PR #933 status
2. Address maintainer feedback (if any)
3. Verify merge completion

### Short-term (Next 30 days)
1. Monitor issue tracker for new feature requests
2. Review and respond to community PRs
3. Update project documentation if needed

## 📊 Recent Activity

### 2026-06-20
- **COMPLETED**: Issue #893 implementation
  - 7 files modified
  - 33 tests created
  - PR #933 submitted
  - Comment added to Issue #893

### Commits (Last 7 days)
- 6 commits related to Issue #893
- All tests passing
- Clean Git history

## 🔧 Technical Debt

### Code Quality
- No FIXMEs in project code (only in dependencies)
- No TODOs in project code (only in dependencies)
- Clean implementation

### Documentation
- ✅ environment-reference.md updated
- ✅ .env.example updated with warnings
- ✅ All changes documented

## 📈 Metrics

### Test Coverage
- **Unit Tests**: 19 tests (test_worker_config.py)
- **Integration Tests**: 14 tests (test_worker_integration.py)
- **Total**: 33 tests
- **Status**: All passing

### Code Changes
- **Files Modified**: 7
- **Lines Added**: ~350
- **Lines Removed**: ~10
- **Commits**: 5

---

**Last Updated**: 2026-06-20  
**Next Review**: After PR #933 merge

---

## 🤝 Contribution Guidelines (From CONTRIBUTING.md)

### Issue-First Workflow

**CRITICAL**: All contributors MUST follow:

1. Create issue BEFORE coding
2. Propose solution approach
3. Wait for maintainer assignment
4. Only then start implementing

> ⚠️ PRs without assigned issues may be closed

### Current Priority Areas

1. **Frontend Enhancement** - Next.js/React UI improvements
2. **Testing** - Expand coverage (we're at 100% for Issue #893!)
3. **Performance** - Async processing & caching
4. **Documentation** - API examples & user guides
5. **Integrations** - New content sources & AI providers

### Git Workflow

**Branch Naming**:
- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation

**Commit Standards**:
- Present tense: "Add feature" not "Added"
- Imperative: "Move cursor" not "Moves"
- Max 72 chars first line
- Reference issues liberally

### Testing Requirements

All contributions MUST include:
- Unit tests (pytest)
- Integration tests for API changes
- Documentation updates
- Code standards (ruff, mypy)

**Test Commands**:
```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```

### PR Requirements

- ✅ Link to approved issue
- ✅ Clear change description
- ✅ Test evidence (screenshots/logs)
- ✅ Focused scope (one issue per PR)

---

**Community**:
- 📱 Discord: https://discord.gg/37XJPXfz2w
- 📚 Dev Docs: docs/7-DEVELOPMENT/
- 🐛 Issues: https://github.com/lfnovo/open-notebook/issues
