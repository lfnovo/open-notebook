## Description

<!-- Provide a clear and concise description of what this PR does -->

## Related Issue

<!-- Non-trivial PRs (features, architecture changes) must link an approved Issue.
     Small obvious fixes (typo, docs, tiny bug) don't need one — write "N/A (small fix)" below.
     Sizeable change without an approved Issue? Mark this PR as draft. Start a Discussion for an
     idea/feature or open an Issue for a reproducible bug, then wait for the work to be approved. -->

Fixes #<!-- issue number, or "N/A (small fix)" -->

## Type of Change

<!-- Mark the relevant option with an "x" -->

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Code refactoring (no functional changes)
- [ ] Performance improvement
- [ ] Test coverage improvement

## How Has This Been Tested?

<!-- Describe the tests you ran and/or how you verified your changes work -->

- [ ] Tested locally with Docker
- [ ] Tested locally with development setup
- [ ] Added new unit tests
- [ ] Existing tests pass (`uv run pytest tests/`, and `npm run test` in `frontend/` if the frontend changed)
- [ ] Manual testing performed (describe below)

**Test Details:**
<!-- Describe your testing approach -->

## Design Alignment

<!-- This section helps ensure your PR aligns with our project vision -->

**Which design principles does this PR support?** (See [VISION.md](https://github.com/lfnovo/open-notebook/blob/main/VISION.md))

- [ ] Privacy First
- [ ] Simplicity Over Features
- [ ] API-First Architecture
- [ ] Provider-Agnostic Core
- [ ] Extensibility Through Standards
- [ ] Async-First for Performance

**Explanation:**
<!-- Brief explanation of how your changes align with these principles -->

## Checklist

<!-- Mark completed items with an "x" -->

### Code Quality
- [ ] My code follows PEP 8 style guidelines (Python)
- [ ] My code follows TypeScript best practices (Frontend)
- [ ] I have added type hints to my code (Python)
- [ ] I have added JSDoc comments where appropriate (TypeScript)
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] My changes generate no new warnings or errors

### Testing
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] I ran linting: `uv run ruff check .`
- [ ] I ran formatting: `uv run ruff format .` (CI fails if `ruff format --check .` finds changes)
- [ ] I ran type checking: `uv run python -m mypy .`
- [ ] Frontend changes: `npm run lint`, `npm run test` and `npm run build` pass (run inside `frontend/`)

### Documentation
- [ ] I have updated the relevant documentation in `/docs` (if applicable)
- [ ] I have added/updated docstrings for new/modified functions
- [ ] I have added a CHANGELOG entry under `[Unreleased]` in the section for its type (if user-visible)
- [ ] I have added comments to complex logic

### Database Changes
- [ ] I have created migration scripts for any database schema changes (in `open_notebook/database/migrations/`, registered in `async_migrate.py`)
- [ ] Migration includes both up and down scripts
- [ ] Migration has been tested locally

### Breaking Changes
- [ ] This PR includes breaking changes
- [ ] I have documented the migration path for users
- [ ] The CHANGELOG entry explains what users must do

## Screenshots (if applicable)

<!-- Add screenshots for UI changes -->

## Additional Context

<!-- Add any other context about the PR here -->

## Pre-Submission Verification

Before submitting, please verify:

- [ ] I have read [CONTRIBUTING.md](https://github.com/lfnovo/open-notebook/blob/main/docs/7-DEVELOPMENT/contributing.md)
- [ ] I have read [VISION.md](https://github.com/lfnovo/open-notebook/blob/main/VISION.md)
- [ ] This PR addresses an approved Issue assigned to me, **or** it's a small obvious fix (typo, docs, tiny bug) that doesn't need one — ideas and features begin in Discussions; reproducible bugs begin in Issues
- [ ] I have not included unrelated changes in this PR
- [ ] My PR title follows the Conventional Commits format (e.g., "fix(podcasts): …", "feat: …")

---

**Thank you for contributing to Open Notebook!** 🎉
