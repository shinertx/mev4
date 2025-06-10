# /src/strategies/cross_domain.py
# Aligns with PROJECT_BIBLE.md: Section 2, 6
# - Implements AbstractStrategy.
# - A simple cross-DEX arbitrage strategy to demonstrate end-to-end functionality.

from decimal import Decimal, getcontext
from src.core.state import State
from src.strategies.base import AbstractStrategy
from src.adapters.dex import DexAdapter
from src.core.logger import get_logger

# Set precision for Decimal calculations
getcontext().prec = 50 

log = get_logger(__name__)

class CrossDomainArbitrageStrategy(AbstractStrategy):
    """
    A strategy that identifies and executes arbitrage opportunities between two DEXs on the same chain.
    Example: Buy WETH for USDC on Uniswap, sell WETH for USDC on Sushiswap for a profit.
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
        # Note: In a real scenario, you'd need decimals for each token to convert properly.
        # We'll assume 18 decimals for simplicity here. This should be fetched from the token contract.
        self.token_a_decimals = 18 
        
        log.info("STRATEGY_INITIALIZED_CrossDomainArbitrage", config=self.__dict__)

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

            # NOTE: A real implementation needs to convert profit_decimal to USD
            # and subtract estimated gas fees. We'll simplify for now.
            # Let's assume profit_decimal is comparable to min_profit_usd for this example.
            
            log.debug("ARB_CHECK", dex_a=self.dex_a_key, dex_b=self.dex_b_key, profit=profit_decimal)

            if profit_decimal > self.min_profit_usd:
                log.info(
                    "PROFITABLE_ARB_OPPORTUNITY_FOUND",
                    path=[self.token_a, self.token_b, self.token_a],
                    trade_amount=self.trade_amount,
                    profit=profit_decimal,
                )
                
                # 3. Execute the arbitrage
                # In a real scenario, you'd need approvals here. The DexAdapter handles that.
                # dex_a.approve(...) -> returns tx_hash_1
                # dex_b.approve(...) -> returns tx_hash_2
                
                # Execute Swap 1: Token A -> Token B on DEX A
                tx1_hash = dex_a.swap(amount_in_wei, int(amount_b_wei * 0.995), [self.token_a, self.token_b])
                # Wait for receipt if necessary, for now we assume it confirms quickly
                
                # Execute Swap 2: Token B -> Token A on DEX B
                tx2_hash = dex_b.swap(amount_b_wei, int(final_amount_a_wei * 0.995), [self.token_b, self.token_a])

                # 4. Update and return new state
                trade_details = {"tx1": tx1_hash, "tx2": tx2_hash, "profit": float(profit_decimal)}
                capital_changes = {self.token_a: profit_decimal}
                
                new_state = state.record_trade(trade_details)
                new_state = new_state.update_capital(capital_changes)
                return new_state

        except Exception as e:
            # If any part of the quote/trade process fails, log it and continue.
            log.error("ARB_CYCLE_FAILED", error=str(e), exc_info=False)
        
        # If no opportunity was found or an error occurred, return the original state
        return state

    def abort(self, reason: str):
        log.critical("STRATEGY_ABORTED_CrossDomainArbitrage", reason=reason)
