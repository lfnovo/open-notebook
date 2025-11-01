# Retry Configuration Guide

Open Notebook includes automatic retry capabilities for background commands to handle transient failures gracefully. This guide explains how retry works and how to configure it for your deployment.

## Overview

The retry system (powered by surreal-commands v1.2.0+) automatically retries failed commands when they encounter transient errors like:

- **Database transaction conflicts** during concurrent operations
- **Network failures** when calling external APIs (embedding providers, LLMs)
- **Request timeouts** to external services
- **Rate limits** from third-party APIs

Permanent errors (invalid input, authentication failures, etc.) are **not** retried and fail immediately.

## How It Works

### Architecture

```
Command Execution
    ↓
Try to execute
    ↓
Success? → Done
    ↓
Transient Error? (RuntimeError, ConnectionError, TimeoutError)
    ↓
Retry with backoff
    ↓
Max attempts reached?
    ↓
Final failure → Report error
```

### Retry Strategies

**Exponential Jitter** (default, recommended):
- Waits: 1s → ~2s → ~4s → ~8s → ~16s (with randomization)
- Prevents "thundering herd" when many workers retry simultaneously
- Best for: Database conflicts, concurrent operations

**Exponential**:
- Waits: 1s → 2s → 4s → 8s → 16s (predictable)
- Good for: API rate limits (predictable backoff helps with quota reset)

**Fixed**:
- Waits: 2s → 2s → 2s → 2s → 2s (constant)
- Best for: Quick recovery scenarios

**Random**:
- Waits: Random between min and max
- Use when: You want unpredictable retry timing

## Global Configuration

Configure default retry behavior for **all** commands via environment variables in your `.env` file:

```bash
# Enable/disable retry globally (default: true)
SURREAL_COMMANDS_RETRY_ENABLED=true

# Maximum retry attempts before giving up (default: 3)
SURREAL_COMMANDS_RETRY_MAX_ATTEMPTS=3

# Wait strategy between retry attempts (default: exponential_jitter)
# Options: exponential_jitter, exponential, fixed, random
SURREAL_COMMANDS_RETRY_WAIT_STRATEGY=exponential_jitter

# Minimum wait time between retries in seconds (default: 1)
SURREAL_COMMANDS_RETRY_WAIT_MIN=1

# Maximum wait time between retries in seconds (default: 30)
SURREAL_COMMANDS_RETRY_WAIT_MAX=30

# Worker concurrency (affects likelihood of DB conflicts)
# Higher concurrency = more conflicts but faster processing
# Lower concurrency = fewer conflicts but slower processing
SURREAL_COMMANDS_MAX_TASKS=5
```

### Tuning Global Defaults

**For resource-constrained deployments** (low CPU/memory):
```bash
SURREAL_COMMANDS_MAX_TASKS=2
SURREAL_COMMANDS_RETRY_MAX_ATTEMPTS=3
SURREAL_COMMANDS_RETRY_WAIT_MAX=20
```
- Fewer concurrent tasks reduce conflict likelihood
- Lower max wait since conflicts are rare

**For high-performance deployments** (powerful servers):
```bash
SURREAL_COMMANDS_MAX_TASKS=10
SURREAL_COMMANDS_RETRY_MAX_ATTEMPTS=5
SURREAL_COMMANDS_RETRY_WAIT_MAX=30
```
- More concurrent tasks for faster processing
- More retries to handle increased conflicts

**For debugging** (disable retries to see immediate errors):
```bash
SURREAL_COMMANDS_RETRY_ENABLED=false
```

## Per-Command Configuration

Individual commands can override global defaults. Open Notebook uses custom retry strategies for specific operations:

### embed_chunk (Database Operations)

Handles concurrent chunk embedding with retry for transaction conflicts:

```python
@command(
    "embed_chunk",
    app="open_notebook",
    retry={
        "max_attempts": 5,
        "wait_strategy": "exponential_jitter",
        "wait_min": 1,
        "wait_max": 30,
        "retry_on": [RuntimeError, ConnectionError, TimeoutError],
    },
)
```

**What it retries**:
- SurrealDB transaction conflicts (`RuntimeError`)
- Network failures to embedding provider (`ConnectionError`)
- Request timeouts (`TimeoutError`)

**What it doesn't retry**:
- Invalid input (`ValueError`)
- Authentication errors
- Missing embedding model

**Why 5 attempts?**
Database conflicts are cheap to retry (local operation), so we retry more aggressively.

### vectorize_source & rebuild_embeddings (Orchestration)

Orchestration commands that coordinate other jobs **disable retries** to fail fast:

```python
@command("vectorize_source", app="open_notebook", retry=None)
```

**Why no retries?**
- Job submission failures should be immediately visible
- Allows quick debugging of orchestration issues
- Individual child jobs (`embed_chunk`) have their own retry logic

## Common Scenarios

### Issue: Vectorization fails with "transaction conflict" errors

**Symptoms**:
```
RuntimeError: Failed to commit transaction due to a read or write conflict
```

**Solution 1 - Reduce concurrency** (fewer conflicts):
```bash
SURREAL_COMMANDS_MAX_TASKS=3
```

**Solution 2 - Increase retry attempts**:
```bash
SURREAL_COMMANDS_RETRY_MAX_ATTEMPTS=7
```

