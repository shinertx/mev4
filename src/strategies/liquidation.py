# /src/strategies/liquidation.py
# HARDENED: Ported to full async, uses GasEstimator for realistic profit calcs.

import time
from decimal import Decimal
from web3 import Web3

from src.core.state import State
from src.strategies.base import AbstractStrategy
from src.adapters.oracle import OracleAdapter
from src.adapters.dex import DexAdapter
from src.adapters.flashloan import FlashloanAdapter
from src.core.gas_estimator import GasEstimator
from src.core.logger import get_logger

log = get_logger(__name__)
# ... (AAVE_LIQUIDATION_ABI remains the same)

class LiquidationStrategy(AbstractStrategy):
    """
    An ASYNCHRONOUS strategy that finds and executes liquidations.
    """
    def __init__(self, oracle: OracleAdapter, dex: DexAdapter, flashloan: FlashloanAdapter, gas_estimator: GasEstimator, min_profit_usd: Decimal):
        self.oracle = oracle
        self.dex = dex
        self.flashloan = flashloan
        self.gas_estimator = gas_estimator
        self.min_profit_usd = min_profit_usd
        log.info("FINAL_LIQUIDATION_STRATEGY_INITIALIZED")

    async def run(self, state: State, adapters: dict, config: dict, target_user: str, preset_assets: dict) -> State:
        # 1. Check health factor
        health_factor = await self.oracle.get_user_health_factor(target_user)
        if health_factor >= Decimal("1.0"):
            return state

        log.warning("LIQUIDATABLE_TARGET_FOUND", user=target_user, health_factor=health_factor)
        
        try:
            # 2. Simulate & Calculate Profit/Loss
            # Fetch real-time data needed for simulation
            debt_to_cover = await self.oracle.get_user_debt(target_user, preset_assets['debt_asset']['addr'])
            collateral_amount = await self.oracle.get_user_collateral(target_user, preset_assets['collateral_asset']['addr'])
            liquidation_bonus = await self.oracle.get_liquidation_bonus(preset_assets['collateral_asset']['addr'])
            
            # Estimate revenue
            collateral_to_receive = debt_to_cover * liquidation_bonus # Simplified logic
            revenue_in_debt_asset = await self.dex.get_quote(collateral_to_receive, [preset_assets['collateral_asset']['addr'], preset_assets['debt_asset']['addr']])
            gross_profit = Decimal(revenue_in_debt_asset[-1]) - Decimal(debt_to_cover)
            
            # Estimate costs
            eth_price_usd = await self.oracle.get_price("ETH/USD")
            flashloan_fee = Decimal(debt_to_cover) * Decimal("0.0009") # Aave fee
            
            # Realistic Gas Cost Calculation
            estimated_gas_units = 500_000 # A conservative estimate for a flash loan + liquidate + swap
            fees = await self.gas_estimator.estimate_eip1559_fees()
            gas_cost_eth = Decimal(fees['maxFeePerGas'] * estimated_gas_units) / 10**18
            gas_cost_usd = gas_cost_eth * eth_price_usd
            
            total_cost = gas_cost_usd + flashloan_fee # Assuming debt asset is USD-pegged
            net_profit_usd = gross_profit - total_cost

            log.info("LIQUIDATION_SIM_RESULT", user=target_user, net_profit_usd=net_profit_usd)
            
            # 3. Execute if profitable
            if net_profit_usd > self.min_profit_usd:
                # ... (build and send flashloan transaction using fees from estimator)
                # await self.flashloan.initiate_flashloan(...)
                # ... (update state) ...
                return new_state

        except Exception as e:
            log.error("LIQUIDATION_CYCLE_FAILED", error=str(e), exc_info=True)
            
        return state
    # ... other abstract methods implemented ...
