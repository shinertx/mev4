from decimal import Decimal
from statistics import mean, pstdev
from typing import List
from src.core.state import State
from src.strategies.base import AbstractStrategy
from src.core.logger import get_logger

log = get_logger(__name__)

MIN = Decimal('0')
MAX = Decimal('1000000')

class IntentMEVStrategy(AbstractStrategy):
    """Example strategy demonstrating ML parameter sanitization."""

    def __init__(self, historical: List[Decimal]):
        self.historical = historical if historical else [Decimal('0')]

    def _validate_param(self, param: Decimal):
        mu = mean(self.historical)
        sigma = pstdev(self.historical) or Decimal('1')
        if not (MIN <= param <= MAX):
            raise ValueError("Parameter out of safe bounds")
        if abs(param - mu) / sigma > 3:
            raise ValueError("Parameter outlier")

    async def run(self, state: State, adapters: dict, config: dict) -> State:
        param = config.get('ml_param', Decimal('0'))
        self._validate_param(Decimal(str(param)))
        log.info('INTENT_MEV_PARAM_ACCEPTED', value=float(param))
        return state

    async def abort(self, reason: str):
        log.critical('INTENT_MEV_ABORTED', reason=reason)
