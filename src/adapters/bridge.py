# /src/adapters/bridge.py
# Aligns with PROJECT_BIBLE.md: Section 2, 3, 5
# - Bridge adapter for programmatic cross-chain capital movement.
# - Implemented for the Stargate Finance bridge router.
# - Checks kill switch before initiating any transfer.

from decimal import Decimal
from web3 import Web3
from web3.contract import Contract

from src.core.tx import TransactionManager, TransactionKillSwitchError
from src.core.kill import is_kill_switch_active
from src.core.logger import get_logger

log = get_logger(__name__)

# Minimal ABI for the Stargate Router contract
STARGATE_ROUTER_ABI = [{"inputs":[{"internalType":"uint16","name":"_dstChainId","type":"uint16"},{"internalType":"uint8","name":"_functionType","type":"uint8"},{"internalType":"address","name":"_to","type":"address"},{"internalType":"bytes","name":"_calldata","type":"bytes"},{"internalType":"uint256","name":"_extOptions","type":"uint256"}],"name":"send","outputs":[],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_dstChainId","type":"uint16"},{"internalType":"uint256","name":"_srcPoolId","type":"uint256"},{"internalType":"uint256","name":"_dstPoolId","type":"uint256"},{"internalType":"address","name":"_refundAddress","type":"address"},{"internalType":"uint256","name":"_amountLD","type":"uint256"},{"internalType":"uint256","name":"_minAmountLD","type":"uint256"},{"components":[{"internalType":"uint256","name":"dstGasForCall","type":"uint256"},{"internalType":"uint256","name":"dstNativeAmount","type":"uint256"},{"internalType":"bytes","name":"dstNativeAddr","type":"bytes"}],"internalType":"struct IStargateRouter.lzTxObj","name":"_lzTxParams","type":"tuple"},{"internalType":"bytes","name":"_to","type":"bytes"},{"internalType":"bytes","name":"_payload","type":"bytes"}],"name":"swap","outputs":[],"stateMutability":"payable","type":"function"}]


class StargateBridgeAdapter:
    """
    An adapter for initiating cross-chain asset transfers using Stargate Finance.
    """
    def __init__(self, tx_manager: TransactionManager, router_address: str):
        self.tx_manager = tx_manager
        self.w3: Web3 = tx_manager.w3
        self.router_address = Web3.to_checksum_address(router_address)
        self.router_contract: Contract = self.w3.eth.contract(
            address=self.router_address, abi=STARGATE_ROUTER_ABI
        )
        log.info(
            "BRIDGE_ADAPTER_INITIALIZED",
            protocol="Stargate",
            router_address=self.router_address
        )

    def _check_kill_switch(self):
        """BIBLE ENFORCEMENT: Safety check before initiating a bridge transfer."""
        if is_kill_switch_active():
            raise TransactionKillSwitchError("Bridge transfer blocked by system kill switch.")

    def bridge_asset(
        self,
        dest_chain_id: int,
        source_pool_id: int,
        dest_pool_id: int,
        amount_ld: int,
        min_amount_ld: int
    ) -> str:
        """
        Initiates a cross-chain swap using Stargate's `swap` function.

        Args:
            dest_chain_id: The LayerZero chain ID for the destination network.
            source_pool_id: The Stargate pool ID for the asset on the source chain.
            dest_pool_id: The Stargate pool ID for the asset on the destination chain.
            amount_ld: The amount of local decimals (wei) to bridge.
            min_amount_ld: The minimum amount to receive on the destination chain.

        Returns:
            The transaction hash of the bridge initiation on the source chain.
        """
        self._check_kill_switch()

        log.warning(
            "BRIDGE_TRANSFER_INITIATED",
            protocol="Stargate",
            from_chain=self.w3.eth.chain_id,
            to_chain=dest_chain_id,
            amount=amount_ld
        )

        # The `swap` function requires a `lzTxObj` for gas payment on the destination.
        # This is a complex parameter; we'll use zero values for a basic transfer.
        # A production implementation MUST calculate the required native gas.
        lz_tx_params = {
            "dstGasForCall": 0,
            "dstNativeAmount": 0,
            "dstNativeAddr": "0x",
        }

        # Build the transaction to call the router.
        # The executor's address is encoded in bytes for the `_to` parameter.
        tx_params = self.router_contract.functions.swap(
            dest_chain_id,
            source_pool_id,
            dest_pool_id,
            self.tx_manager.address, # Refund address in case of failure
            amount_ld,
            min_amount_ld,
            lz_tx_params,
            self.tx_manager.address.encode('utf-8').hex(), # `to` address
            b'' # empty payload
        ).build_transaction({
            'from': self.tx_manager.address,
            'nonce': self.tx_manager.nonce,
            # Bridging often requires sending native tokens to pay for gas on LayerZero.
            # This must be calculated and passed as the `value`.
            'value': 0 # Placeholder: A real call needs to estimate and send native gas value.
        })
        
        return self.tx_manager.build_and_send_transaction(tx_params)
