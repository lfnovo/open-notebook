# Security Guidelines

This document outlines security practices for Open Notebook development. It is informed by real vulnerabilities discovered through coordinated disclosure with [CERT-EU](https://cert.europa.eu) and should be treated as mandatory reading for all contributors.

## Reporting Vulnerabilities

If you discover a security vulnerability, **do not open a public GitHub issue**. Instead:

1. Use [GitHub Security Advisories](https://github.com/lfnovo/open-notebook/security/advisories/new) to report privately
2. Or email the maintainers directly

We follow coordinated vulnerability disclosure and will work with you on a fix before any public announcement.

---

## Database Queries (SurrealQL Injection)

**Rule: Never interpolate user input into SurrealQL queries via f-strings.**

SurrealQL injection is the equivalent of SQL injection. User-controlled values must be passed as parameterized bind variables using `$variable` syntax.

### Parameterized queries (safe)

```python
# Good: parameterized query
result = await repo_query(
    "SELECT * FROM source WHERE id = $id",
    {"id": ensure_record_id(source_id)}
)
```

### F-string interpolation (vulnerable)

```python
# Bad: user input in f-string
result = await repo_query(f"SELECT * FROM source WHERE id = {source_id}")
```

### ORDER BY and other clauses that can't be parameterized

`ORDER BY`, `LIMIT`, and similar clauses typically cannot accept bind variables in SurrealDB. Use **allowlist validation** instead:

```python
# Good: validate against allowlist, then interpolate
allowed_fields = {"name", "created", "updated"}
allowed_directions = {"asc", "desc"}

parts = order_by.strip().lower().split()
if parts[0] not in allowed_fields:
    raise HTTPException(status_code=400, detail="Invalid sort field")
if len(parts) > 1 and parts[1] not in allowed_directions:
    raise HTTPException(status_code=400, detail="Invalid sort direction")

query = f"SELECT * FROM notebook ORDER BY {validated_order_by}"
```

See `api/routers/sources.py` for the reference implementation of sort parameter validation.

### Checklist

- [ ] All user-provided values use `$variable` binding
- [ ] Any f-string in a query only contains validated/hardcoded values
- [ ] `ORDER BY`, `LIMIT`, etc. use allowlist validation
- [ ] Database values used in subsequent queries are also parameterized (prevents second-order injection)

---

## Template Rendering (Server-Side Template Injection)

**Rule: Always use `SandboxedEnvironment` when rendering Jinja2 templates that contain user-provided content.**

The [ai-prompter](https://github.com/lfnovo/ai-prompter) library (>= 0.4.0) uses `SandboxedEnvironment` by default, which blocks access to dangerous Python attributes like `__globals__`, `__subclasses__`, and `__init__`.

### What SandboxedEnvironment prevents

```jinja2
{# These are blocked and raise SecurityError #}
{{ cycler.__init__.__globals__.os.popen('id').read() }}
{{ ''.__class__.__mro__[1].__subclasses__() }}
```

### Guidelines

- Never downgrade ai-prompter below 0.4.0
- If using Jinja2 directly (outside ai-prompter), always use `jinja2.sandbox.SandboxedEnvironment`
- Never pass user-provided strings to `jinja2.Environment` or `jinja2.Template` directly

---

## File Handling (Path Traversal and Local File Inclusion)

### File uploads

**Rule: Always sanitize filenames and validate resolved paths.**

```python
import os
from pathlib import Path

# 1. Strip directory components
safe_filename = os.path.basename(original_filename)

# 2. Validate resolved path stays within target directory
resolved = (Path(upload_folder) / safe_filename).resolve()
if not str(resolved).startswith(str(Path(upload_folder).resolve()) + os.sep):
    raise ValueError("Path traversal detected")
```

Key points:

- Use `os.path.basename()` to strip directory components from user-provided filenames
- Use `Path.resolve()` to resolve symlinks and `..` components
- Use `startswith()` with a **trailing `os.sep`** to prevent sibling directory bypass (e.g., `/uploads_evil/` matching `/uploads`)

### File path inputs

**Rule: Validate that any user-provided file path is within the expected directory.**

```python
uploads_resolved = Path(UPLOADS_FOLDER).resolve()
file_resolved = Path(user_provided_path).resolve()
if not str(file_resolved).startswith(str(uploads_resolved) + os.sep):
    raise HTTPException(status_code=400, detail="Invalid file path")
```

Never pass user-provided file paths directly to file reading or content extraction functions without validation.

### Checklist

- [ ] Filenames from uploads are sanitized with `os.path.basename()`
- [ ] Resolved paths are validated with `startswith(directory + os.sep)`
- [ ] User-provided `file_path` values are validated before use
- [ ] No directory creation from user input (`mkdir` with traversal paths)

---

## Authentication and CORS

### Authentication

Open Notebook currently uses simple password-based middleware (`PasswordAuthMiddleware`). This is suitable for single-user self-hosted deployments but should be hardened for production:

- Change the default password (`OPEN_NOTEBOOK_PASSWORD`)
- Change the default encryption key (`OPEN_NOTEBOOK_ENCRYPTION_KEY`)
- Consider deploying behind a reverse proxy with proper authentication (OAuth, OIDC)

### CORS

The default CORS configuration allows all origins (`allow_origins=["*"]`). This is tracked for improvement in [#730](https://github.com/lfnovo/open-notebook/issues/730). For production deployments, restrict origins to only the frontend URL.

---

## Secrets Management

### Encryption key

`OPEN_NOTEBOOK_ENCRYPTION_KEY` is used to encrypt API keys stored in SurrealDB. In production:

- Set a strong, unique key (do not use the default)
- Use Docker secrets via `OPEN_NOTEBOOK_ENCRYPTION_KEY_FILE` when possible
- Never log or expose this value

### Environment variables

- Sensitive values (API keys, passwords, encryption keys) should never appear in logs
- Use `loguru` with caution — avoid logging full request bodies or environment dumps
- The Docker container runs as root by default; consider running as a non-root user

---

## Code Review Security Checklist

When reviewing PRs, check for:

1. **Query injection**: Any f-string containing user input in a SurrealQL query
2. **Template injection**: User-provided strings passed to Jinja2 without sandboxing
3. **Path traversal**: User-provided filenames or paths used without sanitization
4. **Information disclosure**: Error messages that expose internal paths, stack traces, or configuration
5. **SSRF**: User-provided URLs passed to server-side HTTP requests without validation
6. **Secrets in logs**: Sensitive values logged at any level

---

## Past Vulnerabilities

These vulnerabilities were reported by CERT-EU and are documented here as learning examples:

| Version | Vulnerability | Severity | Advisory |
|---------|--------------|----------|----------|
| <= 1.8.2 | SurrealDB injection via `order_by` parameter | High (8.7) | [GHSA-5wj9-f8q5-8f9c](https://github.com/lfnovo/open-notebook/security/advisories/GHSA-5wj9-f8q5-8f9c) |
| <= 1.8.3 | RCE via Jinja2 SSTI in transformations | Critical (9.2) | [GHSA-f35w-wx37-26q7](https://github.com/lfnovo/open-notebook/security/advisories/GHSA-f35w-wx37-26q7) |
| <= 1.8.3 | Arbitrary file write via path traversal | High (7.0) | [GHSA-x4q2-89g5-594v](https://github.com/lfnovo/open-notebook/security/advisories/GHSA-x4q2-89g5-594v) |
| <= 1.8.3 | Arbitrary file read via LFI | High (8.2) | [GHSA-842v-h4cj-r646](https://github.com/lfnovo/open-notebook/security/advisories/GHSA-842v-h4cj-r646) |
