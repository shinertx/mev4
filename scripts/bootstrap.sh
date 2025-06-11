#!/bin/bash
# /scripts/bootstrap.sh
# Validates environment and starts the main application. Used in Docker CMD.

set -e

REQUIRED_VARS=(EXECUTOR_PRIVATE_KEY ETH_RPC_URL_1 MEMPOOL_WSS_URL)
for var in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!var}" ]]; then
    echo "Missing required environment variable: $var" >&2
    exit 1
  fi
done

echo "--- MEV-OG BOOTSTRAP ---"

# 1. Run Environment Validation
echo "Validating environment..."
python -m src.core.config_validator

# 2. Check for required external connections (e.g., RPC)
# A more advanced script could run a mini healthcheck here before starting.

# 3. Start the Main Application
echo "Environment validated. Starting main application..."
exec python main.py
