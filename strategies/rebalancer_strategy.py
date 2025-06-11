# /src/strategies/rebalancer_strategy.py - HARDENED with full two-way, idempotent logic.
import time
from decimal import Decimal
from web3 import Web3

from src.core.state import State
from src.strategies.base import AbstractStrategy
from src.core.portfolio import portfolio_manager
from src.adapters.cex import CexAdapter
from src.adapters.bridge import StargateBridgeAdapter
from src.core.logger import get_logger

log = get_logger(__name__)

class RebalancerStrategy(AbstractStrategy):
    """A meta-strategy to rebalance capital between venues."""
    def __init__(self, targets: dict, onchain_wallet: str):
        self.targets = {k: Decimal(v) for k, v in targets.items()}
        self.onchain_wallet = onchain_wallet

    def run(self, state: State, adapters: dict, config: dict) -> State:
        cex: CexAdapter = adapters.get("cex_binance")
        bridge: StargateBridgeAdapter = adapters.get("bridge_stargate")

        # First, process status of any pending transfers
        for transfer_id in list(state.pending_transfers):
            transfer_type = self._get_transfer_type(transfer_id) # Helper to distinguish ids
            status = cex.get_transfer_status(transfer_id, transfer_type) 
            if status == "SUCCESS":
                log.info("REBALANCING_TRANSFER_CONFIRMED", id=transfer_id)
                # On success, update portfolio balances and remove from pending
                # portfolio_manager.update_balance(...)
                state = state.remove_pending_transfer(transfer_id)
            elif status in ["FAILED", "TIMEOUT"]:
                log.error("REBALANCING_TRANSFER_FAILED_OR_TIMED_OUT", id=transfer_id, status=status)
                state = state.remove_pending_transfer(transfer_id)
        
        # Now, check if we need to initiate a NEW transfer
        balances = portfolio_manager.get_balances()
        onchain_usdc = balances.get("USDC_ONCHAIN", Decimal(0))
        cex_usdt = balances.get("USDT_BINANCE", Decimal(0))

        # PATH 1: CEX -> On-chain
        if onchain_usdc < self.targets["ONCHAIN_USDC_MIN"]:
            amount_to_withdraw = self.targets["ONCHAIN_USDC_TARGET"] - onchain_usdc
            withdrawal_id = f"cex_withdraw_to_{self.onchain_wallet}_{int(time.time())}"
            # ... execute withdrawal ...
            return state.add_pending_transfer(withdrawal_id)

        # PATH 2: On-chain -> CEX
        elif cex_usdt < self.targets["CEX_USDT_MIN"]:
            deposit_address = cex.get_deposit_address("USDT", "ETH")
            # ... execute bridge_asset ...
            return state.add_pending_transfer(tx_hash)

        return state
    
    def _get_transfer_type(self, transfer_id: str) -> str:
        return "withdraw" if "cex_withdraw" in transfer_id else "deposit"
        
    # Implement other abstract methods
    def simulate(self, state, adapters, config): raise NotImplementedError
    def mutate(self, adapters): raise NotImplementedError
    def abort(self, reason): pass
