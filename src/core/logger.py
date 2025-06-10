# /src/core/logger.py
# Aligns with PROJECT_BIBLE.md: Section 3
# - Structured logging for every trade, state change, kill, error.
# - Emits machine-readable logs with timestamps.

import logging
import sys
import structlog
from src.core.config import settings

# --- Structlog Configuration ---
# This setup ensures that logs are structured as JSON for production environments
# and are human-readable in local development.

# Mute noisy loggers from libraries
logging.getLogger("web3").setLevel(logging.INFO)
logging.getLogger("urllib3").setLevel(logging.INFO)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.LOG_LEVEL)),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

# A simple function to get a logger instance for any module
def get_logger(name: str):
    """Returns a configured structlog logger instance."""
    return structlog.get_logger(name)

# Example of a root logger for system-level events
log = get_logger("MEV-OG.System")
