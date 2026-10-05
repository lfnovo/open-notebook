# Security Configuration

Password protection, credential encryption and production hardening.

Open Notebook's built-in protection is basic: one shared password, no user accounts, CORS open to every origin by default. Treat it as a lock on the door, not as enterprise security. For anything reachable from the internet, put it behind HTTPS and a firewall (see [Production hardening](#production-hardening)).

All variables on this page go in the `open_notebook` service's `environment:` block (apply with `docker compose up -d`) or in `.env` when running from source. Full list: [Environment Reference](environment-reference.md#security-and-access).

---

## API Key Encryption

AI provider keys saved in **Manage → Models** are encrypted before they are stored in SurrealDB, using Fernet (AES-128-CBC with HMAC-SHA256). The Fernet key is derived from `OPEN_NOTEBOOK_ENCRYPTION_KEY` with PBKDF2-HMAC-SHA256 (600,000 iterations).

Generate a unique value for each installation, then put it in place of `<generated-key>`:

```bash
openssl rand -hex 32                                   # macOS, Linux
```

```powershell
[guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")   # Windows PowerShell
```

```yaml
services:
  open_notebook:
    environment:
      - OPEN_NOTEBOOK_ENCRYPTION_KEY=<generated-key>
```

Don't copy an example value from any guide, including this one.

- **The key has no default.** Without it you can't save credentials: **Manage → Models** shows "Encryption key not configured" and the API logs `OPEN_NOTEBOOK_ENCRYPTION_KEY not set. API key encryption will fail until this is configured.`
- **Use a generated value.** Any string is accepted, but PBKDF2 only slows down guessing; it can't save a short, common or published passphrase.
- **Replace the placeholder.** The shipped `docker-compose.yml` sets `change-me-to-a-secret-string`. That value is public, and Open Notebook does not warn about it.
- **Don't change it once credentials are saved.** Keys encrypted with the old value can't be decrypted with the new one. Each affected credential shows **Decryption Error** in Manage → Models; delete and re-create it. There is no key-rotation command.
- **Keep it apart from your backups.** A database backup plus the key gives access to every stored provider key.

### Docker secrets

Both secrets can be read from files. The `_FILE` variant is checked first:

```yaml
environment:
  - OPEN_NOTEBOOK_PASSWORD_FILE=/run/secrets/app_password
  - OPEN_NOTEBOOK_ENCRYPTION_KEY_FILE=/run/secrets/encryption_key
```

### Upgrading to PBKDF2 (v1.15.0)

Before v1.15.0 the Fernet key was derived with a single unsalted SHA-256 hash. Since v1.15.0:

- New and edited credentials are written in the PBKDF2 format (values prefixed with `pbkdf2v1:`).
- Credentials written by older versions keep working; they are decrypted with the old derivation.
- A one-time call rewrites the old values into the new format:

```bash
# Back up the database first (see below)
curl -X POST http://localhost:5055/api/credentials/migrate-encryption \
  -H "Authorization: Bearer your_password"   # omit the header if no password is set
```

The response lists the credentials that were `migrated`, `skipped` (already in the new format) and any `errors`. Running it again changes nothing. A credential that can't be decrypted (for example because the key changed) is left untouched and reported as an error. There is no button for this in the UI.

