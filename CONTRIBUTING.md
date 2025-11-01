# Contributing to Open Notebook

First off, thank you for considering contributing to Open Notebook! What makes open source great is the fact that we can work together and accomplish things we would never do on our own. All suggestions are welcome.

## 🚨 Important: Read Before Contributing Code

**To maintain project coherence and avoid wasted effort, please follow this process:**

1. **Create an issue first** - Before writing any code, create an issue describing the bug or feature
2. **Propose your solution** - Explain how you plan to implement the fix or feature
3. **Wait for assignment** - A maintainer will review and assign the issue to you if approved
4. **Only then start coding** - This ensures your work aligns with the project's vision and architecture

**Why this process?**
- Prevents duplicate work
- Ensures solutions align with our architecture and design principles
- Saves your time by getting feedback before coding
- Helps maintainers manage the project direction

> ⚠️ **Pull requests without an assigned issue may be closed**, even if the code is good. We want to respect your time by making sure work is aligned before it starts.

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct. Be respectful, constructive, and collaborative.

## How Can I Contribute?

### Reporting Bugs

1. **Search existing issues** - Check if the bug was already reported in [Issues](https://github.com/lfnovo/open-notebook/issues)
2. **Create a bug report** - Use the [Bug Report template](https://github.com/lfnovo/open-notebook/issues/new?template=bug_report.yml)
3. **Provide details** - Include:
   - Steps to reproduce
   - Expected vs actual behavior
   - Logs, screenshots, or error messages
   - Your environment (OS, Docker version, Open Notebook version)
4. **Indicate if you want to fix it** - Check the "I would like to work on this" box if you're interested

### Suggesting Features

1. **Search existing issues** - Check if the feature was already suggested
2. **Create a feature request** - Use the [Feature Request template](https://github.com/lfnovo/open-notebook/issues/new?template=feature_request.yml)
3. **Explain the value** - Describe why this feature would be helpful
4. **Propose implementation** - If you have ideas on how to implement it, share them
5. **Indicate if you want to build it** - Check the "I would like to work on this" box if you're interested

### Contributing Code (Pull Requests)

**IMPORTANT: Follow the issue-first workflow above before starting any PR**

Once your issue is assigned:

1. **Fork the repo** and create your branch from `main`
2. **Understand our vision and principles** - Read [DESIGN_PRINCIPLES.md](DESIGN_PRINCIPLES.md) to understand what guides our decisions
3. **Follow our architecture** - Read [docs/development/architecture.md](docs/development/architecture.md) to understand the project structure
4. **Write quality code**:
   - Follow PEP 8 for Python
   - Use TypeScript best practices for frontend
   - Add type hints and proper error handling
   - Write docstrings for functions and classes
4. **Test your changes**:
   - Add tests for new features
   - Ensure existing tests pass: `uv run pytest`
   - Run linter: `make ruff` or `ruff check . --fix`
   - Run type checker: `make lint` or `uv run python -m mypy .`
5. **Update documentation** - If you changed functionality, update the relevant docs in `/docs`
6. **Create your PR**:
   - Reference the issue number (e.g., "Fixes #123")
   - Describe what changed and why
   - Include screenshots for UI changes
   - Keep PRs focused - one issue per PR

### What Makes a Good Contribution?

✅ **We love PRs that:**
- Solve a real problem described in an issue
- Follow our architecture and coding standards
- Include tests and documentation
- Are well-scoped (focused on one thing)
- Have clear commit messages

❌ **We may close PRs that:**
- Don't have an associated approved issue
- Introduce breaking changes without discussion
- Conflict with our architectural vision
- Lack tests or documentation
- Try to solve multiple unrelated problems

## Styleguides

### Git Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

### Python Styleguide

- Follow PEP 8 guidelines
- Use type hints where possible
- Write docstrings for all functions, classes, and modules

### Documentation Styleguide

- Use Markdown for documentation files
- Reference functions and classes appropriately

## Additional Notes


Thank you for contributing to Open Notebook!