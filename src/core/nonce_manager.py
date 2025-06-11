# /src/core/nonce_manager.py

import os, fcntl, aiofiles
from web3 import Web3
from src.core.config import settings
from src.core.logger import get_logger

log = get_logger(__name__)
NONCE_FILE = os.path.join(settings.SESSION_DIR, "nonce.lock")

class NonceManager:
    def __init__(self, w3: Web3, address: str):
        self.w3 = w3
        self.address = address
        os.makedirs(settings.SESSION_DIR, exist_ok=True)
        self._fd = None
        self.nonce = -1

    async def initialize(self):
        self._fd = open(NONCE_FILE, "a+")
        fcntl.flock(self._fd, fcntl.LOCK_EX)
        self._fd.seek(0)
        data = self._fd.read().strip()
        if data.isdigit():
            self.nonce = int(data)
            log.info("NONCE_LOADED", nonce=self.nonce)
        else:
            self.nonce = await self.w3.eth.get_transaction_count(self.address)
            log.info("NONCE_FROM_RPC", nonce=self.nonce)
            await self._write()
        return self.nonce

    async def get(self) -> int:
        return self.nonce

    async def bump(self):
        self.nonce += 1
        await self._write()
        log.debug("NONCE_BUMPED", nonce=self.nonce)

    async def _write(self):
        self._fd.seek(0)
        self._fd.truncate()
        self._fd.write(str(self.nonce))
        self._fd.flush()

    def close(self):
        if self._fd:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            self._fd.close()
            log.info("NONCE_LOCK_RELEASED")
