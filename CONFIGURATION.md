# Configuration Guide

## API Connection Configuration

Starting from version 1.0.0-alpha, Open Notebook uses a simplified API connection system that automatically configures itself based on your deployment environment.

### How It Works

The frontend automatically discovers the API location at runtime by analyzing the incoming HTTP request. This eliminates the need for complex network configurations and works for both Docker deployment modes:
- Multi-container (docker-compose with separate SurrealDB)
- Single-container (all services in one container)

**Auto-detection logic:**
1. If `API_URL` environment variable is set → use it (explicit override)
2. Otherwise, detect from the HTTP request:
   - Uses the same hostname you're accessing the frontend from
   - Automatically changes port to 5055 (API port)
   - Respects `X-Forwarded-Proto` header for reverse proxy setups
3. Falls back to `http://localhost:5055` if detection fails

**Examples:**
- Access frontend at `http://localhost:8502` → API at `http://localhost:5055` ✅
- Access frontend at `http://10.20.30.20:8502` → API at `http://10.20.30.20:5055` ✅
- Access frontend at `http://my-server:8502` → API at `http://my-server:5055` ✅

**No configuration needed** for most deployments!

### Custom Configuration

If you need to change the API URL (e.g., running on a different host, port, or domain), you can configure it using the `API_URL` environment variable.

#### Option 1: Using docker-compose (Recommended)

Edit your `docker.env` file:

```env
API_URL=http://your-server-ip:5055
```

Or add it to your `docker-compose.yml`:

```yaml
services:
  open_notebook:
    image: lfnovo/open_notebook:v1-latest
    ports:
      - "8502:8502"
      - "5055:5055"  # API port must be exposed
    environment:
      - API_URL=http://your-server-ip:5055
```

#### Option 2: Using docker run

```bash
docker run -e API_URL=http://your-server-ip:5055 \
  -p 8502:8502 \
  -p 5055:5055 \
  lfnovo/open_notebook:v1-latest-single
```

### Important Notes

1. **Port 5055 must be exposed**: The browser needs direct access to the API, so port 5055 must be mapped in your Docker configuration.

2. **Use the externally accessible URL**: The `API_URL` should be the URL that a browser can reach, not internal Docker networking addresses.

3. **Protocol matters**: Use `http://` for local deployments, `https://` if you've set up SSL.

### Examples

#### Running on a different host
```env
API_URL=http://192.168.1.100:5055
```

#### Running on a custom domain with SSL
```env
API_URL=https://notebook.example.com/api
```

#### Running on a custom port
```env
API_URL=http://localhost:3055
```
(Remember to update the port mapping in docker-compose accordingly)

### Troubleshooting

**"Unable to connect to server" error on login:**
1. Verify port 5055 is exposed in your Docker configuration
2. Check that `API_URL` matches the URL your browser can access
3. Try accessing `http://localhost:5055/health` directly in your browser
4. If that fails, the API isn't running or port isn't exposed

**API works but frontend doesn't connect:**
1. Check browser console for CORS errors
2. Verify `API_URL` is set correctly
3. Make sure you're using the same protocol (http/https) throughout

### Migration from Previous Versions

If you were previously exposing port 5055 manually or had custom configurations, you may need to:
1. Update your `docker.env` or environment variables to include `API_URL`
2. Ensure port 5055 is exposed in your docker-compose.yml (it's now required)
3. Remove any custom Next.js configuration or environment variables you may have added

The default configuration will work for most users without any changes.