> **Back up the database before migrating, and don't downgrade afterwards.** Versions older than 1.15.0 can't read `pbkdf2v1:` values. This already applies to any credential you add or edit on 1.15.0, migrated or not. To go back to an older version, restore a backup taken before the upgrade. Backup steps: [Advanced → Backup & Restore](advanced.md#backup--restore).

Run the migration as a single admin, while nobody is editing credentials. When `OPEN_NOTEBOOK_PASSWORD` is unset, this endpoint is open to anyone who can reach the API, like every other endpoint.

### Plaintext keys from very old versions

Values that are not encrypted at all (from versions before credential encryption existed) are still read as-is. Saving the credential again encrypts it.

---

## Password Protection

### When to use it

Set a password for any deployment reachable from something other than your own machine: a cloud host, a shared LAN, a reverse proxy on the internet. Without `OPEN_NOTEBOOK_PASSWORD`, authentication is off and anyone who can reach ports 8502 or 5055 can use the app and its stored provider keys. Open Notebook does not log a warning when the password is unset.

```yaml
services:
  open_notebook:
    environment:
      - OPEN_NOTEBOOK_ENCRYPTION_KEY=<generated-key>
      - OPEN_NOTEBOOK_PASSWORD=<generated-password>
```

Generate the password the same way as the key (`openssl rand -hex 32`, or the PowerShell command above), and use a different value for each. Non-ASCII passwords work; API clients must send them UTF-8 encoded.

### How the UI handles it

1. The login page asks for the password on first visit.
2. After a successful login the browser keeps the password in `localStorage` (key `auth-storage`), so it survives closing the browser.
3. **Sign Out** in the UI clears it. Clearing site data for the app does the same.

Anyone with access to that browser profile can read the stored password. Don't log in from shared machines.

### How the API checks it

Every request must send `Authorization: Bearer <password>`:

```bash
curl -H "Authorization: Bearer your_password" http://localhost:5055/api/notebooks
```

Without the header the API answers `401 {"detail": "Missing authorization header"}`. A wrong password gives `{"detail": "Invalid password"}`.

These paths work without a password:

| Path | Purpose |
|------|---------|
| `/` | API banner |
| `/health` | Health check, returns `{"status": "healthy"}` |
| `/docs`, `/redoc`, `/openapi.json` | API documentation |
| `/api/auth/status` | Tells the UI whether a password is required |
| `/api/config` | Version, update check and database status |

### API client examples

```bash
# Create a notebook
curl -X POST http://localhost:5055/api/notebooks \
  -H "Authorization: Bearer your_password" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Notebook", "description": "Research notes"}'

# Upload a file as a source (multipart form)
curl -X POST http://localhost:5055/api/sources \
  -H "Authorization: Bearer your_password" \
  -F "type=upload" \
  -F "file=@document.pdf"
```

```python
import requests

headers = {"Authorization": "Bearer your_password"}
notebooks = requests.get("http://localhost:5055/api/notebooks", headers=headers).json()
```

Full API documentation: `http://localhost:5055/docs` on your instance, or [API Reference](../7-DEVELOPMENT/api-reference.md).

---

## Production Hardening

### Network exposure

- **Don't publish SurrealDB.** The shipped compose file binds it to `127.0.0.1:8000`. It uses `root`/`root` unless you set `SURREAL_USER` and `SURREAL_PASSWORD` (in `.env`, which the compose file passes to both services).
- **Put a reverse proxy with HTTPS in front** and bind the app ports to localhost so only the proxy can reach them. The password travels in a header on every request, so plain HTTP exposes it. See [Reverse Proxy](reverse-proxy.md).

```yaml
services:
  open_notebook:
    ports:
      - "127.0.0.1:8502:8502"
      - "127.0.0.1:5055:5055"
```

```bash
# UFW example: allow only SSH and the reverse proxy
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Docker publishes ports by editing iptables directly, which can bypass UFW rules. Binding to `127.0.0.1` as above is the reliable way to keep a port private.

### CORS Origins

The API accepts cross-origin requests from any origin by default (`*`) and logs a warning at startup while `CORS_ORIGINS` is unset. For internet-facing deployments, list the exact origins that load the UI:

```bash
CORS_ORIGINS=https://notebook.example.com
# Several origins, comma-separated
CORS_ORIGINS=https://notebook.example.com,http://192.168.1.10:8502
```

Include the scheme and any non-default port. Restart the API after changing it (`docker compose up -d`). With the default wildcard, the API does not allow credentialed cross-origin requests; once you list origins, it does, for those origins only. Error responses carry CORS headers only for allowed origins.

Most installs never hit CORS at all: the browser loads the UI and the API from origins it is told about through `API_URL`. If you set `CORS_ORIGINS` and the UI starts failing with CORS errors, the origin you are browsing from is missing from the list.

### Other measures

```yaml
services:
  open_notebook:
    security_opt:
      - no-new-privileges:true
    deploy:
      resources:
        limits:
          memory: 4G
```

- Keep the image current: `docker compose pull && docker compose up -d`.
- Back up `./notebook_data` and `./surreal_data`, and encrypt the backups if your sources are sensitive.

---

## Limitations

| Area | Current behavior |
|------|------------------|
| Users | One shared password, no accounts or roles |
| Password in transit | A plain bearer header: use HTTPS |
| Password in the browser | Stored in `localStorage` until Sign Out |
| Sessions | No expiry; the password is sent with every request |
| Rate limiting, lockout | None |
| Audit log | None |

For single sign-on, per-user access or rate limiting, put an authenticating proxy or API gateway in front of Open Notebook.

---

## Troubleshooting

### The login keeps failing

```bash
# Which password source does the API use? (never prints the value)
docker compose exec open_notebook sh -c 'f="$OPEN_NOTEBOOK_PASSWORD_FILE"; if [ -n "$f" ] && [ -r "$f" ] && grep -q "[^[:space:]]" "$f"; then echo "set from file"; elif [ -n "$OPEN_NOTEBOOK_PASSWORD" ]; then echo "set from variable"; else echo "unset (authentication off)"; fi'

# Does the API accept it?
curl -i -H "Authorization: Bearer your_password" http://localhost:5055/api/notebooks
```

A `_FILE` path that doesn't exist or points to an empty file is ignored (the API log shows `OPEN_NOTEBOOK_PASSWORD_FILE path does not exist` or `points to empty file`), and the API falls back to `OPEN_NOTEBOOK_PASSWORD`.

If you changed the password in `docker-compose.yml`, apply it with `docker compose up -d` (`restart` keeps the old value), then sign out and log in again.

### "Unable to connect to server. Please check if the API is running."

This is the login page failing to reach the API, not a wrong password. See [Connection Issues](../6-TROUBLESHOOTING/connection-issues.md).

### Credential problems

"Encryption key not configured", "Decryption Error" and related messages are covered in [AI & Chat Issues → Credentials and encryption](../6-TROUBLESHOOTING/ai-chat-issues.md#credentials-and-encryption).

---

## Reporting Security Issues

Don't open a public issue. Use GitHub's private vulnerability reporting, as described in [SECURITY.md](../../SECURITY.md).

---

## Related

- [Reverse Proxy](reverse-proxy.md) — HTTPS setup
- [Environment Reference](environment-reference.md) — all variables
- [Developer security notes](../7-DEVELOPMENT/security.md) — threat model and implementation details
