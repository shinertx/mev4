# MEV-OG NextGen

[![CI](https://github.com/your-org/mev-og/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/mev-og/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview
MEV-OG NextGen is a modular trading engine focused on MEV and arbitrage across both
DeFi and CeFi venues. It follows the operational and security guidelines
in [PROJECT_BIBLE.md](PROJECT_BIBLE.md) and is designed to be AI-driven,
kill-switch aware, and GCP ready.

## Architecture & Core Concepts
- **Modular design**: core logic in `src/core`, adapters in `src/adapters`, and
  strategy modules in `src/strategies`.
- **DRP snapshots**: session state is persisted so every agent can roll back or
  recover on failure.
- **Kill switch**: `src/core/kill.py` enforces a global circuit breaker checked by
  every strategy.
- **Mutation flow**: new strategy parameters are applied with audit logging and
  optional manual approval.

## Directory Map
```
abis/                # ABI helpers
contracts/           # Solidity smart contracts
infra/               # Docker, deploy scripts and configs
scripts/             # Helper scripts for setup and simulation
src/                 # Python source code
src/abis/            # ABI imports for adapters
src/adapters/        # DEX, CEX, bridge, oracle adapters
src/core/            # State, kill switch, DRP, logging
src/strategies/      # Trading strategies
test/                # Pytest and solidity tests
```

## Environment Variables
| Name | Default | Description |
| ---- | ------- | ----------- |
| `EXECUTOR_PRIVATE_KEY` | `0x00` | Hot wallet private key |
| `ETH_RPC_URL_1` | ⬜ | Primary RPC endpoint |
| `ETH_RPC_URL_2` | ⬜ | Secondary RPC endpoint |
| `ETH_RPC_URL_3` | ⬜ | Tertiary RPC endpoint |
| `MEMPOOL_WSS_URL` | `wss://dummy.local` | Mempool websocket |
| `BINANCE_API_KEY` | ⬜ | CEX API key |
| `BINANCE_API_SECRET` | ⬜ | CEX API secret |
| `AI_MODEL_API_URL` | `https://api.openai.com/v1/chat/completions` | LLM endpoint |
| `CEX_BASE_URL` | `https://api.binance.com` | CEX base REST URL |
| `OPENAI_API_KEY` | ⬜ | Optional LLM key |
| `LOG_SIGNING_KEY` | ⬜ | Optional audit log key |
| `SENTRY_DSN` | ⬜ | Sentry reporting URL |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `HEALTH_PORT` | `8080` | Port for `/healthz` |
| `SESSION_DIR` | `/tmp/mev_og_session` | DRP snapshot location |
| `REDIS_URL` | `redis://localhost:6379/0` | Replay protection store |
| `MANUAL_APPROVAL` | `false` | Require approval for mutations |
| `CONTROL_API_TOKEN` | ⬜ | Token for control API |
| `MUTATION_TTL_SECONDS` | `3600` | Mutation cache TTL |
| `GCP_PROJECT_ID` | ⬜ | Google Cloud project ID |
| `GCP_REGION` | ⬜ | Google Cloud region |
| `chain_id` | `1` | Target chain ID |
| `UNISWAP_ROUTER_ADDRESS` | ⬜ | Router address for DEX adapter |
| `SANDWICH_MIN_PROFIT` | ⬜ | Minimum profit (USD) to attempt |

## Local Dev Setup
```bash
# clone and enter repo
git clone <repo-url>
cd <repo>

# create local env
cp .env.example .env
# edit .env with your keys

# install deps
pip install -r requirements.txt
pip install flake8 pytest pytest-asyncio

# run lint & tests
flake8 src/ test/
pytest
```

## Quick-Start / Testnet Guide
### Local via `bootstrap.sh`
```bash
./scripts/bootstrap.sh
```
### Docker Compose
```bash
cd infra
docker-compose up --build
```
### Cloud Run
```bash
cd infra
./deploy.sh
```
Deployment parameters are defined in `infra/cloudrun.yaml`.

## Production Checklist & Liveness
- Ensure all required secrets exist in GCP Secret Manager.
- Run `infra/healthcheck.sh` to verify the container is running.
- HTTP `GET /healthz` returns `{"status": "ok"}` when live.

## Commands Reference
- `scripts/bootstrap.sh` – validate env and start app
- `scripts/simulate_fork.sh` – start a forked Anvil node
- `infra/deploy.sh` – build and deploy to Cloud Run
- `infra/healthcheck.sh` – container liveness check

## Post-Deploy Actions
Verify the Cloud Run service URL and monitor metrics in GCP. Update
secrets and environment variables if strategy parameters change.

## Risk Warnings / Kill-Switch
### Audit Status
⬜ audited by third party
### Legal Disclaimer
> WARN: All trading strategies are experimental and may result in fund loss.
Use at your own risk. Compliance with local regulations is your responsibility.

## Upgrade Path & Versioning
Contracts use Solidity `^0.8.10`. No proxy pattern is defined ⬜.
The repo follows Semantic Versioning for releases.

## Testing & CI Matrix
- `pytest` for unit and integration tests
- Fork simulation via `scripts/simulate_fork.sh`
- Solidity tests such as `test/test_reentrancy_attack.sol`
- GitHub Actions runs lint and tests on push

## Contributing & FAQ
Follow guidelines in [AGENTS.md](AGENTS.md). Run `flake8` and
`pytest` before committing. Questions can be opened as GitHub issues.

## License
Distributed under the [MIT](LICENSE) license.

✅ README draft complete
