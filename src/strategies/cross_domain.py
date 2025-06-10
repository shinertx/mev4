# /src/strategies/cross_domain.py
# Aligns with PROJECT_BIBLE.md: Section 2, 6
# - Implements AbstractStrategy for cross-DEX arbitrage.
# - Includes AI-native `mutate` method for dynamic parameter updates.

from decimal import Decimal, getcontext
from typing import Dict, Any

from src.core.state import State
from src.strategies.base import AbstractStrategy
from src.adapters.dex import DexAdapter
from src.adapters.ai_model import AIModelAdapter
from src.core.logger import get_logger

# Set precision for Decimal calculations
getcontext().prec = 50 

log = get_logger(__name__)

class CrossDomainArbitrageStrategy(AbstractStrategy):
    """
    A strategy that identifies and executes arbitrage opportunities between two DEXs on the same chain.
    Example: Buy WETH for USDC on Uniswap, sell WETH for USDC on Sushiswap for a profit.
    This version is AI-native and can have its parameters mutated.
    """
    def __init__(self, dex_a_key: str, dex_b_key: str, trade_path: list, trade_amount: Decimal, min_profit_usd: Decimal):
        """
        Initializes the strategy with its specific configuration.
        
        Args:
            dex_a_key: The key for the first DEX in the adapters dictionary (e.g., "uniswap").
            dex_b_key: The key for the second DEX (e.g., "sushiswap").
            trade_path: The token addresses for the arb [TOKEN_A, TOKEN_B].
            trade_amount: The amount of TOKEN_A to use for the arbitrage.
            min_profit_usd: The minimum profit in USD to execute the trade.
        """
        self.dex_a_key = dex_a_key
        self.dex_b_key = dex_b_key
        self.token_a, self.token_b = trade_path
        self.trade_amount = trade_amount
        self.min_profit_usd = min_profit_usd
        
        # In a real scenario, these would be fetched dynamically from the token contracts.
        self.token_a_decimals = 18 # e.g., WETH
        self.token_b_decimals = 6  # e.g., USDC
        
        # Unique name for this strategy instance for the AI model
        self.strategy_name = f"CrossDomainArb_{self.dex_a_key}_{self.dex_b_key}_{self.token_a[:6]}_{self.token_b[:6]}"
        
        log.info("STRATEGY_INITIALIZED_CrossDomainArbitrage", config=self.get_params())

    def get_params(self) -> Dict[str, Any]:
        """Returns the current configurable parameters of the strategy."""
        return {
            "trade_amount": str(self.trade_amount),
            "min_profit_usd": str(self.min_profit_usd)
        }

    def run(self, state: State, adapters: dict, config: dict) -> State:
        """
        The main execution loop for the strategy.
        Checks for arb opportunities and executes if profitable.
        """
        dex_a: DexAdapter = adapters.get(self.dex_a_key)
        dex_b: DexAdapter = adapters.get(self.dex_b_key)

        if not dex_a or not dex_b:
            log.error("DEX_ADAPTERS_NOT_FOUND", needed=[self.dex_a_key, self.dex_b_key], available=list(adapters.keys()))
            return state # Return original state if adapters are missing

        try:
            # 1. Get quotes for the arbitrage path
            amount_in_wei = int(self.trade_amount * (10**self.token_a_decimals))
            
            # Quote 1: How much TOKEN_B can we get for our TOKEN_A on DEX A?
            quote_a_to_b = dex_a.get_quote(amount_in_wei, [self.token_a, self.token_b])
            amount_b_wei = quote_a_to_b[-1]
            
            # Quote 2: How much TOKEN_A can we get back for that amount of TOKEN_B on DEX B?
            quote_b_to_a = dex_b.get_quote(amount_b_wei, [self.token_b, self.token_a])
            final_amount_a_wei = quote_b_to_a[-1]

            # 2. Calculate profit
            profit_wei = final_amount_a_wei - amount_in_wei
            profit_decimal = Decimal(profit_wei) / (10**self.token_a_decimals)

            # NOTE: A real implementation needs to convert this profit to USD via an oracle
            # and subtract estimated gas fees. We'll simplify and compare like-for-like.
            
            log.debug("ARB_CHECK", dex_a=self.dex_a_key, dex_b=self.dex_b_key, profit=profit_decimal)

            if profit_decimal > self.min_profit_usd: # This assumes min_profit is also denominated in TOKEN_A
                log.info(
                    "PROFITABLE_ARB_OPPORTUNITY_FOUND",
                    path=[self.token_a, self.token_b, self.token_a],
                    trade_amount=self.trade_amount,
                    profit=profit_decimal,
                )
                
                # 3. Execute the arbitrage
                # A robust implementation would first check and request approvals if needed.
                # tx1_hash = dex_a.approve(...)
                # tx2_hash = dex_a.swap(...)
                # etc. For now, we assume approvals are met and calls succeed.
                
                log.warning("ARB_EXECUTION_SKIPPED_IN_DEMO")
                # In a real run, you would uncomment the swap logic here.

                # 4. Update and return new state
                trade_details = {"tx1": "0xsim_hash_1", "tx2": "0xsim_hash_2", "profit": float(profit_decimal)}
                capital_changes = {self.token_a: profit_decimal}
                
                new_state = state.record_trade(trade_details)
                new_state = new_state.update_capital(capital_changes)
                return new_state

        except Exception as e:
            # If any part of the quote/trade process fails, log it and continue.
            log.error("ARB_CYCLE_FAILED", error=str(e), exc_info=False)
        
        # If no opportunity was found or an error occurred, return the original state
        return state

    def mutate(self, adapters: dict) -> bool:
        """
        Applies new parameters from the AI model. This fulfills the "Mutation/AI safety"
        requirement by being an explicit, audited action.
        """
        ai_model: AIModelAdapter = adapters.get("ai_model")
        if not ai_model:
            log.warning("MUTATE_SKIPPED_NO_AI_ADAPTER", strategy_name=self.strategy_name)
            return False

        # Get a suggestion from the AI model
        new_params = ai_model.get_parameter_suggestion(self.strategy_name, self.get_params())

        if new_params:
            log.warning(
                "STRATEGY_PARAMETER_MUTATION_RECEIVED",
                strategy_name=self.strategy_name,
                old_params=self.get_params(),
                new_params=new_params,
            )
            
            # Apply the new parameters safely
            self.trade_amount = Decimal(new_params.get("trade_amount", self.trade_amount))
            self.min_profit_usd = Decimal(new_params.get("min_profit_usd", self.min_profit_usd))
            
            log.info("STRATEGY_MUTATION_APPLIED", new_config=self.get_params())
            return True
            
        return False
        
    def abort(self, reason: str):
        log.critical("STRATEGY_ABORTED_CrossDomainArbitrage", reason=reason)

    def simulate(self, state, adapters, config):
        """Simulated execution for safety checks."""
        # For now, simulation will just call the run method. A more advanced
        # simulation would use forked state and not send real transactions.
        log.info("SIMULATING CrossDomainArbitrageStrategy.run")
        return self.run(state, adapters, config)

    def snapshot(self, path):
        """Snapshot session/state for DRP/rollback."""
        # This would typically save the strategy's internal state, beyond the main agent state.
        # For this simple strategy, there is no extra state to save.
        raise NotImplementedError

    def restore(self, path):
        """Restore from snapshot."""
        raise NotImplementedError
