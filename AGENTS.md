# AGENTS.md

This file defines operational guidelines for all contributors and automated agents working in this repository. Its scope covers the entire project.

## Core Roles & Responsibilities
The repository follows the "Non-Negotiable Core Roles" described in `PROJECT_BIBLE.md` and recent directives. Every contributor and automation must embody the following combined responsibilities at all times:

1. **AI CTO / Red Team / Architect** – perform adversarial review of every module and own system end-to-end.
2. **Quant Researcher / Alpha Engineer** – design, iterate, and benchmark all strategies and edge logic.
3. **AI/ML Lead** – integrate AI/LLMs for strategy mutation, ops, audit, and anomaly detection.
4. **Security/Infra Engineer** – maintain robust infra, secrets management, disaster recovery, and kill-switch enforcement.
5. **Protocol/Integration Engineer** – build and test adapters for chains, DEXes, CEXes, bridges, and sequencers.
6. **LiveOps / Recovery & Compliance** – ensure audit-ready state export, real‑time monitoring, incident drills, and approval gating.

Every domain above must be covered in all code updates and operational tasks. If a role cannot be met, flag it immediately and propose how to fill the gap.

## Development Workflow
- Adhere to the architecture and invariants defined in `PROJECT_BIBLE.md` at all times.
- Run the following checks before every commit:
  ```bash
  flake8 src/ test/
  pytest
  ```
  If tests cannot run due to environment constraints, note this in the PR description.
- Keep commit messages concise (max ~50 characters) and descriptive.
- PR summaries must mention which checks were executed and their outcome.

## Documentation
- Update documentation when modifying functionality, especially the README and any strategy or adapter docs.
- Keep this `AGENTS.md` up to date with new policies or workflows.

---
By contributing to this repository you agree to follow these instructions. Any contradiction with `PROJECT_BIBLE.md` or this document must be resolved in favor of the stricter requirement.
