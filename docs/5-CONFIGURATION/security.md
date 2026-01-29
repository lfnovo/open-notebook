# Security Configuration

Protect your Open Notebook deployment with password authentication and production hardening.

---

## API Key Encryption

Open Notebook encrypts API keys stored in the database using Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256).

### Configuration Methods

| Method | Documentation |
|--------|---------------|
| **Settings UI** | [API Configuration Guide](../3-USER-GUIDE/api-configuration.md) |
| **Environment Variables** | This page (below) |

### Setup

Generate an encryption key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add to your environment:

```bash
# .env or docker.env
OPEN_NOTEBOOK_ENCRYPTION_KEY=your-generated-key-here
```

### Default Credentials

For quick setup, Open Notebook provides defaults:

| Setting | Default | Security Level |
|---------|---------|----------------|
| Password | `open-notebook-change-me` | Development only |
| Encryption Key | Derived from `0p3n-N0t3b0ok` | Development only |

**For production, always set custom credentials.**

### Docker Secrets Support

Both settings support Docker secrets via `_FILE` suffix:

```yaml
environment:
  - OPEN_NOTEBOOK_PASSWORD_FILE=/run/secrets/app_password
  - OPEN_NOTEBOOK_ENCRYPTION_KEY_FILE=/run/secrets/encryption_key
```

### Security Notes

| Scenario | Behavior |
|----------|----------|
| Custom key configured | API keys encrypted with your key |
| No key configured | API keys encrypted with default key (warning logged) |
| Key changed | Old encrypted keys become unreadable |
| Legacy data | Unencrypted keys still work (graceful fallback) |

### Key Management

- **Keep secret**: Never commit the encryption key to version control
- **Backup securely**: Store the key separately from database backups
- **No rotation yet**: Changing the key requires re-saving all API keys
- **Per-deployment**: Each instance should have its own encryption key

---

## When to Use Password Protection

### Use it for:
- Public cloud deployments (PikaPods, Railway, DigitalOcean)
- Shared network environments
- Any deployment accessible beyond localhost

### You can skip it for:
- Local development on your machine
- Private, isolated networks
- Single-user local setups

---

## Quick Setup

### Docker Deployment

```yaml
# docker-compose.yml
services:
  open_notebook:
    image: lfnovo/open_notebook:v1-latest-single
    pull_policy: always
    environment:
      - OPENAI_API_KEY=sk-...
      - OPEN_NOTEBOOK_PASSWORD=your_secure_password
    # ... rest of config
```

Or using environment file:

```bash
# docker.env
OPENAI_API_KEY=sk-...
OPEN_NOTEBOOK_PASSWORD=your_secure_password
```

### Development Setup

```bash
# .env
OPEN_NOTEBOOK_PASSWORD=your_secure_password
```

---

## Password Requirements

### Good Passwords

```bash
# Strong: 20+ characters, mixed case, numbers, symbols
OPEN_NOTEBOOK_PASSWORD=MySecure2024!Research#Tool
OPEN_NOTEBOOK_PASSWORD=Notebook$Dev$2024$Strong!

# Generated (recommended)
OPEN_NOTEBOOK_PASSWORD=$(openssl rand -base64 24)
```

### Bad Passwords

```bash
# DON'T use these
OPEN_NOTEBOOK_PASSWORD=password123
OPEN_NOTEBOOK_PASSWORD=opennotebook
OPEN_NOTEBOOK_PASSWORD=admin
```

---

## How It Works

### Frontend Protection

1. Login form appears on first visit
2. Password stored in browser session
3. Session persists until browser closes
4. Clear browser data to log out

### API Protection

All API endpoints require authentication:

```bash
# Authenticated request
curl -H "Authorization: Bearer your_password" \
  http://localhost:5055/api/notebooks

# Unauthenticated (will fail)
curl http://localhost:5055/api/notebooks
# Returns: {"detail": "Missing authorization header"}
```

### Unprotected Endpoints

These work without authentication:

- `/health` - System health check
- `/docs` - API documentation
- `/openapi.json` - OpenAPI spec

---

## API Authentication Examples

### curl

```bash
# List notebooks
curl -H "Authorization: Bearer your_password" \
  http://localhost:5055/api/notebooks

# Create notebook
curl -X POST \
  -H "Authorization: Bearer your_password" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Notebook", "description": "Research notes"}' \
  http://localhost:5055/api/notebooks

# Upload file
curl -X POST \
  -H "Authorization: Bearer your_password" \
  -F "file=@document.pdf" \
  http://localhost:5055/api/sources/upload
```

