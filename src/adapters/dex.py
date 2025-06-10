# /src/adapters/dex.py
# Aligns with PROJECT_BIBLE.md: Section 2 & 3
# - Modular DEX adapter (starting with Uniswap V2).
# - Must check kill-switch before any capital move.
# - Uses the core TransactionManager for all on-chain actions.

import time
from decimal import Decimal
from typing import List

from web3 import Web3
from web3.contract import Contract

from src.core.tx import TransactionManager, TransactionKillSwitchError
from src.core.kill import is_kill_switch_active
from src.core.logger import get_logger

log = get_logger(__name__)

# Standard ABIs for convenience. In a larger system, this might come from a dedicated ABI library.
ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "remaining", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "success", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"}
]
UNISWAP_V2_ROUTER_ABI = [
    {"inputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}], "name": "getAmountsOut", "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}, {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}, {"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "deadline", "type": "uint256"}], "name": "swapExactTokensForTokens", "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}], "stateMutability": "nonpayable", "type": "function"}
]

class DexAdapter:
    """
    A modular adapter for interacting with a Uniswap V2-like DEX.
    This adapter is stateless and relies on the TransactionManager for execution.
    """

    def __init__(self, tx_manager: TransactionManager, router_address: str):
        self.tx_manager = tx_manager
        self.w3: Web3 = tx_manager.w3
        self.router_address = Web3.to_checksum_address(router_address)
        self.router: Contract = self.w3.eth.contract(address=self.router_address, abi=UNISWAP_V2_ROUTER_ABI)
        log.info(
            "DEX_ADAPTER_INITIALIZED",
            dex_type="Uniswap_V2",
            router_address=self.router_address
        )

    def _check_kill_switch(self):
        """BIBLE ENFORCEMENT: Internal safety check."""
        if is_kill_switch_active():
            raise TransactionKillSwitchError("DEX action blocked by kill switch.")

    def get_quote(self, amount_in_wei: int, path: List[str]) -> List[int]:
        """
        Gets a quote for a swap from the DEX router (read-only call).
        
        Args:
            amount_in_wei: The amount of the input token in its smallest unit.
            path: A list of token addresses [token_in, token_out, ...].
        
        Returns:
            A list of amounts, where the last element is the output amount.
        """
        try:
            return self.router.functions.getAmountsOut(amount_in_wei, path).call()
        except Exception as e:
            log.error("DEX_QUOTE_FAILED", path=path, amount_in=amount_in_wei, error=str(e))
            raise

    def approve(self, token_address: str, amount_wei: int) -> str | None:
        """
        Approves the DEX router to spend a token.
        Checks allowance first to avoid unnecessary transactions.
        """
        self._check_kill_switch()
        token_address = Web3.to_checksum_address(token_address)
        token_contract = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)
        
        current_allowance = token_contract.functions.allowance(
            self.tx_manager.address, self.router_address
        ).call()
        
        if current_allowance >= amount_wei:
            log.info(
                "DEX_APPROVAL_NOT_NEEDED",
                token=token_address,
                current_allowance=current_allowance,
                required_amount=amount_wei
            )
            return None

        log.warning(
            "DEX_APPROVAL_REQUIRED",
            token=token_address,
            spender=self.router_address,
            amount=amount_wei
        )
        tx_data = token_contract.functions.approve(self.router_address, amount_wei).build_transaction({
            'from': self.tx_manager.address,
            'nonce': self.tx_manager.nonce, # Read nonce for building, manager will lock and use final
        })
        
        return self.tx_manager.build_and_send_transaction(tx_data)

    def swap(self, amount_in_wei: int, min_amount_out_wei: int, path: List[str], deadline_seconds: int = 120) -> str:
        """
        Executes a token swap on the DEX.
        
        Args:
            amount_in_wei: The exact amount of input tokens.
            min_amount_out_wei: The minimum amount of output tokens (slippage protection).
            path: The trade path [token_in, token_out].
            deadline_seconds: How long until the transaction expires.

        Returns:
            The transaction hash as a hex string.
        """
        self._check_kill_switch()

        log.info("DEX_SWAP_INITIATED", path=path, amount_in=amount_in_wei, min_amount_out=min_amount_out_wei)

        deadline = int(time.time()) + deadline_seconds
        tx_params = self.router.functions.swapExactTokensForTokens(
            amount_in_wei,
            min_amount_out_wei,
            path,
            self.tx_manager.address, # Send the swapped tokens back to our executor
            deadline
        ).build_transaction({
            'from': self.tx_manager.address,
            'value': 0, # Assuming token-to-token swap, not ETH-to-token
            'nonce': self.tx_manager.nonce # Read for building, manager handles final
        })
        
        # If the input token is WETH and we are swapping ETH, 'value' should be set.
        # This implementation assumes pre-wrapped ETH or token-to-token.

        return self.tx_manager.build_and_send_transaction(tx_params)
