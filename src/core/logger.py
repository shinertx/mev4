# /src/core/logger.py
import logging
import structlog
from structlog.contextvars import bind_contextvars
import sentry_sdk
from prometheus_client import Counter
from src.core.config import settings
import json
import hmac
import hashlib
import os

# --- Prometheus Metrics ---
TRADES_EXECUTED = Counter("mev_og_trades_executed_total", "Total number of trades executed", ["strategy"])
SNAPSHOTS_TAKEN = Counter("mev_og_snapshots_taken_total", "Total number of DRP snapshots taken")
ERRORS_LOGGED = Counter("mev_og_errors_logged_total", "Total number of errors logged", ["level"])
KILL_TRIGGERED = Counter("kill_triggered_total", "Times the kill switch has halted execution")
MUTATION_ATTEMPT = Counter("mutation_attempt_total", "Total mutation attempts")
MUTATION_APPROVED = Counter("mutation_approved_total", "Total mutations approved")
MUTATION_REVERTED = Counter("mutation_reverted_total", "Total mutations reverted via DRP")

SIGNING_KEY = (settings.LOG_SIGNING_KEY.get_secret_value().encode()
               if settings.LOG_SIGNING_KEY else b"insecure")
AUDIT_FILE = os.path.join(settings.SESSION_DIR, "audit.log")

def sign_and_append(event_dict: dict) -> dict:
    payload = json.dumps(event_dict, sort_keys=True)
    sig = hmac.new(SIGNING_KEY, payload.encode(), hashlib.sha256).hexdigest()
    with open(AUDIT_FILE, "a") as f:
        f.write(payload + "|" + sig + "\n")
    event_dict["signature"] = sig
    return event_dict

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
            sign_and_append,
            structlog.processors.JSONRenderer(), # Production-ready JSON logs
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.LOG_LEVEL)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str):
    return structlog.get_logger(name)

def set_cycle_counter(counter: int):
    bind_contextvars(cycle_counter=counter)

configure_logging()
log = get_logger("MEV-OG.System")
