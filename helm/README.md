# Open Notebook Helm Chart

Open Notebook - AI-powered note-taking application with SurrealDB backend.

## Introduction

This chart bootstraps an [Open Notebook](https://github.com/lfnovo/open-notebook) deployment on a [Kubernetes](https://kubernetes.io) cluster using the [Helm](https://helm.sh) package manager.

Open Notebook is a privacy-focused, AI-powered research and note-taking tool that helps you:
- Organize research across multiple notebooks
- Chat with your documents using AI
- Support 17 AI providers (OpenAI, Anthropic, Google, Azure, Ollama, and more)
- Create AI-generated podcasts from your content
- Works with PDFs, web links, videos, audio files, and more

## Prerequisites

- Kubernetes 1.23+
- Helm 3.0+
- PV provisioner support in the underlying infrastructure (for persistence)

## Installing the Chart

To install the chart with the release name `open-notebook`:

```bash
helm install open-notebook ./helm/open-notebook
```

## Uninstalling the Chart

To uninstall/delete the `open-notebook` deployment:

```bash
helm uninstall open-notebook
```

## Configuration

See [values.yaml](values.yaml) for comprehensive configuration with Bitnami-style documentation. Key parameters include:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.registry` | Image registry | `docker.io` |
| `image.repository` | Image repository | `lfnovo/open_notebook` |
| `image.tag` | Image tag (overrides appVersion) | `""` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `surrealdb.enabled` | Deploy internal SurrealDB | `true` |
| `surrealdb.external.enabled` | Use external SurrealDB | `false` |
| `surrealdb.auth.user` | SurrealDB username | `root` |
| `surrealdb.auth.password` | SurrealDB password | `root` |
| `app.replicaCount` | Number of replicas | `1` |
| `app.ports.http` | HTTP frontend port | `8502` |
| `app.ports.api` | API server port | `5055` |
| `service.type` | Kubernetes service type | `ClusterIP` |
| `ingress.enabled` | Enable ingress | `false` |
| `secrets.create` | Create secrets automatically | `true` |
| `config.aiProviders.*` | AI provider configurations | See below |

## AI Provider Configuration

Open Notebook supports 17 AI providers across LLM, embedding, speech-to-text, and text-to-speech:

### LLM Providers (10)
- **OpenAI** - GPT-4, GPT-4 Turbo, GPT-3.5
- **Anthropic** - Claude 3 Opus, Sonnet, Haiku
- **Google Gemini** - Gemini Pro, Gemini Vision
- **Vertex AI** - Google Cloud Vertex AI models
- **Mistral** - Mistral Large, Medium, Small
- **DeepSeek** - DeepSeek Chat, DeepSeek Coder
- **Ollama** - Local OpenAI-compatible models
- **OpenRouter** - Multiple open-source models
- **Groq** - Llama 3, Mixtral, Gemma
- **XAI** - Grok models

### Multi-Modal Providers (2)
- **Azure OpenAI** - Different deployments for LLM/embedding/STT/TTS
- **OpenAI-Compatible** - Azure, FPT Cloud, or other compatible APIs

### Specialized Providers (5)
- **ElevenLabs** - Text-to-speech for podcast generation
- **Voyage AI** - Specialized embeddings
- **Firecrawl** - Web scraping and content extraction
- **Jina** - Content processing and embeddings
- **LangChain** - Debugging and tracing

### Quick Configuration

```yaml
config:
  aiProviders:
    # OpenAI
    openai:
      apiKey: "sk-your-openai-key"

    # Anthropic
    anthropic:
      apiKey: "sk-ant-your-anthropic-key"

    # Google Gemini
    google:
      apiKey: "your-google-api-key"
      geminiBaseUrl: ""  # Optional: custom endpoint

    # Azure OpenAI
    azureOpenai:
      apiKey: "your-azure-key"
      endpoint: "https://your-resource.openai.azure.com"
      apiVersion: "2024-12-01-preview"

    # OpenAI-compatible (e.g., FPT Cloud)
    openaiCompatible:
      baseUrl: "https://api.example.com/v1"
      apiKey: "your-api-key"
```

### Automatic Secret Creation

Enable automatic secret creation for API keys:

```yaml
secrets:
  create: true

config:
  aiProviders:
    openai:
      apiKey: "sk-your-key"  # Will be added to secret automatically
```

## Usage Examples

### Basic Installation with OpenAI

```bash
helm install open-notebook ./helm/open-notebook \
  --set config.aiProviders.openai.apiKey=sk-xxx
```

### Multiple AI Providers

```bash
helm install open-notebook ./helm/open-notebook \
  --set config.aiProviders.openai.apiKey=sk-xxx \
  --set config.aiProviders.anthropic.apiKey=sk-ant-xxx \
  --set config.aiProviders.google.apiKey=your-google-key
```

### Using OpenAI-Compatible Endpoint (Azure/FPT Cloud)

```yaml
config:
  aiProviders:
    openaiCompatible:
      baseUrl: "https://mkp-api.fptcloud.com/v1"
      apiKey: "sk-your-key"
```

### Vertex AI Configuration

```yaml
config:
  aiProviders:
    vertexai:
      project: "your-gcp-project"
      credentials: "base64-encoded-service-account-key"
      location: "us-east5"
```

### Using External SurrealDB

```bash
helm install open-notebook ./helm/open-notebook \
  --set surrealdb.enabled=false \
  --set surrealdb.external.enabled=true \
  --set surrealdb.external.host=surrealdb.example.com \
  --set surrealdb.external.port=8000
```

### With NodePort Service

```yaml
service:
  type: NodePort
  ports:
    http: 8502
    api: 5055
    httpNodePort: 30852
    apiNodePort: 30555

config:
  api:
    url: "http://your-node-ip:30555"
```

### With Ingress and TLS

```bash
helm install open-notebook ./helm/open-notebook \
  --set ingress.enabled=true \
  --set ingress.className=nginx \
  --set ingress.hosts[0].host=notebook.example.com \
  --set ingress.tls[0].secretName=notebook-tls \
  --set ingress.annotations."cert-manager.io/cluster-issuer"=letsencrypt-prod \
  --set config.api.url=https://notebook.example.com
```

### Custom Resources

```yaml
app:
  resources:
    limits:
      cpu: 1000m
      memory: 1Gi
    requests:
      cpu: 500m
      memory: 512Mi

surrealdb:
  resources:
    limits:
      cpu: 500m
      memory: 512Mi
    requests:
      cpu: 250m
      memory: 256Mi
```

### Prometheus Monitoring

Enable ServiceMonitor for Prometheus Operator:

```yaml
serviceMonitor:
  enabled: true
  namespace: monitoring
  interval: 30s
```

### Horizontal Scaling

Requires external SurrealDB:

```yaml
app:
  replicaCount: 3

surrealdb:
  enabled: false
  external:
    enabled: true
    host: external-surrealdb.example.com
    port: 8000
```

## Automatic Secret Management

The chart can automatically create secrets for sensitive data:

```yaml
secrets:
  create: true  # Enable automatic secret creation

config:
  aiProviders:
    openai:
      apiKey: "sk-xxx"  # Automatically added to secret
    anthropic:
      apiKey: "sk-ant-xxx"  # Automatically added to secret
```

Created secret: `open-notebook-secret` containing:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY`
- `SURREAL_PASSWORD`
- And all other configured keys

### Using Existing Secrets

For production, use existing secrets:

```bash
# Create secret manually
kubectl create secret generic open-notebook-secrets \
  --from-literal=OPENAI_API_KEY=sk-xxx \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-xxx

# Reference the secret
helm install open-notebook ./helm/open-notebook \
  --set secrets.create=false \
  --set secrets.existingSecret=open-notebook-secrets
```

## Persistence

The chart supports persistent storage for both the application and SurrealDB:

- **App Data**: `/app/data` - Stores notebooks, sources, notes, and generated content
- **SurrealDB Data**: `/mydata` - Stores the SurrealDB database files

Both are enabled by default with 8Gi PVCs. Customize the size and storage class:

```yaml
app:
  persistence:
    enabled: true
    size: 20Gi
    storageClass: fast-ssd
    mountPath: /app/data

surrealdb:
  persistence:
    enabled: true
    size: 20Gi
    storageClass: fast-ssd
    mountPath: /mydata
```

### Using Existing PVCs

```yaml
app:
  persistence:
    existingClaim: open-notebook-data

surrealdb:
  persistence:
    existingClaim: surrealdb-data
```

## Security

### Password Protection

Enable password protection:

```bash
helm install open-notebook ./helm/open-notebook \
  --set config.auth.password=your-secure-password
```

### Security Contexts

Pod and container security contexts are configurable:

```yaml
app:
  podSecurityContext:
    enabled: true
    fsGroup: 1001
    runAsUser: 1001

  containerSecurityContext:
    enabled: true
    runAsNonRoot: true
    allowPrivilegeEscalation: false
    capabilities:
      drop:
        - ALL
```

### SSL/TLS Configuration

```yaml
config:
  ssl:
    caBundle: /path/to/ca-bundle.crt
    verify: true
```

## Health Checks

Configurable probes for application health monitoring:

```yaml
app:
  livenessProbe:
    enabled: true
    path: /health
    port: api
    initialDelaySeconds: 60
    periodSeconds: 10
    timeoutSeconds: 5
    failureThreshold: 6

  readinessProbe:
    enabled: true
    path: /health
    port: api
    initialDelaySeconds: 30
    periodSeconds: 10
    timeoutSeconds: 5
    failureThreshold: 6

  startupProbe:
    enabled: false
    path: /health
    port: api
    initialDelaySeconds: 0
    failureThreshold: 30
```

## Networking

### Ingress Configuration

Enable ingress to expose Open Notebook via a domain name:

```yaml
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  hosts:
    - host: notebook.example.com
      paths:
        - path: /
          pathType: Prefix
          service: http
  tls:
    - secretName: notebook-tls
      hosts:
        - notebook.example.com
```

### Network Policy

Enable network policies to control pod traffic:

```yaml
networkPolicy:
  enabled: true
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
      - podSelector: {}
  egress:
    - to:
      - podSelector: {}
```

## Advanced Configuration

### Worker Configuration

Configure background worker behavior:

```yaml
config:
  worker:
    maxTasks: 5
    retry:
      enabled: true
      maxAttempts: 3
      waitStrategy: exponential_jitter
      waitMin: 1
      waitMax: 30
```

### Pod Disruption Budget

Ensure availability during disruptions:

```yaml
app:
  podDisruptionBudget:
    enabled: true
    minAvailable: 1
    # or
    maxUnavailable: 1
```

### Service Account

```yaml
app:
  serviceAccount:
    create: true
    name: open-notebook
    automountServiceAccountToken: false
    annotations: {}
```

### Node Selector and Tolerations

```yaml
app:
  nodeSelector:
    workload-type: gpu

  tolerations:
  - key: "nvidia.com/gpu"
    operator: "Exists"
    effect: "NoSchedule"
```

## Upgrading

To upgrade your Helm release:

```bash
helm upgrade open-notebook ./helm/open-notebook
```

To upgrade with custom values:

```bash
helm upgrade open-notebook ./helm/open-notebook \
  --set config.aiProviders.openai.apiKey=new-key \
  --set image.tag=v1.1.0
```

### Upgrade Strategy

Control deployment update behavior:

```yaml
app:
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```

## Rollback

To rollback to a previous revision:

```bash
helm rollback open-notebook
```

Or rollback to a specific revision:

```bash
helm rollback open-notebook 2
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -l app.kubernetes.io/name=open-notebook
kubectl get pods -l app.kubernetes.io/name=open-notebook-surrealdb
```

### View Logs

```bash
# Application logs
kubectl logs -l app.kubernetes.io/name=open-notebook --tail=100 -f

# SurrealDB logs
kubectl logs -l app.kubernetes.io/name=open-notebook-surrealdb --tail=100 -f
```

### Port Forward to Access

```bash
# Forward UI
kubectl port-forward svc/open-notebook 8502:8502

# Forward API
kubectl port-forward svc/open-notebook 5055:5055

# Access at http://localhost:8502
```

### SurrealDB Connection Issues

If the application can't connect to SurrealDB:

```bash
# Check SurrealDB is running
kubectl get pods -l app.kubernetes.io/name=open-notebook-surrealdb

# Port forward to SurrealDB
kubectl port-forward svc/open-notebook-surrealdb 8000:8000

# Test connection
surreal sql --endpoint ws://localhost:8000/rpc --namespace open_notebook --database production --user root --pass root
```

### Check Secrets

```bash
# List secrets
kubectl get secrets -n open-notebook

# View secret (base64 decoded)
kubectl get secret open-notebook-secret -o jsonpath='{.data.OPENAI_API_KEY}' | base64 -d
```

## Metrics and Monitoring

### Prometheus Monitoring

Enable ServiceMonitor for Prometheus Operator:

```yaml
serviceMonitor:
  enabled: true
  namespace: monitoring
  interval: 30s
  scrapeTimeout: 10s
```

Metrics will be available at:
- `http://open-notebook:8502/metrics` (application metrics)
- SurrealDB metrics can be enabled via experimental features

## License

Apache License 2.0

## Support

- GitHub: https://github.com/lfnovo/open-notebook
- Issues: https://github.com/lfnovo/open-notebook/issues
- Discord: https://discord.gg/37XJPXfz2w

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