### Python

```python
import requests

class OpenNotebookClient:
    def __init__(self, base_url: str, password: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {password}"}

    def get_notebooks(self):
        response = requests.get(
            f"{self.base_url}/api/notebooks",
            headers=self.headers
        )
        return response.json()

    def create_notebook(self, name: str, description: str = None):
        response = requests.post(
            f"{self.base_url}/api/notebooks",
            headers=self.headers,
            json={"name": name, "description": description}
        )
        return response.json()

# Usage
client = OpenNotebookClient("http://localhost:5055", "your_password")
notebooks = client.get_notebooks()
```

### JavaScript/TypeScript

```javascript
const API_URL = 'http://localhost:5055';
const PASSWORD = 'your_password';

async function getNotebooks() {
  const response = await fetch(`${API_URL}/api/notebooks`, {
    headers: {
      'Authorization': `Bearer ${PASSWORD}`
    }
  });
  return response.json();
}
```

---

## Production Hardening

### Docker Security

```yaml
services:
  open_notebook:
    image: lfnovo/open_notebook:v1-latest-single
    pull_policy: always
    ports:
      - "127.0.0.1:8502:8502"  # Bind to localhost only
    environment:
      - OPEN_NOTEBOOK_PASSWORD=your_secure_password
    security_opt:
      - no-new-privileges:true
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1.0"
    restart: always
```

### Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 8502/tcp   # Block direct access
sudo ufw deny 5055/tcp   # Block direct API access
sudo ufw enable

# iptables
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -p tcp --dport 8502 -j DROP
iptables -A INPUT -p tcp --dport 5055 -j DROP
```

### Reverse Proxy with SSL

See [Reverse Proxy Configuration](reverse-proxy.md) for complete nginx/Caddy/Traefik setup with HTTPS.

---

## Security Limitations

Open Notebook's password protection provides **basic access control**, not enterprise-grade security:

| Feature | Status |
|---------|--------|
| Password transmission | Plain text (use HTTPS!) |
| Password storage | In memory |
| User management | Single password for all |
| Session timeout | None (until browser close) |
| Rate limiting | None |
| Audit logging | None |

### Risk Mitigation

1. **Always use HTTPS** - Encrypt traffic with TLS
2. **Strong passwords** - 20+ characters, complex
3. **Network security** - Firewall, VPN for sensitive deployments
4. **Regular updates** - Keep containers and dependencies updated
5. **Monitoring** - Check logs for suspicious activity
6. **Backups** - Regular backups of data

---

## Enterprise Considerations

For deployments requiring advanced security:

| Need | Solution |
|------|----------|
| SSO/OAuth | Implement OAuth2/SAML proxy |
| Role-based access | Custom middleware |
| Audit logging | Log aggregation service |
| Rate limiting | API gateway or nginx |
| Data encryption | Encrypt volumes at rest |
| Network segmentation | Docker networks, VPC |

---

## Troubleshooting

### Password Not Working

```bash
# Check env var is set
docker exec open-notebook env | grep OPEN_NOTEBOOK_PASSWORD

# Check logs
docker logs open-notebook | grep -i auth

# Test API directly
curl -H "Authorization: Bearer your_password" \
  http://localhost:5055/health
```

### 401 Unauthorized Errors

```bash
# Check header format
curl -v -H "Authorization: Bearer your_password" \
  http://localhost:5055/api/notebooks

# Verify password matches
echo "Password length: $(echo -n $OPEN_NOTEBOOK_PASSWORD | wc -c)"
```

### Cannot Access After Setting Password

1. Clear browser cache and cookies
2. Try incognito/private mode
3. Check browser console for errors
4. Verify password is correct in environment

### Security Testing

```bash
# Without password (should fail)
curl http://localhost:5055/api/notebooks
# Expected: {"detail": "Missing authorization header"}

# With correct password (should succeed)
curl -H "Authorization: Bearer your_password" \
  http://localhost:5055/api/notebooks

# Health check (should work without password)
curl http://localhost:5055/health
```

---

## Reporting Security Issues

If you discover security vulnerabilities:

1. **Do NOT open public issues**
2. Contact maintainers directly
3. Provide detailed information
4. Allow time for fixes before disclosure

---

## Related

- **[Reverse Proxy](reverse-proxy.md)** - HTTPS and SSL setup
- **[Advanced Configuration](advanced.md)** - Ports, timeouts, and SSL settings
- **[Environment Reference](environment-reference.md)** - All configuration options
