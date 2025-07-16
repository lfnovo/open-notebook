# Security

Open Notebook includes optional password protection for users who need to deploy their instances publicly.

## Password Protection

### When to Use Password Protection

- **Public Hosting**: When deploying on cloud services like PikaPods, DigitalOcean, AWS, etc.
- **Shared Networks**: When running on networks where others might access your instance
- **Team Deployments**: When multiple people need controlled access to the same instance

### When NOT to Use Password Protection

- **Local Development**: When running on your local machine for personal use
- **Private Networks**: When running on secure, private networks
- **Single User**: When you're the only person with access to the machine

## Setup

### 1. Environment Configuration

Add the password to your environment configuration:

**For regular deployment:**
```bash
# In your .env file
OPEN_NOTEBOOK_PASSWORD=your_secure_password_here
```

**For Docker deployment:**
```bash
# In your docker.env file
OPEN_NOTEBOOK_PASSWORD=your_secure_password_here
```

### 2. Password Requirements

- Use a strong, unique password
- Avoid common passwords or dictionary words
- Consider using a password manager to generate and store the password
- The password is case-sensitive

### 3. Restart Services

After setting the password, restart all services:

```bash
# If using make commands
make stop-all
make start-all

# If using Docker
docker compose down
docker compose --profile multi up
```

## How It Works

### Streamlit UI Protection

- Users see a login form when accessing the application
- Password is stored in the browser session
- Users remain logged in until they close the browser or clear session data
- No logout button is provided - users can clear browser data to log out

### API Protection

- All API endpoints require the password in the Authorization header
- Format: `Authorization: Bearer your_password`
- Health check endpoint (`/health`) is excluded from authentication
- API documentation (`/docs`) is excluded from authentication

### Example API Usage

```bash
# Without password protection
curl http://localhost:5055/api/notebooks

# With password protection
curl -H "Authorization: Bearer your_password" http://localhost:5055/api/notebooks
```

## Security Considerations

### This is Basic Protection

The password protection is designed for basic access control, not enterprise security:

- Passwords are transmitted and stored in plain text
- No user roles or permissions system
- No session management or timeout
- No password complexity requirements
- No protection against brute force attacks

### Production Recommendations

For production deployments requiring robust security:

1. **Use HTTPS**: Always deploy behind HTTPS/TLS
2. **Reverse Proxy**: Use nginx or similar with additional security headers
3. **Network Security**: Implement proper firewall rules
4. **Regular Updates**: Keep Open Notebook and dependencies updated
5. **Monitoring**: Log access attempts and monitor for suspicious activity

## Troubleshooting

### Common Issues

**401 Unauthorized Errors:**
- Check that the password is set correctly in your environment
- Verify the Authorization header format: `Bearer your_password`
- Restart all services after setting the password

**UI Not Showing Login Form:**
- Ensure the `OPEN_NOTEBOOK_PASSWORD` environment variable is set
- Check that the Streamlit service restarted properly
- Clear browser cache and cookies

**API Calls Failing:**
- Verify the password is included in the Authorization header
- Check that the API service has access to the environment variable
- Test with a simple curl command first

### Getting Help

If you encounter issues with password protection:

1. Check the application logs for error messages
2. Verify environment variables are set correctly
3. Test with a simple password first
4. Join our [Discord server](https://discord.gg/37XJPXfz2w) for community support
5. Report bugs on [GitHub Issues](https://github.com/lfnovo/open-notebook/issues)