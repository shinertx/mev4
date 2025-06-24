# /test/test_forked_sim.py
# Aligns with PROJECT_BIBLE.md: Section 4
# - Provides a concrete example of testing on a forked mainnet environment.
# - Uses REAL adapters against a local Anvil node to validate end-to-end behavior.

import pytest
from web3 import Web3
from decimal import Decimal
import logging

from src.core.config import settings
from src.core.tx import TransactionManager
from src.adapters.dex import DexAdapter, ERC20_ABI

# --- Real Mainnet Addresses ---
WETH_ADDR = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
USDC_ADDR = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
UNISWAP_V2_ROUTER = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
# An address with lots of WETH on mainnet that we can impersonate
WETH_WHALE = "0x2f0b23f53734252bda2277357e97e1517d6b042a"

# --- Pytest Fixture for Test Setup ---

@pytest.fixture(scope="module")
def forked_environment():
    """
    A fixture that sets up a full environment for testing on a forked chain.
    It assumes `scripts/simulate_fork.sh` is running in a separate terminal.
    """
    # Override the default RPC URL to point to our local Anvil node
    original_rpc_url = settings.ETH_RPC_URL
    settings.ETH_RPC_URL = "http://127.0.0.1:8545"

    try:
        w3 = Web3(Web3.HTTPProvider(settings.ETH_RPC_URL))
        if not w3.is_connected():
            pytest.skip("Could not connect to local Anvil fork. Run 'scripts/simulate_fork.sh' first.")
        
        # Impersonate the whale account so we can sign transactions from it
        w3.provider.make_request("anvil_impersonateAccount", [WETH_WHALE])
        
        # Instantiate REAL adapters pointed at the fork
        tx_manager = TransactionManager()
        # Override the manager's account to be the whale we are impersonating
        tx_manager.address = Web3.to_checksum_address(WETH_WHALE)
        
        dex_adapter = DexAdapter(tx_manager, UNISWAP_V2_ROUTER)
        
        yield w3, tx_manager, dex_adapter
        
    finally:
        # Restore original settings and stop impersonating
        settings.ETH_RPC_URL = original_rpc_url
        if w3.is_connected():
            w3.provider.make_request("anvil_stopImpersonatingAccount", [WETH_WHALE])
            

@pytest.mark.forked
def test_real_dex_swap_on_forked_mainnet(forked_environment):
    """
    GIVEN a running mainnet fork with an impersonated whale account
    WHEN we execute a swap using our real DexAdapter
    THEN the on-chain balances should change as expected.
    """
    w3, tx_manager, dex_adapter = forked_environment
    
    # 1. Arrange: Get initial balances
    weth_contract = w3.eth.contract(address=WETH_ADDR, abi=ERC20_ABI)
    usdc_contract = w3.eth.contract(address=USDC_ADDR, abi=ERC20_ABI)

    whale_weth_before = weth_contract.functions.balanceOf(tx_manager.address).call()
    whale_usdc_before = usdc_contract.functions.balanceOf(tx_manager.address).call()
    
    amount_to_swap_wei = int(Decimal("1") * 10**18) # 1 WETH

    # 2. Act: Execute the approval and swap using our real adapters
    # We must first approve the Uniswap router to spend our WETH
    approve_tx_hash = dex_adapter.approve(WETH_ADDR, amount_to_swap_wei)
    w3.eth.wait_for_transaction_receipt(approve_tx_hash) # Wait for approval to confirm

    # Now execute the swap
    swap_tx_hash = dex_adapter.swap(
        amount_in_wei=amount_to_swap_wei,
        min_amount_out_wei=0, # No slippage concerns in a single-threaded test
        path=[WETH_ADDR, USDC_ADDR]
    )
    w3.eth.wait_for_transaction_receipt(swap_tx_hash) # Wait for swap to confirm

    # 3. Assert: Check final balances
    whale_weth_after = weth_contract.functions.balanceOf(tx_manager.address).call()
    whale_usdc_after = usdc_contract.functions.balanceOf(tx_manager.address).call()

    assert whale_weth_after == whale_weth_before - amount_to_swap_wei
    assert whale_usdc_after > whale_usdc_before
    
    logging.info(f"Forked swap successful! Traded 1 WETH for {(whale_usdc_after - whale_usdc_before) / 1e6} USDC.")
