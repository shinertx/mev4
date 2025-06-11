# /src/abis/uniswap_v2.py
UNISWAP_V2_ROUTER_ABI = [
    {"inputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}], "name": "getAmountsOut", "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}, {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}, {"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "deadline", "type": "uint256"}], "name": "swapExactTokensForTokens", "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}], "stateMutability": "nonpayable", "type": "function"}
]
```---
#### **2. NEW Supporting File: Durable Nonce Manager (`/src/core/nonce_manager.py`)**
*Fixes: `Durable nonce persistence` and `Cross-process lock` from audit.*

**File: `/src/core/nonce_manager.py`**```python
# /src/core/nonce_manager.py
# NEW MODULE: Handles durable, file-based, cross-process nonce management.

import os
import fcntl
import asyncio
import aiofiles
from web3 import Web3

from src.core.config import settings
from src.core.logger import get_logger

log = get_logger(__name__)

NONCE_FILE_PATH = os.path.join(settings.SESSION_DIR, "nonce.lock")

class NonceManager:
    """
    Provides durable, cross-process-safe nonce management using a lockfile.
    """
    def __init__(self, w3: Web3, address: str):
        self.w3 = w3
        self.address = address
        self.nonce = -1
        self._lock_file = None
        os.makedirs(settings.SESSION_DIR, exist_ok=True)

    async def initialize(self):
        """Acquires a file lock and initializes the nonce from file or RPC."""
        self._lock_file = open(NONCE_FILE_PATH, 'w')
        try:
            fcntl.flock(self._lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            log.critical("NONCE_MANAGER_COULD_NOT_ACQUIRE_LOCK", path=NONCE_FILE_PATH)
            raise Exception("Could not acquire nonce lock file. Another process may be running.")

        try:
            async with aiofiles.open(NONCE_FILE_PATH, "r") as f:
                content = await f.read()
                self.nonce = int(content)
                log.info("NONCE_LOADED_FROM_FILE", nonce=self.nonce, path=NONCE_FILE_PATH)
        except (FileNotFoundError, ValueError):
            self.nonce = await self.w3.eth.get_transaction_count(self.address)
            log.warning("NONCE_INITIALIZED_FROM_RPC", nonce=self.nonce)
            await self._write_nonce()
            
    async def get_nonce(self) -> int:
        """Returns the current nonce."""
        return self.nonce

    async def increment(self):
        """Increments the nonce and persists it to the lockfile."""
        self.nonce += 1
        await self._write_nonce()
        log.debug("NONCE_INCREMENTED", new_nonce=self.nonce)

    async def _write_nonce(self):
        """Writes the current nonce value to the file."""
        self._lock_file.seek(0)
        self._lock_file.truncate()
        self._lock_file.write(str(self.nonce))
        self._lock_file.flush()

    def close(self):
        """Releases the file lock."""
        if self._lock_file:
            fcntl.flock(self._lock_file, fcntl.LOCK_UN)
            self._lock_file.close()
            log.info("NONCE_MANAGER_LOCK_RELEASED")
