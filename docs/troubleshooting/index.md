# Troubleshooting Guide

Welcome to the Open Notebook troubleshooting guide. This section provides comprehensive solutions for common issues, debugging techniques, and best practices for getting the most out of your Open Notebook installation.

## 📋 Quick Navigation

### 🔧 Common Issues
- [Installation Problems](./common-issues.md#installation-problems)
- [Runtime Errors](./common-issues.md#runtime-errors)
- [Performance Issues](./common-issues.md#performance-issues)
- [Configuration Problems](./common-issues.md#configuration-problems)

### ❓ Frequently Asked Questions
- [General Usage](./faq.md#general-usage)
- [AI Models and Providers](./faq.md#ai-models-and-providers)
- [Data Management](./faq.md#data-management)
- [Best Practices](./faq.md#best-practices)

### 🐛 Debugging and Analysis
- [Log Analysis](./debugging.md#log-analysis)
- [Error Diagnosis](./debugging.md#error-diagnosis)
- [Performance Profiling](./debugging.md#performance-profiling)
- [Support Information](./debugging.md#support-information)

## 🚨 Emergency Quick Fixes

### Service Not Starting
```bash
# Check all services
make status

# Restart everything
make stop-all
make start-all
```

### Database Connection Issues
```bash
# Restart database
docker compose restart surrealdb

# Check database logs
docker compose logs surrealdb
```

### API Errors
```bash
# Check API logs
docker compose logs open_notebook

# Restart API only
pkill -f "run_api.py"
make api
```

### Memory Issues
```bash
# Check resource usage
docker stats

# Increase Docker memory limit
# Docker Desktop → Settings → Resources → Memory
```

## 🔍 First Steps for Any Issue

1. **Check Service Status**
   ```bash
   make status
   ```

2. **Review Recent Logs**
   ```bash
   docker compose logs --tail=50 -f
   ```

3. **Verify Configuration**
   ```bash
   # Check environment variables
   cat .env | grep -v "API_KEY"
   
   # For Docker
   cat docker.env | grep -v "API_KEY"
   ```

4. **Test Basic Connectivity**
   ```bash
   # Database
   curl http://localhost:8000/health
   
   # API
   curl http://localhost:5055/health
   
   # UI
   curl http://localhost:8502/healthz
   ```

## 📞 Getting Help

### Community Support
- **Discord**: [https://discord.gg/37XJPXfz2w](https://discord.gg/37XJPXfz2w)
- **GitHub Issues**: [https://github.com/lfnovo/open-notebook/issues](https://github.com/lfnovo/open-notebook/issues)
- **Installation Assistant**: [ChatGPT Assistant](https://chatgpt.com/g/g-68776e2765b48191bd1bae3f30212631-open-notebook-installation-assistant)

### Before Asking for Help
1. Check this troubleshooting guide
2. Search existing GitHub issues
3. Collect relevant logs and error messages
4. Note your installation method and environment
5. Include steps to reproduce the issue

### Information to Include
- Installation method (Docker/source)
- Operating system and version
- Error messages and logs
- Configuration (without API keys)
- Steps to reproduce the issue

## 🛠️ Advanced Troubleshooting

For complex issues that aren't covered in the basic guides:

1. **Enable Debug Logging**
   ```bash
   # Add to .env or docker.env
   LOG_LEVEL=DEBUG
   ```

2. **Use Development Mode**
   ```bash
   # For more detailed error information
   make dev
   ```

3. **Check System Resources**
   ```bash
   # Monitor resource usage
   htop
   docker stats
   ```

4. **Test Individual Components**
   ```bash
   # Test database connection
   uv run python -c "from open_notebook.database.repository import repo_query; import asyncio; print(asyncio.run(repo_query('SELECT * FROM system')))"
   
   # Test AI providers
   uv run python -c "from esperanto import AIFactory; model = AIFactory.create_language('openai', 'gpt-5-mini'); print(model.chat_complete([{'role': 'user', 'content': 'Hello'}]))"
   ```

## 📚 Related Documentation

- [Installation Guide](../getting-started/installation.md)
- [Docker Deployment](../deployment/docker.md)
- [Architecture Overview](../development/architecture.md)
- [API Reference](../development/api-reference.md)

---

*This troubleshooting guide is continuously updated based on user feedback and common issues. If you encounter a problem not covered here, please contribute by opening an issue on GitHub.*