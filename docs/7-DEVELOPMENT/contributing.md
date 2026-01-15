# Contributing to Open Notebook

Thank you for your interest in contributing to Open Notebook! We welcome contributions from developers of all skill levels. This guide will help you understand our contribution workflow and what makes a good contribution.

## 🚨 Issue-First Workflow

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

1. **Search existing issues** - Check if the bug was already reported
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
2. **Understand our vision and principles** - Read [design-principles.md](design-principles.md) to understand what guides our decisions
3. **Follow our architecture** - Refer to the architecture documentation to understand project structure
4. **Write quality code** - Follow the standards outlined in [code-standards.md](code-standards.md)
5. **Test your changes** - See [testing.md](testing.md) for test guidelines
6. **Update documentation** - If you changed functionality, update the relevant docs
7. **Create your PR**:
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

## Git Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

## Development Workflow

### Branch Strategy

We use a **feature branch workflow**:

1. **Main Branch**: `main` - production-ready code
2. **Feature Branches**: `feature/description` - new features
3. **Bug Fixes**: `fix/description` - bug fixes
4. **Documentation**: `docs/description` - documentation updates

### Making Changes

1. **Create a feature branch**:
```bash
git checkout -b feature/amazing-new-feature
```

2. **Make your changes** following our coding standards

3. **Test your changes**:
```bash
# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Run formatting
uv run ruff format .
```

4. **Commit your changes**:
```bash
git add .
git commit -m "feat: add amazing new feature"
```

5. **Push and create PR**:
```bash
git push origin feature/amazing-new-feature
# Then create a Pull Request on GitHub
```

### Keeping Your Fork Updated

```bash
# Fetch upstream changes
git fetch upstream

# Switch to main and merge
git checkout main
git merge upstream/main

# Push to your fork
git push origin main
```

## Pull Request Process

When you create a pull request:

1. **Link your issue** - Reference the issue number in PR description
2. **Describe your changes** - Explain what changed and why
3. **Provide test evidence** - Screenshots, test results, or logs
4. **Check PR template** - Ensure you've completed all required sections
5. **Wait for review** - A maintainer will review your PR within a week

### PR Review Expectations

- Code review feedback is about the code, not the person
- Be open to suggestions and alternative approaches
- Address review comments with clarity and respect
- Ask questions if feedback is unclear

## Current Priority Areas

We're actively looking for contributions in these areas:

1. **Frontend Enhancement** - Help improve the Next.js/React UI with real-time updates and better UX
2. **Testing** - Expand test coverage across all components
3. **Performance** - Async processing improvements and caching
4. **Documentation** - API examples and user guides
5. **Integrations** - New content sources and AI providers

## Getting Help

### Community Support

- **Discord**: [Join our Discord server](https://discord.gg/37XJPXfz2w) for real-time help
- **GitHub Discussions**: For longer-form questions and ideas
- **GitHub Issues**: For bug reports and feature requests

### Documentation References

- [Design Principles](design-principles.md) - Understanding our project vision
- [Code Standards](code-standards.md) - Coding guidelines by language
- [Testing Guide](testing.md) - How to write tests
- [Development Setup](development-setup.md) - Getting started locally

## Recognition

We recognize contributions through:

- **GitHub credits** on releases
- **Community recognition** in Discord
- **Contribution statistics** in project analytics
- **Maintainer consideration** for active contributors

---

Thank you for contributing to Open Notebook! Your contributions help make research more accessible and private for everyone.

For questions about this guide or contributing in general, please reach out on [Discord](https://discord.gg/37XJPXfz2w) or open a GitHub Discussion.
