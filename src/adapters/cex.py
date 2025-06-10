# /src/adapters/cex.py
# Aligns with PROJECT_BIBLE.md: Section 2, 3, 5
# - Modular CEX adapter (Binance implementation).
# - Must check kill-switch before any capital move or external call.
# - All secrets/config from core.config.

import time
import hmac
import hashlib
from urllib.parse import urlencode

import requests
from requests import Response

from src.core.config import settings
from src.core.kill import is_kill_switch_active, TransactionKillSwitchError
from src.core.logger import get_logger

log = get_logger(__name__)

# --- Custom Exception for CEX operations ---
class CexError(Exception):
    """Base exception for CEX adapter errors."""
    pass

class CexOrderError(CexError):
    """Raised when an order placement or check fails."""
    pass


class CexAdapter:
    """
    A modular adapter for interacting with the Binance CEX.
    Handles API authentication, request signing, and provides methods
    for trading and account management.
    """
    BASE_URL = "https://api.binance.com"

    def __init__(self):
        self.api_key = settings.BINANCE_API_KEY.get_secret_value() if settings.BINANCE_API_KEY else None
        self.api_secret = settings.BINANCE_API_SECRET.get_secret_value() if settings.BINANCE_API_SECRET else None

        if not self.api_key or not self.api_secret:
            log.warning("CEX_ADAPTER_INITIALIZED_WITHOUT_CREDS", CEX="Binance")
        else:
            log.info("CEX_ADAPTER_INITIALIZED", CEX="Binance")

    def _check_kill_switch(self):
        """BIBLE ENFORCEMENT: Internal safety check before any action."""
        if is_kill_switch_active():
            raise TransactionKillSwitchError("CEX action blocked by system kill switch.")

    def _send_signed_request(self, method: str, endpoint: str, params: dict = None) -> dict:
        """Sends a signed request to the Binance API."""
        self._check_kill_switch()
        if not self.api_key or not self.api_secret:
            raise CexError("Cannot send signed request without API key and secret.")

        if params is None:
            params = {}
        
        # Add timestamp and create signature
        params['timestamp'] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(self.api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        params['signature'] = signature

        headers = {'X-MBX-APIKEY': self.api_key}
        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = requests.request(method, url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            log.error("CEX_REQUEST_FAILED", endpoint=endpoint, error=str(e), response_text=e.response.text if e.response else "N/A")
            raise CexError(f"Request to {endpoint} failed: {e}") from e

    def get_price(self, symbol: str) -> float:
        """
        Gets the latest price for a trading symbol (e.g., 'ETHUSDT').
        This is a public endpoint and does not require signing.
        """
        self._check_kill_switch()
        endpoint = "/api/v3/ticker/price"
        try:
            response = requests.get(f"{self.BASE_URL}{endpoint}", params={"symbol": symbol})
            response.raise_for_status()
            data = response.json()
            return float(data['price'])
        except requests.exceptions.RequestException as e:
            log.error("CEX_GET_PRICE_FAILED", symbol=symbol, error=str(e))
            raise CexError(f"Failed to get price for {symbol}: {e}") from e

    def create_order(self, symbol: str, side: str, order_type: str, quantity: float) -> dict:
        """
        Places an order on Binance.

        Args:
            symbol: e.g., 'ETHUSDT'
            side: 'BUY' or 'SELL'
            order_type: 'MARKET', 'LIMIT', etc.
            quantity: The amount of the base asset to buy/sell.

        Returns:
            The API response from Binance as a dictionary.
        """
        self._check_kill_switch() # CRITICAL: Check before placing a capital-moving order.
        log.info("CEX_CREATE_ORDER_ATTEMPT", symbol=symbol, side=side, type=order_type, quantity=quantity)

        endpoint = "/api/v3/order"
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': f"{quantity:.8f}", # Format quantity to required precision
        }
        
        try:
            order_response = self._send_signed_request('POST', endpoint, params)
            log.info("CEX_ORDER_CREATED_SUCCESSFULLY", order_id=order_response.get('orderId'), response=order_response)
            return order_response
        except CexError as e:
            # Re-raise with a more specific exception type
            raise CexOrderError(f"Failed to create order for {symbol}: {e}") from e
