#!/bin/sh
# Wait for the API to be healthy before starting the frontend
# This prevents the "Unable to Connect to API Server" error during startup
# POSIX-compliant so it runs with /bin/sh (dash) in slim images

API_URL="${INTERNAL_API_URL:-http://localhost:5055}"
MAX_RETRIES=60
RETRY_INTERVAL=5
i=0

echo "Waiting for API to be ready at ${API_URL}/health..."

while [ $i -lt $MAX_RETRIES ]; do
    if curl -s -f "${API_URL}/health" > /dev/null 2>&1; then
        echo "API is ready! Starting frontend..."
        exit 0
    fi
    i=$((i + 1))
    echo "Attempt $i/$MAX_RETRIES: API not ready yet, waiting ${RETRY_INTERVAL}s..."
    sleep $RETRY_INTERVAL
done

echo "ERROR: API did not become ready within $((MAX_RETRIES * RETRY_INTERVAL)) seconds"
echo "Starting frontend anyway - users may see connection errors initially"
exit 0
