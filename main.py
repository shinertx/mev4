# /main.py
# The main entrypoint for the MEV-OG NextGen application.
# It initializes all necessary components and starts the agent loop.
# This version represents the fully-featured system with all adapters available.

import os
from decimal import Decimal

from src.core.logger import log
from src.core.config import settings
from src.core.agent import Agent

# --- Import All Adapters ---
from src.core.tx import TransactionManager
from src.adapters.dex import DexAdapter
from src.adapters.cex import CexAdapter
from src.adapters.oracle import LendingProtocolOracle
from src.adapters.bridge import StargateBridgeAdapter
from src.adapters.ai_model import AIModelAdapter
from src.adapters.flashloan import FlashloanAdapter

# --- Import a Strategy to Run ---
# We will run the CexDexArbitrageStrategy for this example.
from src.strategies.cex_dex_arb import CexDexArbitrageStrategy


# --- Main Execution ---
def main():
    """Initializes all system components and runs the primary agent."""
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
        log.critical("FAILED_TO_INITIALIZE_TRANSACTION_MANAGER", error=str(e), exc_info=True)
        return # Hard exit if we can't connect to the chain or load the account.

    # --- 2. Initialize All Adapters ---
    # In a mature system, these addresses would come from a config file.
    # For clarity, we're defining them here. These are for Ethereum Mainnet.
    UNISWAP_V2_ROUTER = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
    AAVE_V3_POOL = "0x87870Bca3F3fD6036b81f5cEBFbB9635514ED404"
    STARGATE_ROUTER = "0x8731d54E9D02c286767d56ac03e8037C07e01e98"
    # The FlashloanReceiver contract address you would have deployed
    FLASHLOAN_RECEIVER = "0xYourDeployedFlashloanReceiverAddress" # <-- REPLACE THIS

    adapters = {
        "tx_manager": tx_manager,
        "dex_uniswap": DexAdapter(tx_manager, UNISWAP_V2_ROUTER),
        "cex_binance": CexAdapter(),
        "oracle_aave": LendingProtocolOracle(pool_address=AAVE_V3_POOL),
        "bridge_stargate": StargateBridgeAdapter(tx_manager, STARGATE_ROUTER),
        "flashloan_aave": FlashloanAdapter(tx_manager, FLASHLOAN_RECEIVER),
        "ai_model": AIModelAdapter(), # Using the mock version for now
    }
    log.info("ADAPTERS_INITIALIZED", loaded_adapters=list(adapters.keys()))

    # --- 3. Initialize Strategy ---
    # This section determines which strategy the agent will run.
    # We are configuring the CexDexArbitrageStrategy as our primary strategy.
    WETH_ADDR = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    USDC_ADDR = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

    strategy = CexDexArbitrageStrategy(
        cex_key="cex_binance",
        dex_key="dex_uniswap",
        cex_symbol="ETHUSDT",
        onchain_path=[USDC_ADDR, WETH_ADDR],
        trade_amount=Decimal("0.1"),  # The amount of ETH/WETH to arbitrage with
        min_profit_usd=Decimal("5.0") # Minimum profit threshold in USD to execute
    )

    # --- 4. Initialize and Run Agent ---
    # The agent orchestrates the strategy execution loop.
    # In a real system, initial capital would be fetched from on-chain and CEX balances.
    initial_capital = {
        "WETH_ONCHAIN": Decimal("0.1"),
        "USDC_ONCHAIN": Decimal("5000.0"),
        "ETH_BINANCE": Decimal("0.1"),
        "USDT_BINANCE": Decimal("5000.0"),
    }
    
    agent = Agent(
        strategy=strategy,
        initial_capital=initial_capital
    )
    
    # Inject the live adapters into the agent, making them available to the strategy.
    agent.adapters = adapters
    
    # Start the main execution loop.
    agent.run_loop()

if __name__ == "__main__":
    main()
