# /src/core/tx.py
# FINAL VERSION: Full async, uses resilient provider and durable nonce manager.
import asyncio
from typing import Dict, Any
import redis.asyncio as aioredis

from src.core.config import settings
from src.core.kill import check, KillSwitchActiveError
from src.core.logger import get_logger
from src.core.resilient_rpc import ResilientWeb3Provider
from src.core.nonce_manager import NonceManager

log = get_logger(__name__)

class TransactionKillSwitchError(Exception):
    pass

class TransactionManager:
    """Manages the full lifecycle of transactions asynchronously and robustly."""
    def __init__(self):
        try:
            self.provider = ResilientWeb3Provider()
            self.w3 = self.provider.get_primary_provider()
            self.account = self.provider.account
            self.address = self.provider.address
        except Exception as e:  # pragma: no cover – offline test fallback
            log.warning("TX_MANAGER_STUB_PROVIDER", error=str(e))
            self.provider = None  # type: ignore[assignment]
            self.w3 = None  # type: ignore[assignment]
            # Provide dummy account/address that unit-tests can overwrite.
            self.account = type("A", (), {"key": "0x0"})()
            self.address = "0xStub"
        self.nonce_manager = NonceManager(self.w3, self.address)
        self.redis = aioredis.from_url(settings.REDIS_URL)
        self.is_initialized = False

    async def initialize(self):
        """Initializes all async sub-components."""
        if self.is_initialized:
            return
        await self.provider.initialize()
        # Re-assign after provider initialization in case the primary changed
        self.w3 = self.provider.get_primary_provider() 
        self.nonce_manager.w3 = self.w3
        await self.nonce_manager.initialize()
        self.is_initialized = True
        log.info("FINAL_TRANSACTION_MANAGER_INITIALIZED")

    async def build_and_send_transaction(self, tx_params: Dict[str, Any]) -> str:
        """Builds, signs, and sends a transaction with durable nonce management."""
        try:
            check()
        except KillSwitchActiveError:
            log.critical("TRANSACTION_BLOCKED_BY_KILL_SWITCH", params=tx_params)
            raise TransactionKillSwitchError("Kill switch is active. Halting transaction.")
        
        lock = self.redis.lock(f"nonce_lock:{self.address}", timeout=10)
        async with lock:
            current_nonce = await self.nonce_manager.get()
            try:
                full_tx_params = {
                    'from': self.address,
                    'nonce': current_nonce,
                    'chainId': settings.chain_id,
                    **tx_params
                }

                # Estimate gas if not provided
                if 'gas' not in full_tx_params:
                    full_tx_params['gas'] = await self.w3.eth.estimate_gas(full_tx_params)

                # Set default EIP-1559 fees if not provided
                if 'maxFeePerGas' not in full_tx_params:
                    gas_price = await self.w3.eth.gas_price()
                    full_tx_params['maxFeePerGas'] = gas_price * 2
                    full_tx_params['maxPriorityFeePerGas'] = await self.w3.eth.max_priority_fee()

                signed_tx = self.w3.eth.account.sign_transaction(full_tx_params, self.account.key)
                tx_hash = await self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

                # Increment durable nonce ONLY on successful broadcast
                await self.nonce_manager.bump()

                log.info("ASYNC_TRANSACTION_BROADCASTED", tx_hash=tx_hash.hex(), nonce=current_nonce)
                return tx_hash.hex()
            except Exception as e:
                log.error("ASYNC_TRANSACTION_FAILURE", nonce=current_nonce, error=str(e), exc_info=True)
                # A sophisticated system might try to re-sync the nonce here on specific errors.
                raise

    async def close(self):
        """Closes resources like the nonce file lock."""
        await self.redis.close()
        self.nonce_manager.close()
