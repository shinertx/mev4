#!/bin/bash
# /infra/healthcheck.sh
# Aligns with PROJECT_BIBLE.md: Section 4
# - Provides a basic health check for the local container.

CONTAINER_NAME="mev-og-nextgen"

echo "--- Performing Healthcheck on container: ${CONTAINER_NAME} ---"

# Check if the container is running
if [ "$(docker ps -q -f name=${CONTAINER_NAME} -f status=running)" ]; then
    echo "✅ Healthcheck PASSED: Container is running."
    exit 0
else
    echo "❌ Healthcheck FAILED: Container is not running or has crashed."
    echo "--- Last 20 lines of logs ---"
    docker logs --tail 20 ${CONTAINER_NAME}
    exit 1
fi
