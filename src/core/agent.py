# /src/core/agent.py
# FINAL VERSION: An async orchestrator for a single, long-running, stateful strategy.
# Manages the full mutation lifecycle: request, check for approval, and apply.

import asyncio
import json
import redis
from typing import Dict

from src.core.state import State
from src.strategies.base import AbstractStrategy
from src.core.kill import check, KillSwitchActiveError
from src.core.logger import get_logger, set_cycle_counter
from src.core import drp
from src.core.config import settings

log = get_logger(__name__)

class Agent:
    """
    Orchestrates a long-running, stateful strategy, managing its execution
    and AI-driven parameter mutation lifecycle.
    """
    def __init__(self, strategy: AbstractStrategy, initial_state: State, adapters: dict):
        self.strategy = strategy
        self.redis = redis.Redis.from_url(settings.REDIS_URL)
        self.state_lock = asyncio.Lock()
        try:
            saved = self.redis.get(f"state:{initial_state.session_id}")
            if saved:
                self.state = State.from_dict(json.loads(saved))
            else:
                self.state = initial_state
        except Exception as e:
            log.error("STATE_RESTORE_FAILED", error=str(e))
            self.state = initial_state
        self.adapters = adapters
        # Get a unique a name for logging and mutation management
        self.strategy_name = getattr(strategy, 'strategy_name', type(strategy).__name__)
        
        # Make intervals configurable or load from strategy metadata
        self.run_interval = 60  # Run strategy logic every 60 seconds
        self.mutation_request_interval = 3600 # Request new params every hour
        self.last_mutation_request_time = 0

    async def _two_phase_commit(self, trades: list):
        check()
        tx_manager = self.adapters.get("tx_manager")
        if not tx_manager or not trades:
            return
        txs = tx_manager.build_bundle(self.state, trades)
        tx_ids = [tx.get("id") for tx in txs]
        async with self.state_lock:
            self.state = self.state.mark_pending(tx_ids)
        try:
            for tx in txs:
                await tx_manager.send(tx)
            async with self.state_lock:
                self.state = self.state.clear_pending(tx_ids)
        except Exception:
            async with self.state_lock:
                self.state = self.state.clear_pending(tx_ids)
            raise

    async def run_loop(self):
        """The main async execution loop for a stateful agent."""
        log.info("STATEFUL_AGENT_STARTING_LOOP", strategy=self.strategy_name)

        while True:
            try:
                try:
                    check()
                except KillSwitchActiveError:
                    break
                # increment cycle counter and bind to logs
                async with self.state_lock:
                    self.state = self.state.copy(update={"cycle_counter": self.state.cycle_counter + 1})
                    cycle_id = self.state.cycle_counter
                set_cycle_counter(cycle_id)

                # 1. Check for and apply any approved mutations first
                from src.core.mutation import sandboxed_mutate
                mutated = await sandboxed_mutate(self.strategy, self.state, self.adapters)
                if mutated:
                    log.warning("AGENT_APPLIED_APPROVED_MUTATION", strategy=self.strategy_name)

                pre_snapshot = await drp.save_snapshot(self.state)
                try:
                    result = await self.strategy.run(self.state, self.adapters, {})
                    if isinstance(result, tuple):
                        async with self.state_lock:
                            self.state, trades = result
                        await self._two_phase_commit(trades)
                    else:
                        async with self.state_lock:
                            self.state = result
                    async with self.state_lock:
                        await drp.save_snapshot(self.state)
                        self.redis.set(f"state:{self.state.session_id}", json.dumps(self.state.to_dict()))
                except Exception:
                    async with self.state_lock:
                        self.state = await drp.load_snapshot(pre_snapshot)
                    raise

                # 3. Periodically request a new mutation from the LLM
                now = asyncio.get_event_loop().time()
                if (now - self.last_mutation_request_time) > self.mutation_request_interval:
                    log.info("AGENT_REQUESTING_NEW_MUTATION", strategy=self.strategy_name)
                    
                    if hasattr(self.strategy, 'get_performance_data'):
                        async with self.state_lock:
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
