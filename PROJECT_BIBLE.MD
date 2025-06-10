Here is your **PROJECT\_BIBLE.md**—the “source of truth” for a modular, institutional-grade, AI-driven MEV/arbitrage system.
This is the document you’ll **give to ChatGPT before every code prompt** (and keep at the root of your repo forever).
**This will keep every future code output aligned with your requirements—no more “lost in translation.”**

---

```markdown
# PROJECT_BIBLE.md

## MEV-OG NextGen — Institutional-Grade System Blueprint

---

## 1. System Vision

Design and operate a modular, atomic, adversarially-resilient MEV/arbitrage engine that autonomously compounds capital ($5K→$10M+) via DEX/CEX, bridges, rollups, and auctions.  
System must be AI-native, simulation-first, GCP-ready, and bulletproof to exploits, races, and logic drift.

---

## 2. Directory & Module Structure

```

/src/
/core/
agent.py         # Agent/session orchestration, DRP, kill, audit log
state.py         # Atomic capital/session state, rollbackable, auditable
tx.py            # Transaction builder, nonce, replay/kill protection
drp.py           # DRP snapshot/restore/export/import logic
kill.py          # Circuit-breaker, system-wide kill logic
logger.py        # Structured logging, metrics, Prometheus/Sentry
config.py        # Central config loader, .env, secret validation

/adapters/
dex.py           # Modular DEX adapter (Uniswap, 1inch, etc)
cex.py           # Modular CEX adapter (Binance, Coinbase, etc)
bridge.py        # Bridge adapter (L1/L2/L3)
oracle.py        # Price/intent feed adapter
flashloan.py     # Flashloan support
mock.py          # Test/mocking for all adapters

/strategies/
base.py          # AbstractStrategy: interface for run/sim/mutate/snapshot/restore
sandwich.py      # Sandwich attack module
bridge\_race.py   # Bridge delay/race module
cross\_domain.py  # Cross-rollup/L1-L2 arb module
liquidation.py   # Liquidation sniping module
intent\_mev.py    # Intent-based MEV
\# Add all custom strategies here

/test/
test\_core.py
test\_adapters.py
test\_strategies.py
test\_kill.py
test\_drp.py
test\_forked\_sim.py
test\_replay\_attack.py
test\_logging.py

/infra/
Dockerfile
docker-compose.yml
cloudrun.yaml
deploy.sh
healthcheck.sh
setup\_env.sh

/scripts/
simulate\_fork.sh
bootstrap.sh
.env.example
requirements.txt
README.md
PROJECT\_BIBLE.md

````

---

## 3. Security, State, and Mutation Requirements

- **NO global/singleton state:** All capital, session, and trade state must be atomic, rollbackable, and auditable per agent/session.
- **System-wide kill/DRP enforcement:** Every agent/adapter/strategy must check the kill-switch before any capital move or external call. DRP must snapshot/restore/export all critical state.
- **All secrets/config from `.env` or GCP Secret Manager**—never hardcoded.
- **Logging & telemetry:** Every trade, state change, kill, error, and mutation event must emit Prometheus/Sentry/Stackdriver metrics and be written to structured logs with unique IDs and timestamps.
- **Mutation/AI safety:** No code or parameter mutation without explicit audit logging, rollback, and (where appropriate) manual/founder approval.
- **Replay protection:** All trade and state mutations must be idempotent. No double-spends, nonce drift, or partial fill bugs.

---

## 4. Workflow and Deployment Invariants

- **100% containerized, 12-factor, and GCP-ready.**
    - Docker images must be non-root, stateless, and log to stdout.
    - `cloudrun.yaml` and `deploy.sh` for GCP Cloud Run deploy.
    - `.env.example` for onboarding.
- **Onboarding scripts:** All secrets and envs must be validated before first run (`setup_env.sh` or `bootstrap.sh`).
- **Simulation-first:** No mainnet run until all forked/mainnet/chaos tests pass green.
- **CI/CD:** All code linted, type-checked, and tested on every push.  
- **README must include setup, onboarding, test, deploy, and troubleshooting.

---

## 5. Enforcement

- **NO mainnet trades until all simulation, chaos, kill/DRP, and forked-mainnet tests are green.**
- **NO unsandboxed code or parameter mutation.**
- **NO missing secrets/envs on deploy.**
- **NO unlogged trade, state mutation, kill, or DRP event.**
- **Every agent, strategy, and adapter must check the kill-switch before every external or capital-moving action.**

---

## 6. AbstractStrategy Interface

```python
# strategies/base.py
class AbstractStrategy:
    def run(self, state, adapters, config):
        """Main entrypoint for live execution."""
        raise NotImplementedError
    def simulate(self, state, adapters, config):
        """Forked/simulated execution for safety checks."""
        raise NotImplementedError
    def mutate(self, params):
        """Apply new parameters, LLM-driven, always audited."""
        raise NotImplementedError
    def snapshot(self, path):
        """Snapshot session/state for DRP/rollback."""
        raise NotImplementedError
    def restore(self, path):
        """Restore from snapshot."""
        raise NotImplementedError
    def abort(self, reason):
        """Abort and exit cleanly on error/kill."""
        raise NotImplementedError
````

---

## 7. GCP Deployment Checklist

* Docker build passes
* GCP Artifact Registry push/Cloud Run deploy scripts work
* `.env` or GCP Secret Manager provides all secrets
* Healthcheck endpoints are live and report status
* All simulation/chaos/forked tests pass green before mainnet

---

## 8. Core “Must Never Be Violated” Invariants

* All state changes and trades are atomic, auditable, and rollbackable
* Kill/DRP is system-wide, immediate, and cannot be bypassed
* No mutation or AI-driven change is allowed without full audit logging and manual approval where needed
* No unlogged, unaudited error, trade, or state event ever reaches production

---

## 9. Summary

> **This document overrides all other docs, wikis, or code comments.
> Any contradiction is resolved by this PROJECT\_BIBLE.md.
> No code is written, merged, or deployed unless it aligns with these principles.**

---

**— END PROJECT\_BIBLE.md —**

```

---

**Use this as the “first file” in your repo and as the preamble to every LLM codegen prompt.  
