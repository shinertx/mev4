# /src/core/config.py
import os
from pydantic_settings import BaseSettings
from pydantic import SecretStr
from typing import List

# This is the simplified settings loader. If using Vault, the more complex
# load_settings() function from the previous audit fix would be used here.
class Settings(BaseSettings):
    # Core Executor
    EXECUTOR_PRIVATE_KEY: SecretStr | None = SecretStr("0x00")

    # RPC & Mempool Endpoints
    # Deprecated ETH_RPC_URL_* in favor of rpc_urls
    ETH_RPC_URL_1: SecretStr | None = None
    ETH_RPC_URL_2: SecretStr | None = None
    ETH_RPC_URL_3: SecretStr | None = None
    rpc_urls: List[str] = []
    MEMPOOL_WSS_URL: SecretStr | None = SecretStr("wss://dummy.local")

    # Chain configuration
    chain_id: int = 1

    LOG_SIGNING_KEY: SecretStr | None = None

    # External Service Keys
    OPENAI_API_KEY: SecretStr | None = None
    BINANCE_API_KEY: SecretStr | None = None
    BINANCE_API_SECRET: SecretStr | None = None
    SENTRY_DSN: str | None = None
    AI_MODEL_API_URL: str = "https://api.openai.com/v1/chat/completions"
    CEX_BASE_URL: str = "https://api.binance.com"

    # Operational Settings
    LOG_LEVEL: str = "INFO"
    HEALTH_PORT: int = 8080
    SESSION_DIR: str = "/tmp/mev_og_session" # For durable state files
    REDIS_URL: str = "redis://localhost:6379/0"
    MANUAL_APPROVAL: bool = False
    CONTROL_API_TOKEN: str | None = None
    MUTATION_TTL_SECONDS: int = 3600

    # GCP (optional)
    GCP_PROJECT_ID: str | None = None
    GCP_REGION: str | None = None

    # -------------------------------------------------
    # Backwards-compatibility shims
    # -------------------------------------------------

    @property
    def ETH_RPC_URL(self) -> str | None:  # noqa: N802 (legacy name)
        """Primary RPC URL retained for tests that still expect a single
        endpoint named *ETH_RPC_URL*.

        Preference order:

        1. Explicit *ETH_RPC_URL_1* env var / field
        2. First entry in *rpc_urls*
        3. ``None`` if neither is configured
        """
        if self.ETH_RPC_URL_1 is not None:
            return self.ETH_RPC_URL_1.get_secret_value() if isinstance(self.ETH_RPC_URL_1, SecretStr) else str(self.ETH_RPC_URL_1)  # type: ignore[arg-type]
        if self.rpc_urls:
            return self.rpc_urls[0]
        return None

    @ETH_RPC_URL.setter  # type: ignore[override]
    def ETH_RPC_URL(self, value: str | None):  # noqa: N802
        """Allow test suites to overwrite the legacy *ETH_RPC_URL* attribute.

        The value is propagated to *ETH_RPC_URL_1* for consistency.
        """
        if value is None:
            self.ETH_RPC_URL_1 = None  # type: ignore[assignment]
        else:
            # Store as SecretStr to keep types consistent with original field.
            from pydantic import SecretStr

            self.ETH_RPC_URL_1 = SecretStr(value)  # type: ignore[assignment]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

try:
    settings = Settings()
except Exception as e:
    # Late import to avoid circular dependency only for logging the failure
    try:
        from src.core.logger import get_logger, configure_logging
        configure_logging()
        log = get_logger("MEV-OG.Config")
        log.critical("FAILED_TO_LOAD_SETTINGS", error=str(e))
    except Exception:
        print("FAILED_TO_LOAD_SETTINGS", e)
    # In a container, a hard exit is often appropriate if config fails.
    exit(1)
