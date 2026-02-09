## Description

<!-- Provide a clear and concise description of what this PR does -->

- **Modals:** Fix Write Note and Add Source modal positioning so they stay in the viewport; make Write Note modal draggable and resizable (min 600px, max 90vh, default 80vh); center by default and ensure editor fills modal height.
- **Layout:** Sticky headers on Notebooks list and Notebook detail pages so title, actions, and metadata stay visible while content scrolls; fix sidebar and app shell so the left nav fits in the viewport without clipping.
- **Docker:** Fix dev stack build and run: POSIX `wait-for-api.sh`, strip CRLF in Dockerfile, `.gitattributes` for `*.sh`; remove Next.js Google Font (Inter) and use system font stacks so the image builds without network in Docker.
- **API:** CORS configurable via `CORS_ORIGINS` env (comma-separated; default `*`); use in production for locked-down origins.
- **Code quality:** ESLint globals for browser (`window`, `sessionStorage`, `document`) and Node (`process`, `require`, `__dirname`, etc.); fix NoteEditorDialog lint (ResizeObserver cleanup, optional chaining on `setPointerCapture`).
- **CI:** Pin GitHub Actions to full commit SHAs (actions/checkout, actions/cache, docker/*, anthropics/claude-code-action) in all workflow files.

## Related Issue
Fixes #546

## Type of Change

<!-- Mark the relevant option with an "x" -->

- [x] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [x] Code refactoring (no functional changes)
- [ ] Performance improvement
- [ ] Test coverage improvement

## How Has This Been Tested?

<!-- Describe the tests you ran and/or how you verified your changes work -->

- [x] Tested locally with Docker
- [x] Tested locally with development setup
- [ ] Added new unit tests
- [ ] Existing tests pass (`uv run pytest`)
- [x] Manual testing performed (describe below)

**Test Details:**
- Built and ran `docker compose -f docker-compose.dev.yml up`; verified modals, notebooks list/detail headers, and sidebar layout in the browser. Ran `./scripts/save-image.sh` to confirm image save.
- Ran `uv run ruff check . --fix`, `uv run pytest tests/`, and `uv run python -m mypy .` (all passed).

## Design Alignment

<!-- This section helps ensure your PR aligns with our project vision -->

**Which design principles does this PR support?** (See [DESIGN_PRINCIPLES.md](../DESIGN_PRINCIPLES.md))

- [ ] Privacy First
- [x] Simplicity Over Features
- [x] API-First Architecture
- [ ] Multi-Provider Flexibility
- [ ] Extensibility Through Standards
- [ ] Async-First for Performance

**Explanation:**
- Layout and modal changes keep the UI simple and predictable (sticky headers, usable modals). CORS and API config support an API-first, configurable backend. GitHub Actions pinning and ESLint/CORS fixes improve maintainability and security posture.

## Checklist

<!-- Mark completed items with an "x" -->

### Code Quality
- [x] My code follows PEP 8 style guidelines (Python)
- [x] My code follows TypeScript best practices (Frontend)
- [x] I have added type hints to my code (Python)
- [ ] I have added JSDoc comments where appropriate (TypeScript)
- [x] I have performed a self-review of my code
- [x] I have commented my code, particularly in hard-to-understand areas
- [x] My changes generate no new warnings or errors

### Testing
- [ ] I have added tests that prove my fix is effective or that my feature works
- [x] New and existing unit tests pass locally with my changes (`uv run pytest`)
- [x] I ran linting: `make ruff` or `ruff check . --fix`
- [x] I ran type checking: `make lint` or `uv run python -m mypy .`

### Documentation
- [x] I have updated the relevant documentation in `/docs` (if applicable)
- [x] I have added/updated docstrings for new/modified functions
- [ ] I have updated the API documentation (if API changes were made)
- [x] I have added comments to complex logic

### Database Changes
- [ ] I have created migration scripts for any database schema changes (in `/migrations`)
- [ ] Migration includes both up and down scripts
- [ ] Migration has been tested locally

### Breaking Changes
- [ ] This PR includes breaking changes
- [ ] I have documented the migration path for users
- [ ] I have updated MIGRATION.md (if applicable)

## Screenshots (if applicable)

<!-- Add screenshots for UI changes -->

## Additional Context

<!-- Add any other context about the PR here -->

- For production, set `CORS_ORIGINS` to allowed origins (e.g. `https://app.example.com`) instead of `*`.
- `scripts/save-image.sh` is for local use only; not advertised in README.

## Pre-Submission Verification

Before submitting, please verify:

- [x] I have read [CONTRIBUTING.md](../CONTRIBUTING.md)
- [ ] I have read [DESIGN_PRINCIPLES.md](../DESIGN_PRINCIPLES.md)
- [ ] This PR addresses an approved issue that was assigned to me
- [x] I have not included unrelated changes in this PR
- [x] My PR title follows conventional commits format (e.g., "feat: add user authentication")

---

**Thank you for contributing to Open Notebook!** 🎉
