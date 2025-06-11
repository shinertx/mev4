# /src/core/tx.py
import asyncio
from typing import Dict, Any

from src.core.config import settings
from src.core.kill import is_kill_switch_active
from src.core.logger import get_logger
from src.core.resilient_rpc import ResilientWeb3Provider # Using our resilient provider
from src.core.nonce_manager import NonceManager # Using our durable nonce manager

log = get_logger(__name__)

class TransactionKillSwitchError(Exception): pass

class TransactionManager:
    def __init__(self):
        self.provider = ResilientWeb3Provider()
        self.w3 = self.provider.get_primary_provider()
        self.account = self.provider.account
        self.address = self.provider.address
        self.nonce_manager = NonceManager(self.w3, self.address)

    async def initialize(self):
        """Initializes the manager and its sub-components."""
        await self.provider.initialize()
        await self.nonce_manager.initialize()
        log.info("ASYNC_HARDENED_TRANSACTION_MANAGER_INITIALIZED")

    async def build_and_send_transaction(self, tx_params: Dict[str, Any]) -> str:
        if is_kill_switch_active():
            raise TransactionKillSwitchError("Kill switch is active.")
            
        current_nonce = await self.nonce_manager.get_nonce()
        try:
            full_tx_params = {
                'from': self.address,
                'nonce': current_nonce,
                'chainId': self.provider.chain_id,
                **tx_params
            }
            
            if 'gas' not in full_tx_params:
                full_tx_params['gas'] = await self.w3.eth.estimate_gas(full_tx_params)

            if 'maxFeePerGas' not in full_tx_params:
                gas_price = await self.w3.eth.gas_price
                full_tx_params['maxFeePerGas'] = gas_price * 2
                full_tx_params['maxPriorityFeePerGas'] = await self.w3.eth.max_priority_fee

            signed_tx = self.w3.eth.account.sign_transaction(full_tx_params, self.account.key)
            tx_hash = await self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            await self.nonce_manager.increment() # Increment durable nonce ONLY on success
            
            log.info("ASYNC_TRANSACTION_BROADCASTED", tx_hash=tx_hash.hex(), nonce=current_nonce)
            return tx_hash.hex()
        except Exception as e:
            log.error("ASYNC_TRANSACTION_FAILURE", nonce=current_nonce, error=str(e), exc_info=True)
            raise
            
    def close(self):
        self.nonce_manager.close()
