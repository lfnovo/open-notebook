# Security Configuration

Open Notebook includes optional password protection and security features for users who need to deploy their instances publicly or in shared environments.

## 🔒 Password Protection

### When to Use Password Protection

Password protection is recommended for:

- **Public cloud deployments** - PikaPods, Railway, DigitalOcean, AWS, etc.
- **Shared network environments** - Corporate networks, shared servers
- **Team deployments** - Multiple users accessing the same instance
- **Production environments** - Any deployment accessible beyond localhost

### When NOT to Use Password Protection

Skip password protection for:

- **Local development** - Running on your personal machine
- **Private networks** - Secure, isolated network environments
- **Single-user setups** - Only you have access to the machine
- **Testing environments** - Temporary or development instances

## 🚀 Quick Setup

### Docker Deployment

For Docker deployments, add the password to your environment:

```yaml
# docker-compose.yml
services:
  open_notebook:
    image: lfnovo/open_notebook:v1-latest-single
    ports:
      - "8502:8502"
    environment:
      - OPENAI_API_KEY=your_openai_key
      - OPEN_NOTEBOOK_PASSWORD=your_secure_password
    volumes:
      - ./notebook_data:/app/data
    restart: always
```

Or using a `.env` file:

```env
# .env file
OPENAI_API_KEY=your_openai_key
OPEN_NOTEBOOK_PASSWORD=your_secure_password
```

### Development Setup

For development installations, add to your `.env` file:

```env
# .env file in project root
OPEN_NOTEBOOK_PASSWORD=your_secure_password
```

## 🔐 Password Requirements

### Choosing a Secure Password

- **Length**: Minimum 12 characters, preferably 20+
- **Complexity**: Mix of uppercase, lowercase, numbers, and symbols
- **Uniqueness**: Don't reuse passwords from other services
- **Avoid**: Common words, personal information, predictable patterns

### Password Examples

```bash
# Good passwords
OPEN_NOTEBOOK_PASSWORD=MySecure2024!Research#Tool
OPEN_NOTEBOOK_PASSWORD=Notebook$Dev$2024$Strong!

# Bad passwords (don't use these)
OPEN_NOTEBOOK_PASSWORD=password123
OPEN_NOTEBOOK_PASSWORD=opennotebook
OPEN_NOTEBOOK_PASSWORD=admin
```

### Password Management

- **Use a password manager** to generate and store the password
- **Document the password** in your team's secure password vault
- **Rotate passwords** regularly for production deployments
- **Share securely** - Never send passwords via email or chat

## 🛡️ How Security Works

### React frontend Protection

When password protection is enabled:

1. **Login form** appears on first visit
2. **Session storage** - Password stored in browser session
3. **Persistent login** - Users stay logged in until browser closure
4. **No logout button** - Clear browser data to log out

### API Protection

All API endpoints require authentication:

```bash
# API calls require Authorization header
curl -H "Authorization: Bearer your_password" \
  http://localhost:5055/api/notebooks
```

### Excluded Endpoints

These endpoints work without authentication:

- **Health check**: `/health` - System status
- **API documentation**: `/docs` - OpenAPI documentation
- **OpenAPI spec**: `/openapi.json` - API schema

## 🔧 Configuration Examples

### Single Container with Security

```yaml
# docker-compose.single.yml
services:
  open_notebook_single:
    image: lfnovo/open_notebook:v1-latest-single
    ports:
      - "8502:8502"
      - "5055:5055"
    environment:
      - OPENAI_API_KEY=sk-your-openai-key
      - OPEN_NOTEBOOK_PASSWORD=your_secure_password
      - ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
    volumes:
      - ./notebook_data:/app/data
      - ./surreal_single_data:/mydata
    restart: always
```

### Multi-Container with Security

```yaml
# docker-compose.yml
services:
  surrealdb:
    image: surrealdb/surrealdb:v1-latest
    ports:
      - "127.0.0.1:8000:8000"  # Bind to localhost only
    command: start --log warn --user root --pass root file:///mydata/database.db
    volumes:
      - ./surreal_data:/mydata
    restart: always

  open_notebook:
    image: lfnovo/open_notebook:v1-latest
    ports:
      - "8502:8502"
      - "5055:5055"
    environment:
      - OPENAI_API_KEY=sk-your-openai-key
      - OPEN_NOTEBOOK_PASSWORD=your_secure_password
      - SURREAL_URL=ws://surrealdb:8000/rpc
      - SURREAL_USER=root
      - SURREAL_PASSWORD=root
    volumes:
      - ./notebook_data:/app/data
    depends_on:
      - surrealdb
    restart: always
```

### Development with Security

```env
# .env file for development
OPEN_NOTEBOOK_PASSWORD=dev_password_2024

# Database
SURREAL_URL=ws://localhost:8000/rpc
SURREAL_USER=root
SURREAL_PASSWORD=root
SURREAL_NAMESPACE=open_notebook
SURREAL_DATABASE=development

# AI Providers
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
```

## 🌐 Production Security

### HTTPS/TLS Configuration

**Always use HTTPS** in production. Here's an nginx reverse proxy example:

