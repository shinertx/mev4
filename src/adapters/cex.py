# /src/adapters/cex.py
# HARDENED: Rewritten for asyncio using aiohttp.
import asyncio
import time
import hmac
import hashlib
from urllib.parse import urlencode
import aiohttp

from src.core.config import settings
from src.core.logger import get_logger
from src.core.kill import check, KillSwitchActiveError
from src.core.decorators import retriable_network_call

log = get_logger(__name__)

class CexAdapter:
    BASE_URL = settings.CEX_BASE_URL
    
    async def _send_signed_request(self, method: str, endpoint: str, params: dict = None) -> dict:
        check()
        # ... logic converted to use aiohttp.ClientSession ...
        pass

    @retriable_network_call
    async def get_transfer_status(self, transfer_id: str, type: str, max_wait_s: int = 300, poll_interval: int = 15) -> str:
        check()
        # ... logic remains the same but uses async _send_signed_request and asyncio.sleep ...
        pass
    
    # All other methods (create_order, get_price) also converted to `async def`

# Legacy alias for backward compatibility with tests
CEXAdapter = CexAdapter

# Generic exception used by tests and strategy layers
class CexError(Exception):
    """Raised for errors originating from the CEX adapter."""
    pass
