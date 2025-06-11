# /src/adapters/oracle.py
from decimal import Decimal
import asyncio
import aiohttp
from web3 import Web3

from src.core.resilient_rpc import ResilientWeb3Provider # Use async provider
from src.core.logger import get_logger
from src.core.kill import check, KillSwitchActiveError

log = get_logger(__name__)

class OracleAdapter:
    def __init__(self):
        self.provider = ResilientWeb3Provider() # It's now async
        self.w3 = self.provider.get_primary_provider()
        self.http = aiohttp.ClientSession()

    async def initialize(self):
        try:
            check()
        except KillSwitchActiveError:
            raise
        await self.provider.initialize()
        log.info("ASYNC_ORACLE_ADAPTER_INITIALIZED")

    async def _coingecko_price(self, symbol: str) -> Decimal:
        check()
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
        async with self.http.get(url) as resp:
            data = await resp.json()
            return Decimal(str(data[symbol]["usd"]))

    async def _chainlink_price(self, pair: str) -> Decimal:
        check()
        # Placeholder for on-chain Chainlink call
        price_wei = await self.provider.call_consensus("0x0000000000000000000000000000000000000000", [], "latestRoundData")
        return Decimal(price_wei) / Decimal(1e8)

    async def _uniswap_twap(self, pair: str) -> Decimal:
        check()
        # Placeholder for on-chain TWAP
        price_wei = await self.provider.call_consensus("0x0000000000000000000000000000000000000000", [], "consult", pair)
        return Decimal(price_wei) / Decimal(1e18)

    async def get_price(self, pair: str) -> Decimal:
        check()
        coingecko, chainlink, twap = await asyncio.gather(
            self._coingecko_price(pair),
            self._chainlink_price(pair),
            self._uniswap_twap(pair)
        )
        prices = sorted([coingecko, chainlink, twap])
        median_price = prices[1]
        if abs(median_price - twap) / twap > Decimal("0.01"):
            raise ValueError("Median price deviates >1% from on-chain TWAP")
        return median_price
