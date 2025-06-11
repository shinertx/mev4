import asyncio
import os
import pytest

from src.core.tx import TransactionManager
from src.core.nonce_manager import NonceManager
from src.core.config import settings

class DummyEth:
    async def estimate_gas(self, _):
        return 21000
    async def send_raw_transaction(self, _):
        return b'hash'
    async def gas_price(self):
        return 1
    async def max_priority_fee(self):
        return 1
    async def get_transaction_count(self, _):
        return 0
    class account:
        @staticmethod
        def sign_transaction(tx, key):
            return type('S', (), {'rawTransaction': b'raw'})()

class DummyW3:
    def __init__(self):
        self.eth = DummyEth()

class DummyLock:
    def __init__(self):
        self._lock = asyncio.Lock()
    async def __aenter__(self):
        await self._lock.acquire()
    async def __aexit__(self, exc_type, exc, tb):
        self._lock.release()

class DummyRedis:
    def lock(self, name, timeout=10):
        return DummyLock()
    async def close(self):
        pass

@pytest.mark.asyncio
async def test_nonce_collision_handled(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'SESSION_DIR', str(tmp_path))
    tm = TransactionManager()
    tm.w3 = DummyW3()
    tm.account = type('A', (), {'key': '0x0'})()
    tm.address = '0xabc'
    tm.nonce_manager = NonceManager(tm.w3, tm.address)
    tm.redis = DummyRedis()
    await tm.nonce_manager.initialize()

    async def send():
        await tm.build_and_send_transaction({'to': '0x1'})

    await asyncio.gather(send(), send())
    assert await tm.nonce_manager.get() == 2
