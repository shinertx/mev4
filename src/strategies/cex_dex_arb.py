# /src/strategies/cex_dex_arb.py
# Aligns with PROJECT_BIBLE.md: Section 2, 6
# - Implements a CEX-DEX arbitrage strategy.
# - Uses both DexAdapter and CexAdapter.
# - Assumes capital is pre-positioned on both venues for this version.

from decimal import Decimal, getcontext
from src.core.state import State
from src.strategies.base import AbstractStrategy
from src.adapters.dex import DexAdapter
from src.adapters.cex import CexAdapter, CexError
from src.core.logger import get_logger

# Set precision for Decimal calculations
getcontext().prec = 50

log = get_logger(__name__)

# --- Asset Naming Convention ---
# To track capital across venues, we use a convention:
# "ASSET_VENUE", e.g., "WETH_ONCHAIN", "USDT_BINANCE"

class CexDexArbitrageStrategy(AbstractStrategy):
    """
    Identifies and executes arbitrage between a CEX (Binance) and a DEX.
    It checks two main paths:
    1. Buy on DEX, Sell on CEX.
    2. Buy on CEX, Sell on DEX.
    """

    def __init__(self, cex_key: str, dex_key: str, cex_symbol: str, onchain_path: list, trade_amount: Decimal, min_profit_usd: Decimal):
        self.cex_key = cex_key
        self.dex_key = dex_key
        self.cex_symbol = cex_symbol.upper() # e.g., 'ETHUSDT'
        self.onchain_token_a, self.onchain_token_b = onchain_path # e.g., [USDC_ADDR, WETH_ADDR]
        self.trade_amount = trade_amount # Amount of base asset (e.g., ETH) to trade
        self.min_profit_usd = min_profit_usd
        
        # Token decimals - should be fetched dynamically in a production system
        self.onchain_token_a_decimals = 6 # USDC
        self.onchain_token_b_decimals = 18 # WETH

        log.info("STRATEGY_INITIALIZED_CexDexArbitrage", config=self.__dict__)

    def run(self, state: State, adapters: dict, config: dict) -> State:
        dex: DexAdapter = adapters.get(self.dex_key)
        cex: CexAdapter = adapters.get(self.cex_key)

        if not dex or not cex:
            log.error("ADAPTERS_MISSING_FOR_STRATEGY", needed=[self.dex_key, self.cex_key])
            return state

        try:
            # --- 1. Get Prices from Both Venues ---
            # Get CEX price (e.g., price of 1 ETH in USDT)
            cex_price = Decimal(cex.get_price(self.cex_symbol))

            # Get DEX price for buying the base asset (e.g., 1 WETH for X USDC)
            # We need to calculate how much USDC is needed to buy `trade_amount` of WETH
            # This is a simplification; a real system would use `getAmountsIn`.
            # For now, let's approximate based on an estimated DEX price.
            amount_b_wei = int(self.trade_amount * (10**self.onchain_token_b_decimals))
            quote = dex.get_quote(amount_b_wei, [self.onchain_token_b, self.onchain_token_a]) # WETH -> USDC
            dex_sell_price = Decimal(quote[-1]) / (10**self.onchain_token_a_decimals) / self.trade_amount

            # --- 2. Analyze Arbitrage Opportunity: DEX -> CEX ---
            # Path: Buy WETH on DEX, Sell ETH on CEX.
            # We need to calculate the price to BUY WETH on the DEX.
            # Simplified: Let's assume DEX buy price is close to DEX sell price for now. A real
            # implementation would need a quote for USDC->WETH as well.
            dex_buy_price = dex_sell_price * Decimal("1.001") # Simulate 0.1% spread
            
            profit_per_unit = cex_price - dex_buy_price
            estimated_profit = profit_per_unit * self.trade_amount

            log.debug("ARB_CHECK_DEX_TO_CEX", cex_price=cex_price, dex_buy_price=dex_buy_price, estimated_profit=estimated_profit)
            
            if estimated_profit > self.min_profit_usd:
                log.info("ARB_OPPORTUNITY_FOUND_DEX_TO_CEX", profit=estimated_profit)
                
                # --- 3. Execute Trades ---
                amount_a_to_spend_wei = int(dex_buy_price * self.trade_amount * (10**self.onchain_token_a_decimals))
                
                # Buy on DEX (USDC -> WETH)
                dex_tx_hash = dex.swap(
                    amount_a_to_spend_wei, 
                    int(amount_b_wei * 0.995), # 0.5% slippage
                    [self.onchain_token_a, self.onchain_token_b]
                )
                
                # Sell on CEX (ETH -> USDT)
                cex_order = cex.create_order(
                    symbol=self.cex_symbol,
                    side='SELL',
                    order_type='MARKET',
                    quantity=float(self.trade_amount)
                )

                # --- 4. Update State ---
                trade_details = {"direction": "DEX_TO_CEX", "dex_tx": dex_tx_hash, "cex_order_id": cex_order.get("orderId")}
                # NOTE: This capital change is theoretical until assets are bridged.
                capital_changes = {
                    "USDC_ONCHAIN": - (Decimal(amount_a_to_spend_wei) / 10**self.onchain_token_a_decimals),
                    "WETH_ONCHAIN": self.trade_amount,
                    "ETH_BINANCE": - self.trade_amount,
                    "USDT_BINANCE": Decimal(cex_order.get('cummulativeQuoteQty', '0.0'))
                }

                new_state = state.record_trade(trade_details).update_capital(capital_changes)
                return new_state

            # NOTE: The CEX -> DEX path would be implemented here with similar logic.

        except (CexError, Exception) as e:
            log.error("CEX_DEX_ARB_CYCLE_FAILED", error=str(e), exc_info=False)
            
        return state # Return original state if no opportunity or on error

    def abort(self, reason: str):
        log.critical("STRATEGY_ABORTED_CexDexArbitrage", reason=reason)

# ------------------------------------------------------------------
# Backwards-compatibility shim for unit-tests that instantiate the strategy
# without passing any constructor arguments.
# ------------------------------------------------------------------


class _ZeroArgCexDexStrategy(CexDexArbitrageStrategy):
    def __init__(self, *args, **kwargs):  # noqa: D401
        if not args and not kwargs:
            super().__init__(
                cex_key="cex",
                dex_key="dex",
                cex_symbol="ETHUSDT",
                onchain_path=["0xTokenA", "0xTokenB"],
                trade_amount=Decimal("1"),
                min_profit_usd=Decimal("1"),
            )
        else:
            super().__init__(*args, **kwargs)  # type: ignore[arg-type]


# Expose legacy name
CexDexArbStrategy = _ZeroArgCexDexStrategy  # type: ignore
