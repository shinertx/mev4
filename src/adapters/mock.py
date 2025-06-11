# /src/adapters/mock.py
# Aligns with PROJECT_BIBLE.md: Section 2, 4
# - Provides test/mocking implementations for all adapters.
# - Enables "Simulation-first" development and robust unit/integration testing.
# - Fulfills the requirement for testing before mainnet runs.

from typing import List, Dict
from decimal import Decimal

from src.core.tx import TransactionManager, TransactionKillSwitchError
from src.core.kill import check, KillSwitchActiveError, is_kill_switch_active
from src.core.logger import get_logger

log = get_logger(__name__)

class MockTransactionManager(TransactionManager):
    """
    A mock implementation of TransactionManager for testing purposes.
    It does not send real transactions but simulates the process.
    """
    def __init__(self, from_address: str = "0xMockExecutor"):
        self.address = from_address
        self.nonce = 0
        self.sent_transactions = []
        self._must_fail = False
        log.info("MOCK_TRANSACTION_MANAGER_INITIALIZED", address=self.address)

    def _get_initial_nonce(self) -> int:
        return 0

    def set_next_call_to_fail(self, fail: bool = True):
        """Configure the mock to raise an exception on the next call."""
        self._must_fail = fail

    def build_and_send_transaction(self, tx_params: Dict) -> str:
        """
        Simulates building and sending a transaction.
        Checks the kill switch, logs the transaction, and returns a fake hash.
        """
        try:
            check()
        except KillSwitchActiveError:
            log.warning("MOCK_TX_BLOCKED_BY_KILL_SWITCH", params=tx_params)
            raise TransactionKillSwitchError("Kill switch is active.")

        if self._must_fail:
            self._must_fail = False # Reset after firing
            log.error("MOCK_TX_FORCED_FAILURE", params=tx_params)
            raise ValueError("Forced failure for testing.")
        
        tx_hash = f"0xfake_tx_hash_{self.nonce}"
        full_tx = {"hash": tx_hash, **tx_params}

        log.info("MOCK_TRANSACTION_SENT", tx=full_tx)
        self.sent_transactions.append(full_tx)
        self.nonce += 1
        return tx_hash


class MockDexAdapter:
    """
    A mock implementation of DexAdapter for testing strategies.
    Allows setting predefined quotes for swaps.
    """
    def __init__(self, tx_manager: MockTransactionManager):
        if not isinstance(tx_manager, MockTransactionManager):
            raise TypeError("MockDexAdapter must be initialized with a MockTransactionManager.")
        self.tx_manager = tx_manager
        # Quotes are defined as a dict: "TOKEN_IN_ADDR-TOKEN_OUT_ADDR" -> output_amount
        self.quotes: Dict[str, int] = {}
        # Allowances: owner -> spender -> amount
        self.allowances: Dict[str, Dict[str, int]] = {}
        self.router_address = "0xMockRouter"
        log.info("MOCK_DEX_ADAPTER_INITIALIZED")

    def _check_kill_switch(self):
        try:
            check()
        except KillSwitchActiveError:
            raise TransactionKillSwitchError("DEX action blocked by Mock kill switch.")

    def set_quote(self, path: List[str], amount_out: int):
        self._check_kill_switch()
        """Set a predictable output amount for a given trade path."""
        key = "-".join(path)
        self.quotes[key] = amount_out
        log.info("MOCK_DEX_QUOTE_SET", path=path, amount_out=amount_out)

    def get_quote(self, amount_in_wei: int, path: List[str]) -> List[int]:
        self._check_kill_switch()
        """Returns a pre-configured quote for a swap path."""
        key = "-".join(path)
        if key in self.quotes:
            return [amount_in_wei, self.quotes[key]]
        raise ValueError(f"No mock quote set for path {path}")

    def approve(self, token_address: str, amount_wei: int) -> str | None:
        """Simulates a token approval."""
        self._check_kill_switch()
        
        # Check mock allowance
        owner = self.tx_manager.address
        spender_allowances = self.allowances.setdefault(owner, {})
        if spender_allowances.get(self.router_address, 0) >= amount_wei:
            log.info("MOCK_APPROVAL_NOT_NEEDED", token=token_address)
            return None
            
        # Simulate building and sending the approval tx
        tx_params = {"to": token_address, "data": f"approve({self.router_address}, {amount_wei})"}
        tx_hash = self.tx_manager.build_and_send_transaction(tx_params)
        
        # Update mock allowance state
        spender_allowances[self.router_address] = amount_wei
        log.info("MOCK_APPROVAL_PROCESSED", token=token_address, tx_hash=tx_hash)
        return tx_hash

    def swap(self, amount_in_wei: int, min_amount_out_wei: int, path: List[str], **kwargs) -> str:
        """Simulates a swap, returning a fake transaction hash."""
        self._check_kill_switch()
        
        quote_key = "-".join(path)
        if quote_key not in self.quotes or self.quotes[quote_key] < min_amount_out_wei:
            log.error("MOCK_SWAP_WOULD_FAIL_SLIPPAGE", path=path, min_out=min_amount_out_wei)
            raise ValueError("Mock Slippage error")

        tx_params = {
            "to": self.router_address,
            "data": f"swap(in={amount_in_wei}, path={path})"
        }
        return self.tx_manager.build_and_send_transaction(tx_params)
