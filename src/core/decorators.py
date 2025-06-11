# /src/core/decorators.py
# Reusable decorators for operational resilience.
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log
from src.core.logger import get_logger
import logging

log = get_logger(__name__)

# Define a generic retry decorator for network calls
retriable_network_call = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    before_sleep=before_sleep_log(log, logging.WARNING),
    reraise=True # Re-raise the last exception after retries are exhausted
)
