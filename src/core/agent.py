# /src/core/agent.py
# Aligns with PROJECT_BIBLE.md: Section 2, 3, 5
# - Agent/session orchestration with AI mutation cycle.
# - Enforces kill-switch before every action via the run loop.

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
    It is responsible for the main loop, state management, respecting
    the system-wide kill switch, and orchestrating strategy mutations.
    """

    def __init__(self, strategy: AbstractStrategy, initial_capital: Dict[str, Decimal]):
        self.strategy = strategy
        self.state = State(capital_base=initial_capital)
        self.adapters = {} # Will be populated by the main script after initialization.
        self.config = settings.dict()

        # Parameters for the AI mutation cycle
        self.mutation_cycle_count = 0
        self.mutation_interval = 10 # Attempt mutation every 10 strategy runs.

        log.info(
            "AGENT_INITIALIZED",
            session_id=str(self.state.session_id),
            strategy=type(strategy).__name__,
            initial_capital=self.state.capital_base,
            mutation_interval=self.mutation_interval,
        )

    def run_loop(self):
        """
        The main execution loop for the agent, now with a mutation cycle.
        It continuously runs the strategy until the kill switch is activated.
        """
        log.info("AGENT_RUN_LOOP_STARTING", session_id=str(self.state.session_id))

        try:
            while not is_kill_switch_active():
                # 1. Run one cycle of the strategy's core logic.
                # The strategy returns the *new* immutable state.
                self.state = self.strategy.run(self.state, self.adapters, self.config)
                self.mutation_cycle_count += 1

                # 2. Periodically attempt to mutate strategy parameters.
                if self.mutation_cycle_count >= self.mutation_interval:
                    log.info("AGENT_ATTEMPTING_MUTATION_CYCLE", strategy=type(self.strategy).__name__)
                    # The mutate method is called here, inside the main safe loop
                    mutated = self.strategy.mutate(self.adapters)
                    if mutated:
                        log.warning("AGENT_CONFIRMED_STRATEGY_MUTATION", strategy_name=self.strategy.strategy_name)
                    self.mutation_cycle_count = 0 # Reset counter
                
                # Configurable delay between cycles
                time.sleep(1)

            # --- Kill Switch Halt ---
            # If the loop exits, it means the kill switch was activated.
            reason = get_kill_reason()
            log.warning(
                "AGENT_HALTED_BY_KILL_SWITCH",
                session_id=str(self.state.session_id),
                reason=reason,
            )
            self.strategy.abort(reason or "Kill switch activated")

        except Exception as e:
            # --- Critical Failure Halt ---
            log.critical(
                "AGENT_CRITICAL_FAILURE",
                session_id=str(self.state.session_id),
                error=str(e),
                exc_info=e,
            )
            self.strategy.abort(f"Critical unhandled exception: {e}")

        finally:
            log.info("AGENT_RUN_LOOP_STOPPED", session_id=str(self.state.session_id))
