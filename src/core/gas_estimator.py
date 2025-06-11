# /src/core/gas_estimator.py
# NEW MODULE: Centralized, resilient gas price estimation.
# Fixes: Naive gas modeling in all strategies.

from decimal import Decimal
from web3 import Web3

from src.core.resilient_rpc import ResilientWeb3Provider # Use our async, multi-node provider
from src.core.logger import get_logger
from src.core.decorators import retriable_network_call

log = get_logger(__name__)

class GasEstimator:
    """
    Provides reliable, dynamic gas fee estimates using the resilient provider.
    """
    def __init__(self, provider: ResilientWeb3Provider):
        self.provider = provider
        self.w3 = provider.get_primary_provider()
        log.info("GAS_ESTIMATOR_INITIALIZED")

    @retriable_network_call
    async def get_base_fee(self) -> int:
        """Fetches the latest block's base fee."""
        latest_block = await self.w3.eth.get_block('latest')
        return latest_block['baseFeePerGas']

    @retriable_network_call
    async def get_priority_fee(self) -> int:
        """
        Estimates the priority fee by checking the last few blocks.
        A production system might use a more sophisticated percentile approach.
        """
        try:
            # eth_maxPriorityFeePerGas is the modern standard
            return await self.w3.eth.max_priority_fee
        except Exception:
            # Fallback for nodes that don't support it
            log.warning("MAX_PRIORITY_FEE_RPC_UNSUPPORTED_FALLING_BACK")
            return int(Decimal("1.5") * 10**9) # Fallback to 1.5 gwei

    async def estimate_eip1559_fees(self, priority_multiplier: Decimal = Decimal("1.2")) -> dict:
        """
        Provides a complete EIP-1559 fee structure.

        Args:
            priority_multiplier: A buffer to increase likelihood of inclusion.

        Returns:
            A dictionary with 'maxFeePerGas' and 'maxPriorityFeePerGas'.
        """
        base_fee = await self.get_base_fee()
        priority_fee = await self.get_priority_fee()
        
        # Add a buffer to the priority fee to be competitive
        final_priority_fee = int(Decimal(priority_fee) * priority_multiplier)
        
        # Max fee is the base fee plus our priority fee tip
        max_fee = base_fee + final_priority_fee
        
        return {
            "maxPriorityFeePerGas": final_priority_fee,
            "maxFeePerGas": max_fee
        }
