# /src/strategies/base.py
# Aligns with PROJECT_BIBLE.md: Section 6
# - Defines the AbstractStrategy interface.
# - Enforces a consistent structure for all strategies.

from src.core.state import State

class AbstractStrategy:
    """
    This is the interface every MEV/arbitrage strategy must implement.
    It ensures that all strategies can be orchestrated, simulated, snapshotted,
    and safely managed by the core system.
    """
    def run(self, state: State, adapters: dict, config: dict) -> State:
        """
        Main entrypoint for live execution.
        Must check kill switch via adapters before any action.
        Should return the new, updated State object.
        """
        raise NotImplementedError

    def simulate(self, state: State, adapters: dict, config: dict):
        """Forked/simulated execution for safety checks."""
        raise NotImplementedError

    def mutate(self, params: dict):
        """Apply new parameters, LLM-driven, always audited."""
        raise NotImplementedError

    def snapshot(self, path: str):
        """Snapshot session/state for DRP/rollback."""
        raise NotImplementedError

    def restore(self, path: str):
        """Restore from snapshot."""
        raise NotImplementedError

    def abort(self, reason: str):
        """Abort and exit cleanly on error/kill."""
        raise NotImplementedError
