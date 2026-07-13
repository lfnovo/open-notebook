# Design Principles

Engineering practices and decision-making guidance for contributors.

> **Looking for the product vision?** What Open Notebook is (and is not), the durable product
> principles, and the current posture live in **[VISION.md](../../VISION.md)** — read that first.
> The reasoning behind past structural choices lives in the
> **[decision records](decisions/README.md)**.

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

**Instead**: Focus on core use cases; say no to features that don't align with the
[vision](../../VISION.md); build extensibility points for edge cases.

### Premature Optimization

**What it looks like**:
- Optimizing code before knowing if it's slow
- Complex caching strategies without measuring impact
- Trading code clarity for marginal performance gains

**Instead**: Measure first, optimize second; focus on algorithmic improvements; profile before
making performance changes.

### Over-Engineering

**What it looks like**:
- Building abstraction layers "in case we need them later"
- Implementing design patterns for 3-line functions
- Creating frameworks instead of solving problems

**Instead**: Start simple, refactor when patterns emerge; optimize for readability; use
abstractions when they simplify, not complicate.

### Breaking Changes Without Migration Path

**What it looks like**:
- Changing database schema without migration scripts
- Modifying API contracts without versioning
- Removing features without deprecation warnings

**Instead**: Always provide migration scripts for schema changes; deprecate before removing;
document breaking changes clearly.

## 🤝 Decision-Making Framework

When evaluating new features or changes, ask:

### 1. Does it align with our vision?
- Does it help users own their research data?
- Does it support privacy and self-hosting?
- Does it fit our core use cases? (See [VISION.md](../../VISION.md))

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

**When a decision resolves a structural question** — architecture or product — capture it as a
[decision record](decisions/README.md) in the same PR. Half a page, written while the context is
still loaded.

---

## For Contributors

When proposing a feature or change:

1. **Reference the vision and principles** — explain how your proposal aligns with
   [VISION.md](../../VISION.md)
2. **Identify trade-offs** — be honest about what you're trading for what
3. **Suggest alternatives** — show you've considered other approaches
4. **Be open to feedback** — maintainers may see concerns you don't

**Remember**: A "no" to a feature isn't a judgment on you or your idea. It means we're staying
focused on our core vision. We appreciate all contributions and ideas!

---

**Questions about these principles?** Open a discussion on GitHub or join our [Discord](https://discord.gg/37XJPXfz2w).
