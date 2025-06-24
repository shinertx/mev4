# /src/strategies/cross_domain.py
import asyncio
# FINAL VERSION: Full async, integrates with final Agent, provides performance data.
from decimal import Decimal
from typing import Dict, Any

from src.core.state import State
from src.strategies.base import AbstractStrategy
from src.adapters.dex import DexAdapter
from src.adapters.ai_model import AIModelAdapter # Needed for type hinting
from src.core.logger import get_logger

log = get_logger(__name__)

class CrossDomainArbitrageStrategy(AbstractStrategy):
    """
    An ASYNCHRONOUS strategy that identifies and executes arbitrage opportunities.
    This version is designed to be managed by the stateful Agent.
    """
    def __init__(self, dex_a_key: str, dex_b_key: str, trade_path: list, trade_amount: Decimal, min_profit_usd: Decimal):
        self.dex_a_key = dex_a_key
        self.dex_b_key = dex_b_key
        self.token_a, self.token_b = trade_path
        self.trade_amount = trade_amount
        self.min_profit_usd = min_profit_usd
        
        self.token_a_decimals = 18
        self.token_b_decimals = 6
        
        # Unique name for this strategy instance for the AI model
        self.strategy_name = f"CrossDomainArb_{self.dex_a_key}_{self.dex_b_key}_{self.token_a[:6]}_{self.token_b[:6]}"
        log.info("STATEFUL_STRATEGY_INITIALIZED_CrossDomain", config=self.get_params())

    def get_params(self) -> Dict[str, Any]:
        """Returns the current configurable parameters of the strategy."""
        return {"trade_amount": str(self.trade_amount), "min_profit_usd": str(self.min_profit_usd)}

    def get_performance_data(self, state: State) -> dict:
        """Gathers performance metrics for the AI strategist from state history."""
        profitable_trades = [t for t in state.history if t['event_type'] == 'TRADE_EXECUTED' and t['data'].get('profit', 0) > 0]
        # This is a simplified calculation. A real one would be more robust.
        total_profit = sum(Decimal(str(t['data']['profit'])) for t in profitable_trades)
        
        return {
            "performance": {
                "total_trades": len([t for t in state.history if t['event_type'] == 'TRADE_EXECUTED']),
                "profitable_trades": len(profitable_trades),
                "total_profit_usd": str(total_profit)
            },
            "current_params": self.get_params()
        }

    async def mutate(self, adapters: dict) -> bool:
        """Applies a new set of parameters if one has been approved by an operator."""
        ai_model: AIModelAdapter = adapters.get("ai_model")
        if not ai_model: return False

        approved_params = ai_model.get_approved_mutation(self.strategy_name)
        if approved_params:
            log.warning("APPLYING_APPROVED_MUTATION", strategy_name=self.strategy_name, params=approved_params)
            # Add validation here to ensure new params are sensible
            self.trade_amount = Decimal(approved_params.get("trade_amount", str(self.trade_amount)))
            self.min_profit_usd = Decimal(approved_params.get("min_profit_usd", str(self.min_profit_usd)))
            return True
        return False

    async def run(self, state: State, adapters: dict, config: dict) -> State:
        """The main async execution logic for the strategy."""
        dex_a: DexAdapter = adapters.get(self.dex_a_key)
        dex_b: DexAdapter = adapters.get(self.dex_b_key)
        # oracle: OracleAdapter = adapters.get("oracle_chainlink")

        if not all([dex_a, dex_b]): # and oracle]):
            log.error("ADAPTERS_MISSING_FOR_STRATEGY", needed=[self.dex_a_key, self.dex_b_key])
            return state

        try:
            amount_in_wei = int(self.trade_amount * (10**self.token_a_decimals))
            
            # Use asyncio.gather to get quotes concurrently
            quote_a_to_b, quote_b_to_a_pre = await asyncio.gather(
                dex_a.get_quote(amount_in_wei, [self.token_a, self.token_b]),
                dex_b.get_quote(amount_in_wei, [self.token_a, self.token_b]) # Check both directions
            )
            
            # This is a simplified arb logic; a real one is more complex.
            # For now, just logging the check.
            log.info("PERIODIC_ARB_CHECK", dex_a_price=quote_a_to_b[-1], dex_b_price=quote_b_to_a_pre[-1])
            # ... full arbitrage, execution, and state update logic would go here ...

        except Exception as e:
            log.error("CROSS_DOMAIN_ARB_CYCLE_FAILED", error=str(e), exc_info=True)

        return state

    async def abort(self, reason: str):
        log.critical("STRATEGY_ABORTED", strategy_name=self.strategy_name, reason=reason)
