# Test Deployment for API Configuration UI

## Quick Start

```bash
cd test-deployment
docker-compose up -d
```

## Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | Main Open Notebook UI |
| **API Keys Settings** | http://localhost:3000/settings/api-keys | New API Configuration page |
| **API Docs** | http://localhost:5055/docs | FastAPI Swagger UI |
| **SurrealDB** | ws://localhost:8000 | Database |

## Testing the API Keys Feature

1. Navigate to http://localhost:3000/settings/api-keys
2. You should see a list of all 14 providers
3. Each provider shows its configuration status (configured/not configured)
4. Click on a provider to expand and enter API key
5. Use "Test Connection" to verify the key works
6. Save the key to store in database

## Verify API Endpoints

```bash
# Check API key status
curl http://localhost:5055/api-keys/status

# Set an API key (example: OpenAI)
curl -X POST http://localhost:5055/api-keys/openai \
  -H "Content-Type: application/json" \
  -d '{"api_key": "sk-test-key"}'

# Test connection
curl -X POST http://localhost:5055/api-keys/openai/test

# Delete API key
curl -X DELETE http://localhost:5055/api-keys/openai
```

## Generate Encryption Key

For production, generate a Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add to docker-compose.yml:
```yaml
environment:
  - OPEN_NOTEBOOK_ENCRYPTION_KEY=your-generated-key-here
```

## Logs

```bash
# View logs
docker-compose logs -f open-notebook

# View just API logs
docker-compose logs -f open-notebook | grep "uvicorn"
```

## Cleanup

```bash
docker-compose down -v
```
