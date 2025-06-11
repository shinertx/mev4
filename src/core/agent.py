# /src/core/agent.py
# FINAL VERSION: An async orchestrator for a single, long-running, stateful strategy.
# Manages the full mutation lifecycle: request, check for approval, and apply.

import asyncio
from typing import Dict

from src.core.state import State
from src.strategies.base import AbstractStrategy
from src.core.kill import is_kill_switch_active
from src.core.logger import get_logger

log = get_logger(__name__)

class Agent:
    """
    Orchestrates a long-running, stateful strategy, managing its execution
    and AI-driven parameter mutation lifecycle.
    """
    def __init__(self, strategy: AbstractStrategy, initial_state: State, adapters: dict):
        self.strategy = strategy
        self.state = initial_state
        self.adapters = adapters
        # Get a unique a name for logging and mutation management
        self.strategy_name = getattr(strategy, 'strategy_name', type(strategy).__name__)
        
        # Make intervals configurable or load from strategy metadata
        self.run_interval = 60  # Run strategy logic every 60 seconds
        self.mutation_request_interval = 3600 # Request new params every hour
        self.last_mutation_request_time = 0

    async def run_loop(self):
        """The main async execution loop for a stateful agent."""
        log.info("STATEFUL_AGENT_STARTING_LOOP", strategy=self.strategy_name)

        while not is_kill_switch_active():
            try:
                # 1. Check for and apply any approved mutations first
                mutated = await self.strategy.mutate(self.adapters)
                if mutated:
                    log.warning("AGENT_APPLIED_APPROVED_MUTATION", strategy=self.strategy_name)
            
                # 2. Run the strategy's core logic
                self.state = await self.strategy.run(self.state, self.adapters, {})

                # 3. Periodically request a new mutation from the LLM
                now = asyncio.get_event_loop().time()
                if (now - self.last_mutation_request_time) > self.mutation_request_interval:
                    log.info("AGENT_REQUESTING_NEW_MUTATION", strategy=self.strategy_name)
                    
                    if hasattr(self.strategy, 'get_performance_data'):
                        performance_data = self.strategy.get_performance_data(self.state)
                        await self.adapters['ai_model'].fetch_and_propose_mutation(self.strategy_name, performance_data)
                    else:
                        log.warning("STRATEGY_MISSING_GET_PERFORMANCE_DATA", strategy=self.strategy_name)
                        
                    self.last_mutation_request_time = now
                    
                await asyncio.sleep(self.run_interval)

            except Exception as e:
                log.error("STATEFUL_AGENT_LOOP_ERROR", strategy=self.strategy_name, error=str(e), exc_info=True)
                # Avoid hammering on persistent errors
                await asyncio.sleep(self.run_interval)
        
        log.critical("STATEFUL_AGENT_HALTED_BY_KILL_SWITCH", strategy=self.strategy_name)
        await self.strategy.abort("Kill switch activated")
