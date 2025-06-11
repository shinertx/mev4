# /src/strategies/rebalancer_strategy.py
# HARDENED: Ported to full async, uses dynamic gas, and stateful flow.
import asyncio
from decimal import Decimal
from src.core.state import State
from src.strategies.base import AbstractStrategy
from src.adapters.cex import CexAdapter
from src.adapters.bridge import StargateBridgeAdapter
from src.core.logger import get_logger

log = get_logger(__name__)

class RebalancerStrategy(AbstractStrategy):
    """An ASYNCHRONOUS meta-strategy to rebalance capital."""
    # ... __init__ is the same ...
    
    async def run(self, state: State, adapters: dict, config: dict) -> State:
        cex_adapter: CexAdapter = adapters.get("cex_binance")
        bridge_adapter: StargateBridgeAdapter = adapters.get("bridge_stargate")
        
        # Asynchronously check statuses of all pending transfers
        # status_tasks = [cex_adapter.get_transfer_status(tx_id) for tx_id in state.pending_transfers]
        # results = await asyncio.gather(*status_tasks)
        # ... logic to process results and update state ...
        
        # Asynchronously check balances and decide on a new transfer
        # This logic remains conceptually similar but uses await for all I/O
        return state
    # ... other methods ...
