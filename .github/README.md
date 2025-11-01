# GitHub Workflow & Templates

This folder contains GitHub-specific configuration for Open Notebook's contribution workflow.

## 📋 Issue Templates

We have three issue templates to guide contributors:

### 🐛 Bug Report (`ISSUE_TEMPLATE/bug_report.yml`)

For reporting bugs or unexpected behavior when the app is running but misbehaving.

**Key Features:**
- Structured format for bug details
- Environment and version information
- Checkbox for contributors who want to fix the issue
- Automatic `bug` and `needs-triage` labels

**When to Use:** App is installed and running, but something doesn't work as expected.

### ✨ Feature Request (`ISSUE_TEMPLATE/feature_request.yml`)

For suggesting new features or improvements.

**Key Features:**
- Description of the feature
- Explanation of why it would be helpful
- Space for proposed solution
- Checkbox for contributors who want to implement it
- Automatic `enhancement` and `needs-triage` labels

**When to Use:** You have an idea for a new feature or improvement.

### 🔧 Installation Issue (`ISSUE_TEMPLATE/installation_issue.yml`)

For problems with installation or setup.

**Key Features:**
- Deployment type selection
- Environment details
- Error message collection
- Automatic `installation` label

**When to Use:** Having trouble getting Open Notebook running.

## 🔄 Pull Request Template

The PR template (`pull_request_template.md`) ensures contributors provide all necessary information:

**Sections:**
- Description and related issue
- Type of change
- Testing details
- Design alignment with project principles
- Comprehensive checklist for code quality, testing, documentation
- Screenshots for UI changes

**Key Checkpoints:**
- References an approved issue
- Aligns with [design principles](../DESIGN_PRINCIPLES.md)
- Includes tests and documentation
- Follows code style guidelines

## 🚀 GitHub Actions

Our CI/CD workflows in `.github/workflows/`:

### `build-and-release.yml`
- Builds Docker images on releases
- Publishes to Docker Hub and GitHub Container Registry
- Supports multi-platform builds (amd64, arm64)

### `build-dev.yml`
- Builds dev images on pushes to main
- Tags with commit SHA for testing

### `claude-code-review.yml`
- Automated code review using Claude Code
- Runs on pull requests
- Provides AI-powered suggestions

## 📖 How the Contribution Flow Works

```
┌─────────────────────────────────────────────────────────┐
│ 1. Contributor identifies a bug or has a feature idea   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Creates an issue using appropriate template          │
│    - Describes the problem/feature                      │
│    - Checks "I am a developer..." if willing to work    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Maintainer reviews issue (within 48 hours)           │
│    - Assesses alignment with design principles          │
│    - Labels appropriately                               │
│    - Asks for clarification if needed                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 4. If approved: Contributor proposes solution approach  │
│    - Discusses implementation strategy                  │
│    - Maintainer provides feedback                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Issue is assigned to contributor                     │
│    - Contributor forks repo                             │
│    - Creates feature branch from main                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 6. Contributor develops solution                        │
│    - Reads DESIGN_PRINCIPLES.md                         │
│    - Reads docs/development/architecture.md             │
│    - Writes code, tests, documentation                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 7. Creates Pull Request                                 │
│    - Uses PR template                                   │
│    - References issue number                            │
│    - Fills out all checklist items                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 8. Maintainer reviews PR                                │
│    - Checks code quality                                │
│    - Verifies tests pass                                │
│    - Ensures alignment with architecture                │
│    - Provides feedback or approves                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 9. If approved: PR is merged! 🎉                        │
│    - Contributor is thanked                             │
│    - Issue is closed                                    │
│    - Changes included in next release                   │
└─────────────────────────────────────────────────────────┘
```

## 🎯 Why This Process?

### Prevents Wasted Effort
- Contributors don't spend time on code that won't be merged
- Ensures alignment with project vision before coding starts

### Maintains Quality
- All code reviewed against design principles
- Consistent architecture across contributions
- Proper testing and documentation

### Respects Everyone's Time
- Clear expectations upfront
- Structured feedback process
- Efficient review process

### Protects Project Vision
- Maintainers can guide direction
- Features align with long-term goals
- Technical debt is minimized

## 📚 Related Documentation

For contributors:
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [DESIGN_PRINCIPLES.md](../DESIGN_PRINCIPLES.md) - Project vision and principles
- [docs/development/architecture.md](../docs/development/architecture.md) - Technical architecture

For maintainers:
- [MAINTAINER_GUIDE.md](../MAINTAINER_GUIDE.md) - How to review and manage contributions

## 🤝 Questions?

- Join our [Discord](https://discord.gg/37XJPXfz2w)
- Open a [Discussion](https://github.com/lfnovo/open-notebook/discussions)
- Read the [FAQ](../docs/troubleshooting/faq.md)

---

**Thank you for contributing to Open Notebook!** Your contributions help make this the best open-source research tool available.
