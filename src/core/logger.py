# /src/core/logger.py
import logging
import structlog
import sentry_sdk
from prometheus_client import Counter
from src.core.config import settings

# --- Prometheus Metrics ---
TRADES_EXECUTED = Counter("mev_og_trades_executed_total", "Total number of trades executed", ["strategy"])
SNAPSHOTS_TAKEN = Counter("mev_og_snapshots_taken_total", "Total number of DRP snapshots taken")
ERRORS_LOGGED = Counter("mev_og_errors_logged_total", "Total number of errors logged", ["level"])

def configure_logging():
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN.get_secret_value(), traces_sample_rate=1.0)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(), # Production-ready JSON logs
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.LOG_LEVEL)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str):
    return structlog.get_logger(name)

configure_logging()
log = get_logger("MEV-OG.System")
