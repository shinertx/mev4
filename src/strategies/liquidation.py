# /src/strategies/liquidation.py
# Aligns with PROJECT_BIBLE.md: Section 2, 6
# - Implements a liquidation sniping strategy.
# - Orchestrates Oracle, Flashloan, and DEX adapters.

from decimal import Decimal, getcontext
from typing import Dict, Any

from web3 import Web3

from src.core.state import State
from src.strategies.base import AbstractStrategy
from src.adapters.oracle import LendingProtocolOracle
from src.adapters.dex import DexAdapter
from src.adapters.flashloan import FlashloanAdapter
from src.core.logger import get_logger

getcontext().prec = 50
log = get_logger(__name__)

# ABI fragment for Aave Pool's liquidationCall
AAVE_LIQUIDATION_ABI = {"inputs":[{"internalType":"address","name":"collateralAsset","type":"address"},{"internalType":"address","name":"debtAsset","type":"address"},{"internalType":"address","name":"user","type":"address"},{"internalType":"uint256","name":"debtToCover","type":"uint256"},{"internalType":"bool","name":"receiveAToken","type":"bool"}],"name":"liquidationCall","outputs":[],"stateMutability":"nonpayable","type":"function"}


class LiquidationStrategy(AbstractStrategy):
    """
    Finds and executes liquidations on a lending protocol like Aave.
    This strategy monitors a user's health factor and, if it drops below 1.0,
    initiates a flash-loan-powered liquidation to seize their collateral at a discount.
    """
    def __init__(self, oracle_key: str, dex_key: str, flashloan_key: str, min_profit_usd: Decimal):
        self.oracle_key = oracle_key
        self.dex_key = dex_key
        self.flashloan_key = flashloan_key
        self.min_profit_usd = min_profit_usd
        log.info("STRATEGY_INITIALIZED_Liquidation", config=self.__dict__)

    def run(self, state: State, adapters: dict, config: dict, target_user: str, preset_assets: Dict[str, Any]) -> State:
        """
        Main entrypoint for a liquidation attempt on a single target user.

        Args:
            state: The current system state.
            adapters: Dictionary of available adapters.
            config: System-wide configuration.
            target_user: The address of the user to check for liquidation.
            preset_assets: Defines the specific liquidation path.
                Example: {
                    "debt_asset": {"addr": "0x...", "decimals": 6},
                    "collateral_asset": {"addr": "0x...", "decimals": 18},
                    "aave_pool": "0x..."
                }
        """
        oracle: LendingProtocolOracle = adapters.get(self.oracle_key)
        dex: DexAdapter = adapters.get(self.dex_key)
        flashloan: FlashloanAdapter = adapters.get(self.flashloan_key)

        if not all([oracle, dex, flashloan]):
            log.error("ADAPTERS_MISSING_FOR_LIQUIDATION", needed=[self.oracle_key, self.dex_key, self.flashloan_key])
            return state

        # 1. Check if Target is Liquidatable
        health_factor = oracle.get_user_health_factor(target_user)
        log.debug("LIQUIDATION_CHECK", user=target_user, health_factor=health_factor)

        if health_factor >= Decimal("1.0"):
            return state # Not liquidatable, do nothing.
            
        log.warning("LIQUIDATABLE_TARGET_FOUND", user=target_user, health_factor=health_factor)

        try:
            # 2. Simulation Phase
            # In a real system, you'd fetch the user's total debt, collateral, liquidation bonus, etc.
            # We'll use assumed values for this demonstration.
            debt_to_cover = Decimal("1000") # Amount of debt we will repay (e.g., 1000 USDC)
            liquidation_bonus = Decimal("1.05") # Assume a 5% bonus

            debt_asset = preset_assets["debt_asset"]
            collateral_asset = preset_assets["collateral_asset"]

            debt_to_cover_wei = int(debt_to_cover * (10**debt_asset["decimals"]))
            collateral_to_receive_approx = debt_to_cover * liquidation_bonus
            # Note: A real implementation needs to account for token prices. Assuming 1:1 price for simplicity.
            collateral_to_receive_wei = int(collateral_to_receive_approx * (10**collateral_asset["decimals"]))

            # SIMULATE: Selling the received collateral on the DEX
            backrun_quote = dex.get_quote(collateral_to_receive_wei, [collateral_asset["addr"], debt_asset["addr"]])
            backrun_amount_out_wei = backrun_quote[-1]

            # 3. Profit Calculation
            gross_profit_wei = backrun_amount_out_wei - debt_to_cover_wei
            flashloan_fee_wei = int(Decimal(debt_to_cover_wei) * Decimal("0.0009")) # Aave fee
            net_profit_wei = gross_profit_wei - flashloan_fee_wei
            net_profit_usd = Decimal(net_profit_wei) / (10**debt_asset["decimals"])

            log.info("LIQUIDATION_SIM_RESULT", user=target_user, net_profit_usd=net_profit_usd)

            # 4. Execution Phase
            if net_profit_usd > self.min_profit_usd:
                log.critical("PROFITABLE_LIQUIDATION_FOUND", user=target_user, net_profit=net_profit_usd)
                
                # Encode the atomic sequence of actions for the flash loan
                # ACTION 1: The liquidation call itself
                liquidation_calldata = Web3().eth.contract(abi=[AAVE_LIQUIDATION_ABI]).encodeABI(
                    fn_name="liquidationCall",
                    args=[collateral_asset["addr"], debt_asset["addr"], target_user, debt_to_cover_wei, False]
                )
                
                # ACTION 2: The DEX swap to sell the collateral
                swap_calldata = dex.router.encodeABI(
                    fn_name="swapExactTokensForTokens",
                    args=[collateral_to_receive_wei, 0, [collateral_asset["addr"], debt_asset["addr"]], flashloan.receiver_address, int(time.time()) + 120]
                )
                  
                # ASSUMPTION: The FlashloanAdapter can encode a chain of calls.
                encoded_actions = flashloan.encode_action_chain(
                    targets=[preset_assets["aave_pool"], dex.router_address],
                    calldatas=[liquidation_calldata, swap_calldata]
                )

                # Initiate the flash loan with the encoded atomic bundle
                tx_hash = flashloan.initiate_flashloan(
                    loan_assets=[debt_asset["addr"]],
                    loan_amounts=[debt_to_cover_wei],
                    encoded_action_calldata=encoded_actions
                )

                # 5. Update State
                trade_details = {"type": "LIQUIDATION", "target_user": target_user, "profit_usd": float(net_profit_usd), "tx_hash": tx_hash}
                new_state = state.record_trade(trade_details).update_capital({debt_asset["addr"]: net_profit_usd})
                return new_state

        except Exception as e:
            log.error("LIQUIDATION_CYCLE_FAILED", error=str(e), exc_info=True)
            
        return state

    def abort(self, reason: str):
        log.critical("STRATEGY_ABORTED_Liquidation", reason=reason)
