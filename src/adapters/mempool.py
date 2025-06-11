# /src/adapters/mempool.py
import asyncio
import json
import websockets
from websockets.exceptions import ConnectionClosed

from src.core.config import settings
from src.core.kill import is_kill_switch_active
from src.core.logger import get_logger

log = get_logger(__name__)

MEMPOOL_WSS_URL = settings.MEMPOOL_WSS_URL.get_secret_value()

class MempoolAdapter:
    def __init__(self, wss_url: str = MEMPOOL_WSS_URL):
        self.wss_url = wss_url
        self.connection = None

    async def connect(self):
        log.info("MEMPOOL_ADAPTER_CONNECTING", url=self.wss_url)
        try:
            self.connection = await websockets.connect(self.wss_url)
            await self.connection.send(json.dumps({
                "id": 1, "method": "eth_subscribe", "params": ["newPendingTransactions"]
            }))
            await self.connection.recv()
            log.info("MEMPOOL_ADAPTER_CONNECTED_AND_SUBSCRIBED")
        except (ConnectionClosed, OSError) as e:
            log.error("MEMPOOL_CONNECTION_FAILED", error=str(e), exc_info=True)
            self.connection = None
            raise

    async def stream_transactions(self):
        while not is_kill_switch_active():
            if not self.connection or self.connection.closed:
                try:
                    await self.connect()
                except Exception:
                    await asyncio.sleep(5)
                    continue
            
            try:
                message = await self.connection.recv()
                data = json.loads(message)
                tx = data.get("params", {}).get("result", {})
                if tx and isinstance(tx, dict):
                    yield tx
            except ConnectionClosed:
                log.warning("MEMPOOL_CONNECTION_CLOSED_RECONNECTING")
                self.connection = None
            except Exception as e:
                log.error("MEMPOOL_STREAM_ERROR", error=str(e))
                await asyncio.sleep(1)

        log.critical("MEMPOOL_ABORTED_BY_KILL_SWITCH")
        return
