# /src/core/resilient_rpc.py
# New module to provide a resilient, multi-node Web3 provider.

from collections import Counter
from web3 import Web3
# --- POA middleware import across Web3 versions ---
try:
    # Web3 < 7 (and eth-account <0.9) ships the helper here
    from web3.middleware import geth_poa_middleware  # type: ignore
except ImportError:
    try:
        # Web3 6.x exposes it via eth_account
        from eth_account.middleware import construct_poa_middleware as geth_poa_middleware  # type: ignore
    except ImportError:
        # Web3 7.x removed the helper entirely – use a no-op shim so code continues to run
        def geth_poa_middleware(make_request, web3):  # type: ignore
            return make_request
from src.core.config import settings
from src.core.logger import get_logger
from src.core.decorators import retriable_network_call

log = get_logger(__name__)

def get_rpc_urls_from_env():
    """Dynamically finds all ETH_RPC_URL_n variables from settings."""
    urls = [getattr(settings, 'ETH_RPC_URL_1', None)]
    i = 2
    while (url := getattr(settings, f'ETH_RPC_URL_{i}', None)):
        urls.append(url)
        i += 1
    return [u.get_secret_value() for u in urls if u]

class ResilientWeb3Provider:
    def __init__(self):
        self.rpc_urls = get_rpc_urls_from_env()
        if len(self.rpc_urls) < 2:
            log.warning("RESILIENCE_DEGRADED_LT_2_RPCS", count=len(self.rpc_urls))
        
        self.providers = []
        for url in self.rpc_urls:
            provider = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 10}))
            provider.middleware_onion.inject(geth_poa_middleware, layer=0)
            if provider.is_connected():
                self.providers.append(provider)
        
        if not self.providers:
            raise ConnectionError("All RPC nodes are unreachable.")
        self.primary_provider = self.providers[0]
        log.info("RESILIENT_WEB3_PROVIDER_INITIALIZED", rpc_count=len(self.providers))

    def get_primary_provider(self) -> Web3:
        """Returns the primary provider, used for sending transactions."""
        return self.primary_provider

    @retriable_network_call
    def call_consensus(self, contract_address: str, contract_abi: list, function_name: str, *args):
        results = []
        for provider in self.providers:
            try:
                provider_contract = provider.eth.contract(address=contract_address, abi=contract_abi)
                func = getattr(provider_contract.functions, function_name)
                result = func(*args).call()
                results.append(result)
            except Exception as e:
                log.error("RPC_CONSENSUS_CALL_FAILED", url=provider.provider.endpoint_uri, error=str(e))
                continue
        
        if not results:
            raise Exception("Consensus call failed on all RPC nodes.")
            
        consensus = Counter(tuple(r) if isinstance(r, list) else r for r in results).most_common(1)[0]
        result, count = consensus
        
        if count <= len(results) / 2:
            raise Exception(f"Consensus failed: No majority result. Results: {results}")
            
        log.debug("RPC_CONSENSUS_SUCCESS", result=result, count=count, total=len(results))
        return result