**Solution 3 - Longer backoff** (give more time between retries):
```bash
SURREAL_COMMANDS_RETRY_WAIT_MAX=60
```

### Issue: Embedding provider rate limits (429 errors)

**Symptoms**:
```
HTTP 429: Rate limit exceeded
```

**Solution - Configure longer waits**:
```bash
SURREAL_COMMANDS_RETRY_WAIT_MIN=5
SURREAL_COMMANDS_RETRY_WAIT_MAX=120
SURREAL_COMMANDS_RETRY_WAIT_STRATEGY=exponential
```

This gives the API quota time to reset between retries.

### Issue: Slow/unstable network to embedding provider

**Symptoms**:
```
TimeoutError: Request timed out
ConnectionError: Failed to establish connection
```

**Solution - More retries with longer waits**:
```bash
SURREAL_COMMANDS_RETRY_MAX_ATTEMPTS=5
SURREAL_COMMANDS_RETRY_WAIT_MAX=60
```

### Issue: Want to see errors immediately (debugging)

**Solution - Disable retries temporarily**:
```bash
SURREAL_COMMANDS_RETRY_ENABLED=false
```

Remember to re-enable after debugging!

## Monitoring Retry Behavior

### Check Worker Logs

Retry attempts are logged automatically:

```
Transaction conflict for chunk 42 - will be retried by retry mechanism
[Retry] Attempt 2/5 for embed_chunk, waiting 2.3s
[Retry] Attempt 3/5 for embed_chunk, waiting 5.1s
Successfully embedded chunk 42
```

### Look for Retry Patterns

**High retry rate** (many retries happening):
- Consider reducing `SURREAL_COMMANDS_MAX_TASKS`
- Check if external services are slow/unstable
- May need to increase `SURREAL_COMMANDS_RETRY_WAIT_MAX`

**Retries exhausted** (commands failing after all retries):
- Check if issue is actually permanent (auth error, invalid config)
- May need to increase `SURREAL_COMMANDS_RETRY_MAX_ATTEMPTS`
- Check external service status

**No retries** (operations always succeed first try):
- Your retry configuration is working well!
- Could potentially increase `SURREAL_COMMANDS_MAX_TASKS` for better performance

## Best Practices

### ✅ Do

- **Use exponential_jitter for concurrent operations** (prevents thundering herd)
- **Set reasonable max_attempts** (3-5 for most operations)
- **Monitor retry rates** to tune configuration
- **Test retry behavior** with large documents after config changes
- **Document custom retry strategies** in your deployment notes

### ❌ Don't

- **Don't set max_attempts too high** (>10) - may mask real issues
- **Don't use fixed strategy for concurrent operations** - causes thundering herd
- **Don't disable retries in production** unless debugging
- **Don't set wait_max too low** (<5s) - may exhaust retries too quickly
- **Don't forget to re-enable retries** after debugging

## Advanced: Custom Retry Logic

If you're developing custom commands, you can configure retry behavior:

```python
from surreal_commands import command

@command(
    "my_custom_command",
    app="my_app",
    retry={
        "max_attempts": 3,
        "wait_strategy": "exponential_jitter",
        "wait_min": 1,
        "wait_max": 30,
        "retry_on": [RuntimeError, ConnectionError, TimeoutError],
    },
)
async def my_custom_command(input_data):
    try:
        # Your command logic
        result = await some_operation()
        return result

    except RuntimeError:
        # Re-raise to trigger retry
        raise

    except ValueError:
        # Don't retry - permanent error
        return {"success": False, "error": str(e)}
```

**Key points**:
- Exceptions in `retry_on` must be **re-raised** to trigger retries
- Other exceptions should be caught and returned as failures
- Transient errors: RuntimeError, ConnectionError, TimeoutError
- Permanent errors: ValueError, AuthenticationError, etc.

## Troubleshooting

### Retries not working

**Check 1**: Is retry enabled?
```bash
grep SURREAL_COMMANDS_RETRY_ENABLED .env
# Should show: SURREAL_COMMANDS_RETRY_ENABLED=true
```

**Check 2**: Is the exception being re-raised?
Check your command code - exceptions must be re-raised to trigger retries.

**Check 3**: Is the exception in `retry_on` list?
Only exceptions listed in `retry_on` are retried.

### Worker crashing on errors

**Issue**: Worker crashes instead of retrying

**Cause**: Exception is not being caught by retry mechanism

**Solution**: Check that the exception type is in the `retry_on` list and is being re-raised in the command.

### Retries taking too long

**Issue**: Commands retry forever

**Cause**: `wait_max` is too high or `max_attempts` is too high

**Solution**: Reduce retry parameters:
```bash
SURREAL_COMMANDS_RETRY_MAX_ATTEMPTS=3
SURREAL_COMMANDS_RETRY_WAIT_MAX=30
```

## References

- [surreal-commands v1.2.0 Release](https://github.com/lfnovo/surreal-commands/releases/tag/v1.2.0)
- [surreal-commands Retry Documentation](https://github.com/lfnovo/surreal-commands#retry-configuration)
- [Issue #229: Batch Vectorization Transaction Conflicts](https://github.com/lfnovo/open-notebook/issues/229)
- [Exponential Backoff Best Practices](https://en.wikipedia.org/wiki/Exponential_backoff)
