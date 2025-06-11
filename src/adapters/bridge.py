# /src/adapters/bridge.py - HARDENED with explicit destination address and native gas
from web3 import Web3
from web3.contract import Contract
from merkletools import MerkleTools
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature

from src.core.tx import TransactionManager, TransactionKillSwitchError
from src.core.kill import is_kill_switch_active
from src.core.logger import get_logger

STARGATE_ROUTER_ABI = [{"inputs":[{"internalType":"uint16","name":"_dstChainId","type":"uint16"},{"internalType":"uint256","name":"_srcPoolId","type":"uint256"},{"internalType":"uint256","name":"_dstPoolId","type":"uint256"},{"internalType":"address","name":"_refundAddress","type":"address"},{"internalType":"uint256","name":"_amountLD","type":"uint256"},{"internalType":"uint256","name":"_minAmountLD","type":"uint256"},{"components":[{"internalType":"uint256","name":"dstGasForCall","type":"uint256"},{"internalType":"uint256","name":"dstNativeAmount","type":"uint256"},{"internalType":"bytes","name":"dstNativeAddr","type":"bytes"}],"internalType":"struct IStargateRouter.lzTxObj","name":"_lzTxParams","type":"tuple"},{"internalType":"bytes","name":"_to","type":"bytes"},{"internalType":"bytes","name":"_payload","type":"bytes"}],"name":"swap","outputs":[],"stateMutability":"payable","type":"function"}]
log = get_logger(__name__)

class StargateBridgeAdapter:
    def __init__(self, tx_manager: TransactionManager, router_address: str):
        self.tx_manager = tx_manager
        self.w3: Web3 = tx_manager.w3
        self.router_address = Web3.to_checksum_address(router_address)
        self.router_contract: Contract = self.w3.eth.contract(address=self.router_address, abi=STARGATE_ROUTER_ABI)
        self.mt = MerkleTools(hash_type="keccak")

    def _check_kill_switch(self):
        if is_kill_switch_active():
            raise TransactionKillSwitchError("Bridge action blocked by kill switch.")

    def bridge_asset(
        self,
        dest_chain_id: int,
        source_pool_id: int,
        dest_pool_id: int,
        amount_ld: int,
        min_amount_ld: int,
        to_address: str,         
        refund_address: str,     
        native_gas_amount: int   
    ) -> str:
        self._check_kill_switch()
        log.warning("BRIDGE_TRANSFER_INITIATED", to_chain=dest_chain_id, to_address=to_address, amount=amount_ld)

        lz_tx_params = {
            "dstGasForCall": 0,
            "dstNativeAmount": native_gas_amount,
            "dstNativeAddr": Web3.to_bytes(hexstr=to_address)
        }

        tx_params = self.router_contract.functions.swap(
            dest_chain_id,
            source_pool_id,
            dest_pool_id,
            Web3.to_checksum_address(refund_address),
            amount_ld,
            min_amount_ld,
            lz_tx_params,
            Web3.to_bytes(hexstr=to_address), 
            b''
        ).build_transaction({
            'from': self.tx_manager.address,
            'nonce': self.tx_manager.nonce,
            'value': native_gas_amount
        })

        tx_hash = self.tx_manager.build_and_send_transaction(tx_params)
        return tx_hash

    def verify_bridge_event(self, root: str, leaf: str, proof: list[str], relayer_sig: str | None = None, relayer_pubkey_pem: str | None = None) -> bool:
        if proof:
            if not self.mt.validate_proof(proof, leaf, root):
                raise ValueError("Invalid Merkle proof")
        elif relayer_sig and relayer_pubkey_pem:
            pubkey = serialization.load_pem_public_key(relayer_pubkey_pem.encode())
            try:
                pubkey.verify(bytes.fromhex(relayer_sig), leaf.encode(), ec.ECDSA(hashes.SHA256()))
            except InvalidSignature:
                raise ValueError("Invalid relayer signature")
        else:
            raise ValueError("No proof or attestation provided")
        log.info("BRIDGE_EVENT_VERIFIED", leaf=leaf)
        return True
