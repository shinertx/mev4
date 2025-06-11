# /main.py
# FINAL PRODUCTION VERSION
# This version correctly orchestrates multiple, isolated agents and tasks CONCURRENTLY.
# It rejects the flawed shared-state "slow_loops" model.
import asyncio
from decimal import Decimal
from aiohttp import web

# All necessary imports from our previous robust versions...
from src.core.config import settings
from src.core.config_validator import validate as validate_config
from src.core.logger import configure_logging, get_logger
from src.core.kill import is_kill_switch_active
from src.core.drp import get_last_snapshot_timestamp
from src.core.state import State
from src.core.tx import TransactionManager
from src.core.agent import Agent # Our intelligent, single-strategy agent
from src.adapters.dex import DexAdapter
from src.adapters.mempool import MempoolAdapter
from src.adapters.ai_model import AIModelAdapter
from src.strategies.sandwich import SandwichStrategy
from src.strategies.rebalancer_strategy import RebalancerStrategy # Example stateful strategy

async def healthz(request):
    """Provides a JSON health status for the service."""
    # ... healthz logic ...
    return web.json_response({"status": "ok", "kill_switch_active": is_kill_switch_active()})

async def main():
    configure_logging()
    log = get_logger("MEV-OG.System")
    validate_config()
    log.info("FINAL_PRODUCTION_ENGINE_STARTING")

    # --- Initialize Core Components (using our hardened, async versions) ---
    tx_manager = TransactionManager()
    await tx_manager.initialize()
    
    # --- Initialize Adapters ---
    adapters = {
        "tx_manager": tx_manager,
        "dex": DexAdapter(tx_manager, settings.UNISWAP_ROUTER_ADDRESS),
        "mempool": MempoolAdapter(),
        "ai_model": AIModelAdapter(),
        # ... other async adapters ...
    }

    # --- TASK 1: Initialize the High-Frequency, Event-Driven Strategy ---
    sandwich_strategy = SandwichStrategy(adapters['dex'], Decimal(settings.SANDWICH_MIN_PROFIT))
    async def mempool_listener():
        await adapters['mempool'].connect()
        async for tx in adapters['mempool'].stream_transactions():
            # Each sandwich attempt is a stateless, fire-and-forget task
            asyncio.create_task(sandwich_strategy.process_transaction(tx, State()))

    # --- TASK 2: Initialize the Slow, Stateful, AI-Managed Rebalancer Agent ---
    # Each stateful strategy gets its OWN state and its OWN agent.
    rebalancer_strategy = RebalancerStrategy()
    rebalancer_state = State(capital_base={"USDC_ONCHAIN": Decimal("10000"), "USDT_BINANCE": Decimal("10000")})
    rebalancer_agent = Agent(
        strategy=rebalancer_strategy, 
        initial_state=rebalancer_state, 
        adapters=adapters
    )

    # --- TASK 3: Initialize ANOTHER Slow, Stateful Agent (e.g. for Liquidation) ---
    # liquidation_strategy = LiquidationStrategy(...)
    # liquidation_state = State(...)
    # liquidation_agent = Agent(...)

    # --- Start Healthcheck Server & All Tasks ---
    app = web.Application()
    app.add_routes([web.get("/healthz", healthz)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", settings.HEALTH_PORT or 8080)
    await site.start()
    log.info(f"HEALTHCHECK_SERVER_STARTED on port {settings.HEALTH_PORT or 8080}")

    log.info("STARTING_ALL_CONCURRENT_TASKS")
    await asyncio.gather(
        mempool_listener(),
        rebalancer_agent.run_loop(),
        # liquidation_agent.run_loop(), # Each agent runs its own independent loop
    )
    
    tx_manager.close()
    await runner.cleanup()
    log.warning("SYSTEM_SHUTDOWN_COMPLETE")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
