# /src/adapters/flashloan.py
# Aligns with PROJECT_BIBLE.md: Section 2, 3, 5
# - Adapter for initiating flash loans via a pre-deployed receiver contract.
# - Checks kill-switch before initiating the transaction.

from typing import List, Dict

from web3 import Web3
from web3.contract import Contract

from src.core.tx import TransactionManager, TransactionKillSwitchError
from src.core.kill import check, KillSwitchActiveError
from src.core.logger import get_logger

log = get_logger(__name__)

# A minimal ABI for our FlashloanReceiver contract
RECEIVER_ABI = [
    {"inputs": [{"internalType": "address[]", "name": "assets", "type": "address[]"}, {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}, {"internalType": "bytes", "name": "params", "type": "bytes"}], "name": "initiateFlashloan", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "target", "type": "address"}, {"internalType": "bytes", "name": "data", "type": "bytes"}], "name": "executeCall", "outputs": [], "stateMutability": "nonpayable", "type": "function"}
]

class FlashloanAdapter:
    """
    Adapter for interacting with our deployed FlashloanReceiver contract.
    This class helps strategies build and execute flash loan transactions.
    """
    def __init__(self, tx_manager: TransactionManager, receiver_address: str):
        self.tx_manager = tx_manager
        self.w3: Web3 = tx_manager.w3
        self.receiver_address = Web3.to_checksum_address(receiver_address)
        self.receiver_contract: Contract = self.w3.eth.contract(
            address=self.receiver_address, abi=RECEIVER_ABI
        )
        log.info(
            "FLASHLOAN_ADAPTER_INITIALIZED",
            receiver_address=self.receiver_address
        )

    def _check_kill_switch(self):
        """BIBLE ENFORCEMENT: Safety check before initiating a massive capital movement."""
        try:
            check()
        except KillSwitchActiveError:
            raise TransactionKillSwitchError("Flash loan blocked by system kill switch.")

    def initiate_flashloan(
        self,
        loan_assets: List[str],
        loan_amounts: List[int],
        encoded_action_calldata: bytes
    ) -> str:
        """
        Builds and sends the transaction to initiate the flash loan.

        Args:
            loan_assets: A list of token addresses to borrow.
            loan_amounts: A list of amounts (in wei) for each token.
            encoded_action_calldata: The ABI-encoded calldata for the operations
                                     the FlashloanReceiver contract should execute.

        Returns:
            The transaction hash of the flash loan initiation.
        """
        self._check_kill_switch()

        log.info(
            "FLASHLOAN_INITIATED",
            assets=loan_assets,
            amounts=loan_amounts,
            receiver=self.receiver_address,
        )

        # Build the transaction to call `initiateFlashloan` on our receiver contract.
        tx_params = self.receiver_contract.functions.initiateFlashloan(
            loan_assets,
            loan_amounts,
            encoded_action_calldata
        ).build_transaction({
            'from': self.tx_manager.address,
            'nonce': self.tx_manager.nonce,
        })

        return self.tx_manager.build_and_send_transaction(tx_params)

    def encode_action_chain(self, targets: List[str], calldatas: List[bytes]) -> bytes:
        """
        A helper function to encode a chain of actions into the `params` format
        that our simple FlashloanReceiver understands.
        
        This is a basic implementation. A more advanced one might handle dependencies
        between calls.
        
        Args:
            targets: List of contract addresses to call (e.g., Uniswap Router).
            calldatas: List of encoded calldata for each call.
            
        Returns:
            A single bytes payload to be passed as `params` to the flash loan.
        """
        # For our simple contract, we can just concatenate the calls.
        # This implementation requires a more sophisticated receiver that can loop
        # through and decode multiple calls.
        # For now, we will focus on encoding a SINGLE action.
        if len(targets) != 1 or len(calldatas) != 1:
            raise NotImplementedError("This helper currently supports only a single action.")

        # This encodes the call to `FlashloanReceiver.executeCall(target, data)`
        return self.receiver_contract.functions.executeCall(targets[0], calldatas[0])._encode_transaction_data()
