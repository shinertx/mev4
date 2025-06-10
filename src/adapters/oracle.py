# /src/adapters/oracle.py
# Aligns with PROJECT_BIBLE.md: Section 2
# - Price/intent feed adapter.
# - Implemented as a lending protocol oracle for Aave V3.
# - Provides read-only data for strategies like liquidation sniping.

from decimal import Decimal
from web3 import Web3

from src.core.config import settings
from src.core.logger import get_logger

log = get_logger(__name__)

# Minimal ABI for Aave V3 Pool to get user data
AAVE_V3_POOL_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "getUserAccountData",
        "outputs": [
            {"internalType": "uint256", "name": "totalCollateralBase", "type": "uint256"},
            {"internalType": "uint256", "name": "totalDebtBase", "type": "uint256"},
            {"internalType": "uint256", "name": "availableBorrowsBase", "type": "uint256"},
            {"internalType": "uint256", "name": "currentLiquidationThreshold", "type": "uint256"},
            {"internalType": "uint256", "name": "ltv", "type": "uint256"},
            {"internalType": "uint256", "name": "healthFactor", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    }
]

class LendingProtocolOracle:
    """
    An adapter for reading user account data from a lending protocol.
    This implementation targets the Aave V3 Pool contract.
    It is used to identify accounts that are eligible for liquidation.
    """
    def __init__(self, pool_address: str):
        self.w3 = Web3(Web3.HTTPProvider(settings.ETH_RPC_URL.get_secret_value()))
        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to Ethereum node for Oracle.")

        self.pool_address = Web3.to_checksum_address(pool_address)
        self.pool_contract = self.w3.eth.contract(address=self.pool_address, abi=AAVE_V3_POOL_ABI)
        log.info(
            "LENDING_ORACLE_INITIALIZED",
            protocol="Aave_V3",
            pool_address=self.pool_address
        )

    def get_user_health_factor(self, user_address: str) -> Decimal:
        """
        Fetches the health factor for a given user address from the Aave V3 Pool.
        A health factor below 1.0 means the user is liquidatable.

        Args:
            user_address: The Ethereum address of the user's position to check.

        Returns:
            The user's health factor as a Decimal object.
        """
        user_address = Web3.to_checksum_address(user_address)
        log.debug("FETCHING_HEALTH_FACTOR", user=user_address, oracle=self.pool_address)
        
        try:
            # getUserAccountData returns a tuple of values. The healthFactor is the 6th element (index 5).
            user_data = self.pool_contract.functions.getUserAccountData(user_address).call()
            raw_health_factor = user_data[5]

            # The health factor is returned as a uint with 18 decimals. We convert it.
            health_factor = Decimal(raw_health_factor) / Decimal(10**18)
            
            return health_factor
        except Exception as e:
            # This could fail if the user has no position, or due to a network error.
            log.error(
                "FAILED_TO_FETCH_HEALTH_FACTOR",
                user=user_address,
                error=str(e)
            )
            # Return a "safe" health factor on error to prevent accidental liquidation attempts.
            return Decimal("Infinity")
