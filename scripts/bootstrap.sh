#!/bin/bash
# /scripts/bootstrap.sh
# Validates environment and starts the main application. Used in Docker CMD.

set -e

echo "--- MEV-OG BOOTSTRAP ---"

# 1. Run Environment Validation
echo "Validating environment..."
python -m src.core.config_validator

# 2. Check for required external connections (e.g., RPC)
# A more advanced script could run a mini healthcheck here before starting.

# 3. Start the Main Application
echo "Environment validated. Starting main application..."
exec python main.py