```nginx
# /etc/nginx/sites-available/open-notebook
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # React frontend
    location / {
        proxy_pass http://127.0.0.1:8502;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # API endpoints
    location /api/ {
        proxy_pass http://127.0.0.1:5055;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Firewall Configuration

Configure your firewall to restrict access:

```bash
# UFW (Ubuntu)
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 8502/tcp  # Block direct access to Next.js
sudo ufw deny 5055/tcp  # Block direct access to API
sudo ufw enable

# iptables
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -p tcp --dport 8502 -j DROP
iptables -A INPUT -p tcp --dport 5055 -j DROP
```

### Docker Security

```yaml
# Production docker-compose.yml with security
services:
  open_notebook:
    image: lfnovo/open_notebook:v1-latest
    ports:
      - "127.0.0.1:8502:8502"  # Bind to localhost only
      - "127.0.0.1:5055:5055"
    environment:
      - OPEN_NOTEBOOK_PASSWORD=your_secure_password
    volumes:
      - ./notebook_data:/app/data
    restart: always
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1.0"
```

## 🔍 API Authentication

### Making Authenticated API Calls

```bash
# Get all notebooks
curl -H "Authorization: Bearer your_password" \
  http://localhost:5055/api/notebooks

# Create a new notebook
curl -X POST \
  -H "Authorization: Bearer your_password" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Notebook", "description": "Research notes"}' \
  http://localhost:5055/api/notebooks

# Upload a file
curl -X POST \
  -H "Authorization: Bearer your_password" \
  -F "file=@document.pdf" \
  http://localhost:5055/api/sources/upload
```

### Python API Client

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
        data = {"name": name, "description": description}
        response = requests.post(
            f"{self.base_url}/api/notebooks",
            headers=self.headers,
            json=data
        )
        return response.json()

# Usage
client = OpenNotebookClient("http://localhost:5055", "your_password")
notebooks = client.get_notebooks()
```

## 🚨 Security Considerations

### Important Limitations

Open Notebook's password protection provides **basic access control**, not enterprise-grade security:

- **Plain text transmission** - Passwords sent over HTTP (use HTTPS)
- **No password hashing** - Passwords stored in memory as plain text
- **No user management** - Single password for all users
- **No session timeout** - Sessions persist until browser closure
- **No rate limiting** - No protection against brute force attacks
- **No audit logging** - No security event logging

### Risk Mitigation

1. **Use HTTPS** - Always encrypt traffic with TLS
2. **Strong passwords** - Use complex, unique passwords
3. **Network security** - Implement proper firewall rules
4. **Regular updates** - Keep containers and dependencies updated
5. **Monitoring** - Monitor access logs and system resources
6. **Backup strategy** - Regular backups of data and configurations

### Enterprise Considerations

For enterprise deployments requiring advanced security:

- **SSO integration** - Consider implementing OAuth2/SAML
- **Role-based access** - Implement user roles and permissions
- **Audit logging** - Track all user actions and API calls
- **Rate limiting** - Implement API rate limiting
- **Database encryption** - Encrypt data at rest
- **Network segmentation** - Isolate services in secure networks

## 🔧 Troubleshooting

### Common Security Issues

#### Password Not Working

```bash
# Check environment variable is set
docker compose exec open_notebook env | grep OPEN_NOTEBOOK_PASSWORD

# Check container logs
docker compose logs open_notebook | grep -i auth

# Test API directly
curl -H "Authorization: Bearer your_password" \
  http://localhost:5055/health
```

#### UI Shows Login Form but API Doesn't

```bash
# Environment variable might not be set for API
docker compose exec open_notebook env | grep OPEN_NOTEBOOK_PASSWORD

# Restart services
docker compose restart

# Check both services are using the same password
docker compose logs | grep -i password
```

#### 401 Unauthorized Errors

```bash
# Check authorization header format
curl -v -H "Authorization: Bearer your_password" \
  http://localhost:5055/api/notebooks

# Verify password matches environment variable
echo $OPEN_NOTEBOOK_PASSWORD

# Check for special characters in password
echo "Password contains: $(echo $OPEN_NOTEBOOK_PASSWORD | wc -c) characters"
```

#### Cannot Access After Setting Password

```bash
# Clear browser cache and cookies
# Try incognito/private mode
# Check browser console for errors
# Verify password is correct
```

### Security Testing

```bash
# Test without password (should fail)
curl http://localhost:5055/api/notebooks

# Test with correct password (should succeed)
curl -H "Authorization: Bearer your_password" \
  http://localhost:5055/api/notebooks

# Test health endpoint (should work without password)
curl http://localhost:5055/health

# Test documentation (should work without password)
curl http://localhost:5055/docs
```

## 📞 Getting Help

### Security Issues

If you discover security vulnerabilities:

1. **Do not open public issues** for security problems
2. **Contact the maintainer** directly via email
3. **Provide detailed information** about the vulnerability
4. **Allow time for fixes** before public disclosure

### Community Support

For security configuration help:

- **[Discord Server](https://discord.gg/37XJPXfz2w)** - Real-time help
- **[GitHub Issues](https://github.com/lfnovo/open-notebook/issues)** - Configuration problems
- **[Documentation](../index.md)** - Additional guides

### Best Practices

1. **Test security** thoroughly before production deployment
2. **Monitor logs** regularly for suspicious activity
3. **Keep updated** with security patches and updates
4. **Follow principle of least privilege** in network configuration
5. **Regular security reviews** of your deployment

---

**Ready to secure your deployment?** Start with the Quick Setup section above and always use HTTPS in production!