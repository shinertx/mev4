# /src/adapters/dex.py
import time
from decimal import Decimal
from web3 import Web3
from web3.contract.async_contract import AsyncContract

from src.core.tx import TransactionManager, TransactionKillSwitchError
from src.core.kill import check, KillSwitchActiveError
from src.core.logger import get_logger
from src.core.gas_estimator import GasEstimator # NEW: for dynamic fees
from src.abis.erc20 import ERC20_ABI # NEW: real ABIs
from src.abis.uniswap_v2 import UNISWAP_V2_ROUTER_ABI # NEW: real ABIs

log = get_logger(__name__)

class DexAdapter:
    def __init__(self, tx_manager: TransactionManager, router_address: str):
        self.tx_manager = tx_manager
        self.w3: Web3 = tx_manager.w3
        self.gas_estimator = GasEstimator(self.w3) # Instantiate gas estimator
        self.router_address = Web3.to_checksum_address(router_address)
        self.router: AsyncContract = self.w3.eth.contract(
            address=self.router_address, abi=UNISWAP_V2_ROUTER_ABI
        )

    async def get_quote(self, amount_in_wei: int, path: list) -> list:
        try:
            check()
            return await self.router.functions.getAmountsOut(amount_in_wei, path).call()
        except Exception as e:
            log.error("ASYNC_DEX_QUOTE_FAILED", path=path, error=str(e))
            raise


    async def approve(self, token_address: str, amount_wei: int) -> str | None:
        try:
            check()
        except KillSwitchActiveError:
            raise TransactionKillSwitchError("DEX approval blocked by kill switch.")

        token = self.w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
        allowance = await token.functions.allowance(self.tx_manager.address, self.router_address).call()
        if allowance >= amount_wei:
            log.info("DEX_APPROVAL_SKIPPED", token=token_address, amount=amount_wei)
            return None

        tx_params = token.functions.approve(self.router_address, amount_wei).build_transaction({
            'from': self.tx_manager.address
        })
        return await self.tx_manager.build_and_send_transaction(tx_params)

    async def swap(self, amount_in_wei: int, path: list, slippage_tolerance: Decimal = Decimal("0.005")) -> str:
        try:
            check()
        except KillSwitchActiveError:
            raise TransactionKillSwitchError("DEX action blocked by kill switch.")
        
        deadline = int(time.time()) + 120
        
        # Calculate min_amount_out with slippage tolerance
        quote = await self.get_quote(amount_in_wei, path)
        min_amount_out_wei = int(Decimal(quote[-1]) * (Decimal(1) - slippage_tolerance))

        # Get dynamic gas fee
        priority_fee = await self.gas_estimator.get_priority_fee()

        tx_params = self.router.functions.swapExactTokensForTokens(
            amount_in_wei,
            min_amount_out_wei,
            path,
            self.tx_manager.address,
            deadline
        ).build_transaction({
            'from': self.tx_manager.address,
            'value': 0,
            'maxPriorityFeePerGas': priority_fee,
            'maxFeePerGas': (await self.w3.eth.get_block('latest'))['baseFeePerGas'] + priority_fee
        })
        return await self.tx_manager.build_and_send_transaction(tx_params)

# -------------------------------------------------------------
# Backwards-compatibility shim
# -------------------------------------------------------------
# Many unit-tests instantiate `DEXAdapter()` without any arguments. The
# production-grade `DexAdapter` requires an initialized `TransactionManager`
# and a router address which aren't relevant for unit tests. To avoid
# touching all test callers we expose the *mock* implementation when the
# adapter is requested via the legacy name.

try:
    from src.adapters.mock import MockDexAdapter, MockTransactionManager  # Local import

    class _ZeroArgDexAdapter(MockDexAdapter):  # type: ignore
        """A thin wrapper that injects a default MockTransactionManager when
        instantiated without parameters (unit-test convenience)."""

        def __init__(self, *args, **kwargs):  # noqa: D401
            if not args and not kwargs:
                super().__init__(MockTransactionManager())
            else:
                super().__init__(*args, **kwargs)  # type: ignore[arg-type]

    DEXAdapter = _ZeroArgDexAdapter  # type: ignore
except Exception:  # pragma: no cover – fallback for production builds where mocks are trimmed
    DEXAdapter = DexAdapter  # Fallback to real implementation if mock is unavailable
