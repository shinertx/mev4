# /src/core/agent.py
# Aligns with PROJECT_BIBLE.md: Section 2 & 3
# - Agent/session orchestration, DRP, kill, audit log.
# - Every agent MUST check the kill-switch before any action.

import time
from decimal import Decimal
from typing import Dict

from src.core.state import State
from src.strategies.base import AbstractStrategy
from src.core.kill import is_kill_switch_active, get_kill_reason
from src.core.config import settings
from src.core.logger import get_logger

log = get_logger(__name__)


class Agent:
    """
    Orchestrates a single, isolated execution of a strategy.
    It is responsible for the main loop, state management, and respecting
    the system-wide kill switch.
    """

    def __init__(self, strategy: AbstractStrategy, initial_capital: Dict[str, Decimal]):
        self.strategy = strategy
        self.state = State(capital_base=initial_capital)
        # In a real system, 'adapters' would be a dictionary of live adapter instances
        # e.g., {"dex": DexAdapter(), "cex": CexAdapter()}
        self.adapters = {} # Mock for now
        self.config = settings.dict() # Pass a snapshot of config

        log.info(
            "AGENT_INITIALIZED",
            session_id=str(self.state.session_id),
            strategy=type(strategy).__name__,
            initial_capital=self.state.capital_base,
        )

    def run_loop(self):
        """
        The main execution loop for the agent.
        It continuously runs the strategy until the kill switch is activated.
        """
        log.info("AGENT_RUN_LOOP_STARTING", session_id=str(self.state.session_id))

        try:
            while not is_kill_switch_active():
                # The core of the system's safety and execution model:
                # 1. Check kill switch
                # 2. Execute one cycle of the strategy
                # 3. The strategy returns the *new* state.
                # 4. The loop continues with this new state.
                
                # The state is replaced with the new state returned by the strategy run.
                # This ensures state transitions are explicit and atomic per cycle.
                self.state = self.strategy.run(self.state, self.adapters, self.config)

                # TODO: Add configurable delay between cycles
                time.sleep(1)

            # If the loop exits, it means the kill switch was activated.
            reason = get_kill_reason()
            log.warning(
                "AGENT_HALTED_BY_KILL_SWITCH",
                session_id=str(self.state.session_id),
                reason=reason,
            )
            self.strategy.abort(reason)

        except Exception as e:
            log.critical(
                "AGENT_CRITICAL_FAILURE",
                session_id=str(self.state.session_id),
                error=str(e),
                exc_info=e,
            )
            self.strategy.abort(f"Critical unhandled exception: {e}")

        finally:
            log.info("AGENT_RUN_LOOP_STOPPED", session_id=str(self.state.session_id))
