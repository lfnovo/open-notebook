## Description

<!-- Provide a clear and concise description of what this PR does -->

## Related Issue

<!-- This PR should be linked to an approved issue. If not, please create an issue first. -->

Fixes #<!-- issue number -->

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
- [ ] Existing tests pass (`uv run pytest`)
- [ ] Manual testing performed (describe below)

**Test Details:**
<!-- Describe your testing approach -->

## Design Alignment

<!-- This section helps ensure your PR aligns with our project vision -->

**Which design principles does this PR support?** (See [DESIGN_PRINCIPLES.md](../DESIGN_PRINCIPLES.md))

- [ ] Privacy First
- [ ] Simplicity Over Features
- [ ] API-First Architecture
- [ ] Multi-Provider Flexibility
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
- [ ] I ran linting: `make ruff` or `ruff check . --fix`
- [ ] I ran type checking: `make lint` or `uv run python -m mypy .`

### Documentation
- [ ] I have updated the relevant documentation in `/docs` (if applicable)
- [ ] I have added/updated docstrings for new/modified functions
- [ ] I have updated the API documentation (if API changes were made)
- [ ] I have added comments to complex logic

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

## Pre-Submission Verification

Before submitting, please verify:

- [ ] I have read [CONTRIBUTING.md](../CONTRIBUTING.md)
- [ ] I have read [DESIGN_PRINCIPLES.md](../DESIGN_PRINCIPLES.md)
- [ ] This PR addresses an approved issue that was assigned to me
- [ ] I have not included unrelated changes in this PR
- [ ] My PR title follows conventional commits format (e.g., "feat: add user authentication")

---

**Thank you for contributing to Open Notebook!** 🎉
