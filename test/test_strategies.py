# Example usage in a Pytest test file
from src.adapters.mock import MockTransactionManager, MockDexAdapter
from src.strategies.some_strategy import SomeArbitrageStrategy # Assuming this exists
from src.core.state import State
from decimal import Decimal

def test_strategy_executes_swap():
    # 1. Setup
    mock_tx_manager = MockTransactionManager()
    mock_dex_adapter = MockDexAdapter(mock_tx_manager)

    # Configure the mock environment
    weth_addr = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    usdc_addr = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    mock_dex_adapter.set_quote(path=[weth_addr, usdc_addr], amount_out=3000 * 10**6) # 1 WETH -> 3000 USDC

    strategy = SomeArbitrageStrategy()
    initial_state = State(capital_base={"WETH": Decimal("1.0")})
    adapters = {"dex": mock_dex_adapter, "tx_manager": mock_tx_manager}

    # 2. Execute
    final_state = strategy.run(initial_state, adapters, {})

    # 3. Assert
    # Check that a transaction was actually sent
    assert len(mock_tx_manager.sent_transactions) > 0
    # Check that the swap transaction was sent to the router
    swap_tx = mock_tx_manager.sent_transactions[-1]
    assert swap_tx["to"] == mock_dex_adapter.router_address
    assert "swap" in swap_tx["data"]
    # Check that the state was updated
    # assert final_state.capital_base["USDC"] > 0
