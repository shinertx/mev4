# /test/test_strategies.py
# Aligns with PROJECT_BIBLE.md: Section 2, 4
# - Tests a concrete strategy (CrossDomainArbitrageStrategy).
# - Utilizes mock adapters for "Simulation-first" development.
# - Verifies correct state mutation, transaction dispatch, and safety checks.

import os
import pytest
from decimal import Decimal

from src.core.state import State
from src.core.kill import activate_kill_switch, KILL_SWITCH_FILE
from src.strategies.cross_domain import CrossDomainArbitrageStrategy
from src.adapters.mock import MockTransactionManager, MockDexAdapter

# --- Constants for testing ---
WETH_ADDR = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
USDC_ADDR = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
TRADE_AMOUNT_WETH = Decimal("1")
PROFIT_THRESHOLD = Decimal("0.05") # Expect at least 0.05 WETH profit

# --- Pytest Fixture for Test Setup ---

@pytest.fixture
def mock_env():
    """Sets up a reusable mock environment for strategy testing."""
    mock_tx_manager = MockTransactionManager(from_address="0xExecutor")
    mock_uniswap = MockDexAdapter(mock_tx_manager)
    mock_sushiswap = MockDexAdapter(mock_tx_manager)
    
    adapters = {
        "uniswap": mock_uniswap,
        "sushiswap": mock_sushiswap,
        "tx_manager": mock_tx_manager
    }
    
    strategy = CrossDomainArbitrageStrategy(
        dex_a_key="uniswap",
        dex_b_key="sushiswap",
        trade_path=[WETH_ADDR, USDC_ADDR],
        trade_amount=TRADE_AMOUNT_WETH,
        min_profit_usd=PROFIT_THRESHOLD # NOTE: Using WETH as proxy for USD for this test
    )
    
    initial_state = State(capital_base={WETH_ADDR: Decimal("10")})
    
    return strategy, initial_state, adapters

@pytest.fixture
def kill_switch_context():
    """A context manager fixture to safely test kill switch behavior."""
    try:
        activate_kill_switch(reason="Testing kill switch")
        yield
    finally:
        if os.path.exists(KILL_SWITCH_FILE):
            os.remove(KILL_SWITCH_FILE)

# --- Test Cases ---

def test_strategy_executes_on_profitable_opportunity(mock_env):
    """
    GIVEN a profitable arbitrage opportunity exists between two mock DEXs
    WHEN the strategy runs
    THEN it should execute two swaps and update the state with the profit.
    """
    strategy, initial_state, adapters = mock_env
    # 1 WETH -> 3000 USDC on Uniswap
    adapters["uniswap"].set_quote(path=[WETH_ADDR, USDC_ADDR], amount_out=3000 * 10**18)
    # 3000 USDC -> 1.1 WETH on Sushiswap (0.1 WETH profit)
    adapters["sushiswap"].set_quote(path=[USDC_ADDR, WETH_ADDR], amount_out=int(Decimal("1.1") * 10**18))
    
    # Act
    new_state = strategy.run(initial_state, adapters, {})
    
    # Assert
    # State should be updated, so it must be a *new* object
    assert new_state is not initial_state
    # Two swaps should have been sent (one on each DEX)
    assert len(adapters["tx_manager"].sent_transactions) == 2
    
    # State audit history should record the trade
    assert len(new_state.history) == 1
    assert new_state.history[0]["event_type"] == "TRADE_EXECUTED"
  
    # Capital should be updated with the profit
    expected_profit = Decimal("0.1")
    assert new_state.capital_base[WETH_ADDR] == initial_state.capital_base[WETH_ADDR] + expected_profit

def test_strategy_does_not_execute_on_unprofitable_opportunity(mock_env):
    """
    GIVEN an unprofitable arbitrage opportunity
    WHEN the strategy runs
    THEN it should not execute any transactions and the state should remain unchanged.
    """
    strategy, initial_state, adapters = mock_env
    # 1 WETH -> 3000 USDC on Uniswap
    adapters["uniswap"].set_quote(path=[WETH_ADDR, USDC_ADDR], amount_out=3000 * 10**18)
    # 3000 USDC -> 0.9 WETH on Sushiswap (a loss)
    adapters["sushiswap"].set_quote(path=[USDC_ADDR, WETH_ADDR], amount_out=int(Decimal("0.9") * 10**18))
    
    # Act
    new_state = strategy.run(initial_state, adapters, {})

    # Assert
    # No transactions should be sent
    assert len(adapters["tx_manager"].sent_transactions) == 0
    # The state should not have changed, so the original object is returned
    assert new_state is initial_state
    assert len(new_state.history) == 0

def test_strategy_is_halted_by_kill_switch(mock_env, kill_switch_context):
    """
    GIVEN a profitable arbitrage opportunity
    BUT the kill switch is active
    WHEN the strategy runs
    THEN it should be gracefully halted without sending transactions.
    """
    # Arrange: Same profitable setup as the first test
    strategy, initial_state, adapters = mock_env
    adapters["uniswap"].set_quote(path=[WETH_ADDR, USDC_ADDR], amount_out=3000 * 10**18)
    adapters["sushiswap"].set_quote(path=[USDC_ADDR, WETH_ADDR], amount_out=int(Decimal("1.1") * 10**18))
    
    # Act
    # The strategy's top-level run() catches exceptions from adapters
    # to ensure the agent loop doesn't crash.
    new_state = strategy.run(initial_state, adapters, {})
    
    # Assert
    # No transactions should have been sent because the adapter's `swap` method
    # would raise a `TransactionKillSwitchError` immediately.
    assert len(adapters["tx_manager"].sent_transactions) == 0
    # State should be unchanged
    assert new_state is initial_state
