# Design Principles & Project Vision

This document outlines the core principles, vision, and design philosophy that guide Open Notebook's development. All contributors should read and understand these principles before proposing changes or new features.

## 🎯 Project Vision

Open Notebook aims to be a **privacy-focused, self-hosted alternative to Google's Notebook LM** that empowers users to:

1. **Own their research data** - Full control over where data lives and who can access it
2. **Choose their AI providers** - Freedom to use any AI provider or run models locally
3. **Customize their workflows** - Flexibility to adapt the tool to different research needs
4. **Access their work anywhere** - Through web UI, API, or integrations

### What Open Notebook IS

- A **research assistant** for managing and understanding content
- A **platform** that connects various AI providers
- A **privacy-first** tool that keeps your data under your control
- An **extensible system** with APIs and customization options

### What Open Notebook IS NOT

- A document editor (use Google Docs, Notion, etc. for that)
- A file storage system (use Dropbox, S3, etc. for that)
- A general-purpose chatbot (use ChatGPT, Claude, etc. for that)
- A replacement for your entire workflow (it's one tool in your toolkit)

## 🏗️ Core Design Principles

### 1. Privacy First

**Principle**: User data and research should stay under user control by default.

**In Practice**:
- Self-hosted deployment is the primary use case
- No telemetry or analytics without explicit opt-in
- No hard dependency on specific cloud services
- Clear documentation on what data goes where

**Example Decisions**:
- ✅ Support for local Ollama models
- ✅ Configurable AI provider selection
- ❌ Hard-coded cloud service integrations
- ❌ Required external service dependencies

### 2. Simplicity Over Features

**Principle**: The tool should be easy to understand and use, even if it means fewer features.

**In Practice**:
- Clear, focused UI with well-defined sections
- Sensible defaults that work for most users
- Advanced features hidden behind optional configuration
- Documentation written for non-technical users

**Example Decisions**:
- ✅ Three-column layout (Sources, Notes, Chat)
- ✅ Default models that work out of the box
- ❌ Overwhelming users with too many options upfront
- ❌ Complex multi-step workflows for basic tasks

### 3. API-First Architecture

**Principle**: All functionality should be accessible via API, not just the UI.

**In Practice**:
- UI calls the same API that external clients use
- Comprehensive REST API with OpenAPI documentation
- No "UI-only" features that can't be automated
- Clear separation between frontend and backend

**Example Decisions**:
- ✅ FastAPI backend with full API documentation
- ✅ Consistent API patterns across all endpoints
- ❌ Business logic in UI components
- ❌ Features that require direct database access

### 4. Multi-Provider Flexibility

**Principle**: Users should never be locked into a single AI provider.

**In Practice**:
- Support for multiple AI providers through Esperanto library
- Easy switching between providers and models
- Clear documentation on provider limitations
- Graceful degradation when providers are unavailable

**Example Decisions**:
- ✅ Support for 16+ AI providers
- ✅ Per-feature model selection (chat, embeddings, TTS)
- ❌ Features that only work with OpenAI
- ❌ Hard-coded API endpoints for specific providers

### 5. Extensibility Through Standards

**Principle**: The system should be extensible through well-defined interfaces, not by forking.

**In Practice**:
- Plugin systems for transformations and commands
- Standard data formats (JSON, Markdown)
- Clear extension points in the architecture
- Documentation for common customization scenarios

**Example Decisions**:
- ✅ Custom transformation templates
- ✅ Background command system
- ✅ Jinja2 prompt templates
- ❌ Hard-coded business logic without extension points

### 6. Async-First for Performance

**Principle**: Long-running operations should not block the user interface or API.

**In Practice**:
- Async/await patterns throughout the backend
- Background job processing for heavy workloads
- Status updates and progress tracking
- Graceful handling of slow AI provider responses

**Example Decisions**:
- ✅ AsyncIO for database operations
- ✅ Background commands for podcast generation
- ✅ Streaming responses for chat
- ❌ Synchronous blocking operations in API endpoints

## 🎨 UI/UX Principles

### Focus on Content, Not Chrome

- Minimize UI clutter and distractions
- Content should occupy most of the screen space
- Controls appear when needed, not always visible
- Consistent layout across different views

### Progressive Disclosure

- Show simple options first, advanced options on demand
- Don't overwhelm new users with every possible setting
- Provide sensible defaults that work for 80% of use cases
- Make power features discoverable but not intrusive

### Responsive and Fast

- UI should feel instant for common operations
- Show loading states for operations that take time
- Cache and optimize where possible
- Degrade gracefully on slow connections

## 🔧 Technical Principles

### Clean Separation of Concerns

**Layers should not leak**:
- Frontend should not know about database structure
- API should not contain business logic (delegate to domain layer)
- Domain models should not know about HTTP requests
- Database layer should not know about AI providers

### Type Safety and Validation

**Catch errors early**:
- Use Pydantic models for all API boundaries
- Type hints throughout Python codebase
- TypeScript for frontend code
- Validate data at system boundaries

### Test What Matters

**Focus on valuable tests**:
- Test business logic and domain models
- Test API contracts and error handling
- Don't test framework code (FastAPI, React, etc.)
- Integration tests for critical workflows

### Database as Source of Truth

**SurrealDB is our single source of truth**:
- All state persisted in database
- No business logic in database layer
- Use SurrealDB features (record links, queries) appropriately
- Schema migrations for all schema changes

## 🚫 Anti-Patterns to Avoid

### Feature Creep

**What it looks like**:
- Adding features because they're "cool" or "easy"
- Building features for edge cases before common cases work well
- Trying to be everything to everyone

**Why we avoid it**:
- Increases complexity and maintenance burden
- Makes the tool harder to learn and use
- Dilutes the core value proposition

**Instead**:
- Focus on core use cases
- Say no to features that don't align with vision
- Build extensibility points for edge cases

### Premature Optimization

**What it looks like**:
- Optimizing code before knowing if it's slow
- Complex caching strategies without measuring impact
- Trading code clarity for marginal performance gains

**Why we avoid it**:
- Makes code harder to understand and maintain
- Optimizes the wrong things
- Wastes development time

**Instead**:
- Measure first, optimize second
- Focus on algorithmic improvements
- Profile before making performance changes

### Over-Engineering

**What it looks like**:
- Building abstraction layers "in case we need them later"
- Implementing design patterns for 3-line functions
- Creating frameworks instead of solving problems

**Why we avoid it**:
- Increases cognitive load for contributors
- Makes simple changes require touching many files
- Hides the actual business logic

**Instead**:
- Start simple, refactor when patterns emerge
- Optimize for readability and clarity
- Use abstractions when they simplify, not complicate

### Breaking Changes Without Migration Path

**What it looks like**:
- Changing database schema without migration scripts
- Modifying API contracts without versioning
- Removing features without deprecation warnings

**Why we avoid it**:
- Breaks existing installations
- Frustrates users and contributors
- Creates maintenance nightmares

**Instead**:
- Always provide migration scripts for schema changes
- Deprecate before removing
- Document breaking changes clearly

## 🤝 Decision-Making Framework

When evaluating new features or changes, ask:

### 1. Does it align with our vision?
- Does it help users own their research data?
- Does it support privacy and self-hosting?
- Does it fit our core use cases?

### 2. Does it follow our principles?
- Is it simple to use and understand?
- Does it work via API?
- Does it support multiple providers?
- Can it be extended by users?

### 3. Is the implementation sound?
- Does it maintain separation of concerns?
- Is it properly typed and validated?
- Does it include tests?
- Is it documented?

### 4. What is the cost?
- How much complexity does it add?
- How much maintenance burden?
- Does it introduce new dependencies?
- Will it be used enough to justify the cost?

### 5. Are there alternatives?
- Can existing features solve this problem?
- Can this be built as a plugin or extension?
- Should this be a separate tool instead?

## 📚 Examples of Principle-Driven Decisions

### Why we migrated from Streamlit to Next.js

**Principle**: API-First Architecture

**Reasoning**:
- Streamlit coupled UI and backend logic
- Difficult to build external integrations
- Limited control over API behavior
- Next.js + FastAPI provides clear separation

### Why we use Esperanto for AI providers

**Principle**: Multi-Provider Flexibility

**Reasoning**:
- Abstracts provider-specific details
- Easy to add new providers
- Consistent interface across providers
- No vendor lock-in

### Why we have a Background Command System

**Principle**: Async-First for Performance

**Reasoning**:
- Podcast generation takes minutes
- Users shouldn't wait for long operations
- Need status tracking and error handling
- Supports future batch operations

### Why we support Local Ollama

**Principle**: Privacy First

**Reasoning**:
- Enables fully offline operation
- No data sent to external services
- Free for users after hardware cost
- Aligns with self-hosted philosophy

## 🔄 Evolution of Principles

These principles are not set in stone. As the project grows and we learn from users, some principles may evolve. However, changes to core principles should be:

1. **Well-justified** - Clear reasoning for why the change is needed
2. **Discussed openly** - Community input on major changes
3. **Documented** - Updated in this document with explanation
4. **Gradual** - Not implemented as breaking changes when possible

---

## For Contributors

When proposing a feature or change:

1. **Reference these principles** - Explain how your proposal aligns
2. **Identify trade-offs** - Be honest about what you're trading for what
3. **Suggest alternatives** - Show you've considered other approaches
4. **Be open to feedback** - Maintainers may see concerns you don't

**Remember**: A "no" to a feature isn't a judgment on you or your idea. It means we're staying focused on our core vision. We appreciate all contributions and ideas!

---

**Questions about these principles?** Open a discussion on GitHub or join our [Discord](https://discord.gg/37XJPXfz2w).
