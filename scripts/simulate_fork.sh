#!/bin/bash
# /scripts/simulate_fork.sh
# Aligns with PROJECT_BIBLE.md: Section 4
# - Launches a forked mainnet environment for high-fidelity simulation and testing.

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
# Load variables from the .env file in the project root
if [ ! -f ../.env ]; then
    echo "Error: .env file not found in the project root. Please create it from .env.example."
    exit 1
fi
source ../.env

# Check for required RPC URL
: "${ETH_RPC_URL?ETH_RPC_URL not set in .env. This is required to fork mainnet.}"

# Optional: Set a specific block number to fork from for repeatable simulations.
# If not set, it will fork from the latest block.
FORK_BLOCK_NUMBER=${FORK_BLOCK_NUMBER:-"latest"}
LOCAL_RPC_PORT=8545

echo "--- Starting Anvil Fork ---"
echo "Forking from: ${ETH_RPC_URL}"
echo "Forking at block: ${FORK_BLOCK_NUMBER}"
echo "Local RPC available at: http://127.0.0.1:${LOCAL_RPC_PORT}"
echo "---------------------------"

# Launch anvil
# --fork-url: The remote node to fork the state from.
# --fork-block-number: Pins the state to a specific block for deterministic tests.
# --chain-id 31337: The default local chain ID for Hardhat/Anvil.
anvil --fork-url "${ETH_RPC_URL}" --fork-block-number "${FORK_BLOCK_NUMBER}" --chain-id 31337 --port ${LOCAL_RPC_PORT}
