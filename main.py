# /main.py
# The main entrypoint for the MEV-OG NextGen application.
# It initializes all necessary components and starts the agent loop.

import os
from decimal import Decimal

from src.core.logger import get_logger, log
from src.core.config import settings
from src.core.agent import Agent

# --- Import Adapters and Strategies ---
# In a real deployment, you might have a factory or dynamic loader here.
from src.core.tx import TransactionManager
from src.adapters.dex import DexAdapter
from src.strategies.cross_domain import CrossDomainArbitrageStrategy

# --- Main Execution ---
def main():
    """Initializes and runs the primary agent."""
    log.info(
        "MEV_OG_SYSTEM_STARTING",
        log_level=settings.LOG_LEVEL,
        gcp_project=settings.GCP_PROJECT_ID
    )

    # --- 1. Initialize Core Components ---
    # The TransactionManager is the foundation for any on-chain adapter.
    # It will fail fast if RPC_URL or PRIVATE_KEY are invalid.
    try:
        tx_manager = TransactionManager()
    except Exception as e:
        log.critical("FAILED_TO_INITIALIZE_TRANSACTION_MANAGER", error=str(e))
        return # Exit if we can't connect to the chain or load the account.

    # --- 2. Initialize Adapters ---
    # These would be configured via environment variables or a config file.
    # For this example, we'll use Uniswap and Sushiswap on Mainnet.
    # IMPORTANT: Ensure these are the correct router addresses for your target chain.
    UNISWAP_V2_ROUTER = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
    SUSHISWAP_ROUTER = "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F"
    
    adapters = {
        "tx_manager": tx_manager,
        "uniswap": DexAdapter(tx_manager, UNISWAP_V2_ROUTER),
        "sushiswap": DexAdapter(tx_manager, SUSHISWAP_ROUTER)
    }
    log.info("ADAPTERS_INITIALIZED", loaded_adapters=list(adapters.keys()))

    # --- 3. Initialize Strategy ---
    # Configure the strategy with its parameters.
    # These should also come from a more dynamic config system in a mature version.
    WETH_ADDR = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    USDC_ADDR = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

    strategy = CrossDomainArbitrageStrategy(
        dex_a_key="uniswap",
        dex_b_key="sushiswap",
        trade_path=[WETH_ADDR, USDC_ADDR],
        trade_amount=Decimal("0.1"),  # The amount of WETH to test arbitrage with
        min_profit_usd=Decimal("0.005") # Minimum profit threshold in WETH
    )

    # --- 4. Initialize and Run Agent ---
    # The agent gets the strategy, initial capital, and all adapters.
    # Initial capital should be fetched from on-chain balances in a real system.
    agent = Agent(
        strategy=strategy,
        initial_capital={WETH_ADDR: Decimal("0.1")} # Placeholder
    )
    
    agent.adapters = adapters # Inject the live adapters
    agent.run_loop()

if __name__ == "__main__":
    main()
