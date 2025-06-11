# /src/strategies/sandwich.py
import asyncio
from decimal import Decimal
from typing import Dict, Any

from src.core.state import State
from src.adapters.dex import DexAdapter
from src.adapters.oracle import OracleAdapter # Fixed
from src.core.logger import get_logger
from src.core.drp import save_snapshot, load_snapshot # Fixed
from src.core.kill import check, KillSwitchActiveError
from src.abis.uniswap_v2 import UNISWAP_V2_ROUTER_ABI

log = get_logger(__name__)
UNISWAP_V2_ROUTER = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"

class SandwichStrategy:
    def __init__(self, dex: DexAdapter, min_profit_usd: Decimal):
        self.dex = dex
        self.w3 = dex.w3
        self.oracle = OracleAdapter() # Fixed
        self.min_profit_usd = min_profit_usd
        self.uniswap_contract = self.w3.eth.contract(abi=UNISWAP_V2_ROUTER_ABI)

    async def process_transaction(self, tx: Dict[str, Any], initial_state: State):
        try:
            check()
        except KillSwitchActiveError:
            log.critical("SANDWICH_ABORTED_BY_KILL_SWITCH", tx_hash=tx.get("hash"))
            return initial_state

        is_target, decoded_data = self.decode_if_target(tx)
        if not is_target:
            return initial_state
        
        current_state = await save_snapshot(initial_state)
        # In a real DRP, the path would be stored more robustly.

        try:
            profit_in_usd = await self.simulate_sandwich(decoded_data)
            if profit_in_usd > self.min_profit_usd:
                log.warning("PROFITABLE_SANDWICH_FOUND", profit_usd=profit_in_usd, victim_tx=tx.get("hash"))
                # ... execute bundle ...
                trade_details = {"type": "SANDWICH", "victim": tx.get("hash"), "profit_usd": float(profit_in_usd)}
                return current_state.record_trade(trade_details)
        except Exception as e:
            log.error("SANDWICH_CYCLE_FAILED_RESTORING_STATE", victim_tx=tx.get("hash"), error=str(e))
            return await load_snapshot(current_state) # Restore pre-trade state
        
        return current_state

    def decode_if_target(self, tx: dict) -> (bool, dict):
        """Decodes Uniswap V2 swap transactions."""
        if str(tx.get('to')).lower() != UNISWAP_V2_ROUTER.lower():
            return False, {}
        try:
            func_obj, func_params = self.uniswap_contract.decode_function_input(tx['input'])
            if 'swap' in func_obj.fn_name:
                return True, func_params
        except ValueError:
            return False, {}
        return False, {}
    
    async def simulate_sandwich(self, victim_tx_data: Dict[str, Any]) -> Decimal:
        # ... hardened simulation logic from previous response ...
        pass
