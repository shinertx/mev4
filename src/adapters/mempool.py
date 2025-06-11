# /src/adapters/mempool.py
import asyncio
import json
import websockets
from websockets.exceptions import ConnectionClosed

from src.core.config import settings
from src.core.kill import check, KillSwitchActiveError
from src.core.logger import get_logger

log = get_logger(__name__)

MEMPOOL_WSS_URLS = [u.strip() for u in settings.MEMPOOL_WSS_URL.get_secret_value().split(',')]

class MempoolAdapter:
    def __init__(self, wss_urls: list[str] = MEMPOOL_WSS_URLS):
        self.wss_urls = wss_urls
        self.idx = 0
        self.connection = None
        self.stall_timeout = 0.5  # 500ms stall detection

    async def connect(self):
        check()
        url = self.wss_urls[self.idx]
        log.info("MEMPOOL_ADAPTER_CONNECTING", url=url)
        try:
            self.connection = await websockets.connect(url)
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
        while True:
            try:
                check()
            except KillSwitchActiveError:
                log.critical("MEMPOOL_ABORTED_BY_KILL_SWITCH")
                break
            if not self.connection or self.connection.closed:
                try:
                    await self.connect()
                except Exception:
                    await asyncio.sleep(5)
                    self.idx = (self.idx + 1) % len(self.wss_urls)
                    continue

            try:
                message = await asyncio.wait_for(self.connection.recv(), timeout=self.stall_timeout)
                data = json.loads(message)
                tx = data.get("params", {}).get("result", {})
                if tx and isinstance(tx, dict):
                    yield tx
            except asyncio.TimeoutError:
                log.warning("MEMPOOL_FEED_STALLED", url=self.wss_urls[self.idx])
                self.idx = (self.idx + 1) % len(self.wss_urls)
                self.connection = None
            except ConnectionClosed:
                log.warning("MEMPOOL_CONNECTION_CLOSED_RECONNECTING")
                self.connection = None
            except Exception as e:
                log.error("MEMPOOL_STREAM_ERROR", error=str(e))
                await asyncio.sleep(1)

        return
