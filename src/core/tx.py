# /src/core/tx.py
# Aligns with PROJECT_BIBLE.md: Section 2, 3, 5, 8
# - Transaction builder, nonce management, replay protection, kill protection.
# - MUST check kill switch before sending.
# - State mutations (nonce) are managed atomically to prevent drift.

import threading
from typing import Dict, Any

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from eth_account.signers.local import LocalAccount

from src.core.config import settings
from src.core.kill import is_kill_switch_active
from src.core.logger import get_logger

log = get_logger(__name__)

# Custom exception for clarity when the kill switch is the reason for failure.
class TransactionKillSwitchError(Exception):
    """Raised when a transaction is blocked by the kill switch."""
    pass

class TransactionManager:
    """
    Manages the lifecycle of transactions for a single account.
    This includes nonce management, gas estimation, signing, and sending.
    It is stateful (manages a nonce) but its state is isolated to one executor.
    An instance of this class should be owned by an Agent.
    """
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.ETH_RPC_URL.get_secret_value()))
        if not self.w3.is_connected():
            log.error("WEBSERVICE_CONNECTION_FAILED", provider_url=settings.ETH_RPC_URL)
            raise ConnectionError("Failed to connect to the Ethereum node.")
        
        # Apply POA middleware for chains like Polygon, BSC, etc.
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        self.account: LocalAccount = Account.from_key(settings.EXECUTOR_PRIVATE_KEY.get_secret_value())
        self.address = self.account.address
        
        # The nonce lock is CRITICAL to prevent race conditions and nonce drift.
        self._nonce_lock = threading.Lock()
        self.nonce = self._get_initial_nonce()

        log.info(
            "TRANSACTION_MANAGER_INITIALIZED",
            executor_address=self.address,
            initial_nonce=self.nonce,
            chain_id=self.w3.eth.chain_id,
        )

    def _get_initial_nonce(self) -> int:
        """Fetches the initial nonce for the account from the blockchain."""
        try:
            return self.w3.eth.get_transaction_count(self.address)
        except Exception as e:
            log.error("FAILED_TO_FETCH_INITIAL_NONCE", address=self.address, error=str(e))
            raise

    def sync_nonce(self):
        """Forces a re-synchronization of the nonce from the chain."""
        with self._nonce_lock:
            old_nonce = self.nonce
            self.nonce = self._get_initial_nonce()
            log.warning(
                "NONCE_SYNCHRONIZED",
                old_nonce=old_nonce,
                new_nonce=self.nonce,
                address=self.address,
            )

    def build_and_send_transaction(self, tx_params: Dict[str, Any]) -> str:
        """
        Builds, signs, and sends a transaction while managing the nonce.
        This is the primary entry point for all on-chain actions.

        Args:
            tx_params: A dictionary of transaction parameters (e.g., 'to', 'data', 'value').

        Returns:
            The transaction hash as a hex string.
            
        Raises:
            TransactionKillSwitchError: If the system kill switch is active.
            ValueError: If transaction parameters are invalid.
            Exception: For various web3/network errors.
        """
        # BIBLE ENFORCEMENT: System-wide kill switch check before any other action.
        if is_kill_switch_active():
            log.critical("TRANSACTION_BLOCKED_BY_KILL_SWITCH", params=tx_params)
            raise TransactionKillSwitchError("Kill switch is active. Halting transaction.")

        with self._nonce_lock:
            try:
                # 1. Prepare transaction details
                full_tx_params = {
                    'from': self.address,
                    'nonce': self.nonce,
                    'chainId': self.w3.eth.chain_id,
                    **tx_params
                }
                
                # Estimate gas if not provided
                if 'gas' not in full_tx_params:
                    full_tx_params['gas'] = self.w3.eth.estimate_gas(full_tx_params)

                # Set gas fees (EIP-1559) if not provided
                if 'maxFeePerGas' not in full_tx_params:
                    full_tx_params['maxFeePerGas'] = self.w3.eth.gas_price * 2
                    full_tx_params['maxPriorityFeePerGas'] = self.w3.eth.max_priority_fee

                # 2. Sign the transaction
                signed_tx = self.w3.eth.account.sign_transaction(
                    full_tx_params,
                    self.account.key
                )
                
                # 3. Send the raw transaction
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                
                # 4. CRITICAL: Increment nonce ONLY after successful broadcast.
                # This is the core of replay/drift protection.
                log.info(
                    "TRANSACTION_BROADCASTED",
                    tx_hash=tx_hash.hex(),
                    nonce=self.nonce,
                    address=self.address,
                )
                self.nonce += 1
                
                return tx_hash.hex()

            except ValueError as e:
                # Often indicates a revert, e.g., "transaction would fail"
                log.error("TRANSACTION_VALIDATION_ERROR", error=str(e), tx_params=tx_params, current_nonce=self.nonce)
                # We do NOT increment the nonce here.
                # A common error is "nonce too low". We can handle it by re-syncing.
                if 'nonce too low' in str(e).lower():
                    log.warning("Nonce too low detected. Re-syncing nonce.")
                    self.sync_nonce()
                raise
            except Exception as e:
                log.error("TRANSACTION_SEND_FAILURE", error=str(e), exc_info=e)
                # Do not increment nonce on failure.
                raise
