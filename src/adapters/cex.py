# /src/adapters/cex.py - HARDENED with transfer status polling and retries.
import time
import hmac
import hashlib
from urllib.parse import urlencode
import requests

from decimal import Decimal
from src.core.decorators import retriable_network_call
from src.core.tx import TransactionKillSwitchError
from src.core.config import settings
from src.core.kill import is_kill_switch_active
from src.core.logger import get_logger

log = get_logger(__name__)

class CexError(Exception): pass
class CexOrderError(CexError): pass

class CexAdapter:
    BASE_URL = "https://api.binance.com"

    def __init__(self):
        self.api_key = settings.BINANCE_API_KEY.get_secret_value() if settings.BINANCE_API_KEY else None
        self.api_secret = settings.BINANCE_API_SECRET.get_secret_value() if settings.BINANCE_API_SECRET else None
        if not self.api_key or not self.api_secret:
            log.warning("CEX_ADAPTER_INITIALIZED_WITHOUT_CREDS", CEX="Binance")

    def _check_kill_switch(self):
        if is_kill_switch_active():
            raise TransactionKillSwitchError("CEX action blocked by system kill switch.")

    def _send_signed_request(self, method: str, endpoint: str, params: dict = None) -> dict:
        self._check_kill_switch()
        if params is None: params = {}
        params['timestamp'] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(self.api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        params['signature'] = signature
        headers = {'X-MBX-APIKEY': self.api_key}
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.request(method, url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    @retriable_network_call
    def get_deposit_address(self, asset: str, network: str) -> str:
        endpoint = "/sapi/v1/capital/deposit/address"
        params = {"coin": asset, "network": network}
        try:
            response = self._send_signed_request('GET', endpoint, params)
            address = response['address']
            log.info("CEX_DEPOSIT_ADDRESS_FETCHED", asset=asset, network=network)
            return address
        except Exception as e:
            raise CexError(f"Failed to get deposit address for {asset}: {e}") from e

    @retriable_network_call
    def get_transfer_status(self, transfer_id: str, type: str, max_wait_s: int = 300, poll_interval: int = 15) -> str:
        deadline = time.time() + max_wait_s
        endpoint = {"withdraw": "/sapi/v1/capital/withdraw/history", "deposit":  "/sapi/v1/capital/deposit/hisrec"}[type]
        while time.time() < deadline:
            resp = self._send_signed_request('GET', endpoint, {})
            record = next((r for r in resp if str(r.get("txId", r.get("id"))) == transfer_id), None)
            if record:
                status = record.get("status")
                log.debug("CEX_TRANSFER_STATUS_POLL", id=transfer_id, type=type, status=status)
                if (type == "withdraw" and status == 6) or (type == "deposit" and status == 1): return "SUCCESS"
                if status in {3, 5}: return "FAILED"
            time.sleep(poll_interval)
        log.error("CEX_TRANSFER_STATUS_TIMEOUT", id=transfer_id, type=type)
        return "TIMEOUT"

    def withdraw(self, asset: str, address: str, amount: float, network: str) -> str:
        # ... implementation from previous response
        pass
