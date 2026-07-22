# Contributing to Open Notebook

Thank you for your interest in contributing to Open Notebook! We welcome contributions from developers of all skill levels. This guide will help you understand our contribution workflow and what makes a good contribution.

## 🚦 Discussions for Ideas, Issues for Work

Open Notebook separates **exploration** from **execution**:

- **Feature requests, ideas, behavior changes, product/design/architecture proposals, and contribution proposals start in [GitHub Discussions](https://github.com/lfnovo/open-notebook/discussions/new?category=ideas).** This is where the community explores the problem and maintainers make the product or design decision.
- **Reproducible bugs start in [GitHub Issues](https://github.com/lfnovo/open-notebook/issues/new/choose).**
- **Implementation starts from an approved Issue.** Once an idea is sufficiently clear and accepted, a maintainer creates an Issue from the Discussion, scopes it, and assigns it before coding begins.

This means non-trivial contributions follow one of two paths:

```text
Idea or feature → Discussion → decision → approved Issue → code → PR
Reproducible bug               → triaged Issue  → code → PR
```

**When you can skip both and just open a PR:**
- Typos, broken links, and small documentation clarifications
- Small, obvious bug fixes — a few lines, one clear right answer, no design decisions
- Translation fixes or completing missing i18n keys

**When a Discussion is definitely required first:**
- New features, of any size
- Architecture or structural changes
- Breaking changes
- Product, UX, or behavior changes
- Anything where the *how* has more than one reasonable answer

**Already coded something sizeable without prior discussion or an approved Issue?** Don't throw it away: mark the PR as **draft**. Open a Discussion for a feature or design proposal, or an Issue for a reproducible bug, and link it from the PR. A maintainer will help route the work.

**Why this process?**
- Prevents duplicate work
- Ensures solutions align with our architecture and design principles
- Saves your time by getting feedback before coding
- Helps maintainers manage the project direction

> ⚠️ **Non-trivial pull requests without an approved Issue may be closed**, even if the code is good. A Discussion is where an idea is explored; an Issue is the project's commitment to execute it.

## Code of Conduct

By participating in this project, you are expected to uphold our [Code of Conduct](/CODE_OF_CONDUCT.md). Be respectful, constructive, and collaborative.

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

1. **Search existing Discussions and Issues** - Check whether the problem is already being explored or worked on
2. **Start an Idea Discussion** - Use the [Ideas form](https://github.com/lfnovo/open-notebook/discussions/new?category=ideas)
3. **Start with the problem and outcome** - Explain what you are trying to do, what is difficult today, and what success would look like
4. **Add possible directions if useful** - Implementation ideas and references are welcome, but not required
5. **Join the exploration** - Help answer questions, evaluate trade-offs, or test prototypes
6. **Wait for graduation before coding** - If accepted, the proposal becomes one or more approved Issues that can be assigned

### Contributing Code (Pull Requests)

**IMPORTANT: For non-trivial work, start from an approved and assigned Issue before coding. Ideas reach that point through Discussions; reproducible bugs reach it through Issue triage.**

Once your issue is assigned:

1. **Fork the repo** and create your branch from `main`
2. **Understand our vision and principles** - Read [VISION.md](../../VISION.md) (what the product is and where it's going) and [design-principles.md](design-principles.md) (engineering practices)
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
- Are non-trivial and don't have an associated approved Issue (small obvious fixes are exempt — see the workflow above)
- Introduce breaking changes without discussion
- Conflict with our architectural vision
- Lack tests or documentation
- Try to solve multiple unrelated problems

### AI-Assisted and Agent-Generated PRs

A large share of contributions — including our own — are written with coding agents (Claude Code, Cursor, Copilot, etc.). That's welcome. The tool doesn't change the contract; **the operator does not stop being the author**:

1. **You own the PR.** You must have read, understood, and be able to explain every line of the diff. "The agent wrote it" is never an answer in review.
2. **Discussion before commitment; approved Issue before implementation.** Agents make it cheap to produce large unsolicited PRs — those get closed like any other unassigned PR, regardless of code quality. Small obvious fixes are exempt. For larger work, use a Discussion to shape an idea or an Issue to report a reproducible bug, then wait for an approved work item.
3. **Tests must have actually run.** Paste real output. An agent *claiming* tests pass is not test evidence.
4. **Point your agent at the right context.** The repo ships `AGENTS.md` files (root, `open_notebook/`, `frontend/`) with the normative rules, and [change-playbooks.md](change-playbooks.md) with step-by-step recipes — agents that read them produce PRs that pass review faster.
5. **Keep it scoped.** Agents tend to "improve" surrounding code along the way. Unrelated refactors belong in separate issues/PRs.

Disclosure of AI assistance is appreciated but optional — responsibility for the result is what matters, and it's yours either way.

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
- **GitHub Discussions**: For questions, ideas, features, product direction, design, and architecture
- **GitHub Issues**: For reproducible bugs and approved work items

### Documentation References

- [VISION.md](../../VISION.md) - Product identity and current posture
- [Design Principles](design-principles.md) - Engineering practices and anti-patterns
- [Decision Records](decisions/README.md) - Why things are the way they are
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
