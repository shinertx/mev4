# /src/core/config.py
import os
from pydantic import BaseSettings, SecretStr, AnyUrl
from src.core.logger import log

# This is the simplified settings loader. If using Vault, the more complex
# load_settings() function from the previous audit fix would be used here.
class Settings(BaseSettings):
    # Core Executor
    EXECUTOR_PRIVATE_KEY: SecretStr

    # RPC & Mempool Endpoints
    ETH_RPC_URL_1: SecretStr
    ETH_RPC_URL_2: SecretStr | None = None
    ETH_RPC_URL_3: SecretStr | None = None
    MEMPOOL_WSS_URL: SecretStr

    # External Service Keys
    OPENAI_API_KEY: SecretStr | None = None
    BINANCE_API_KEY: SecretStr | None = None
    BINANCE_API_SECRET: SecretStr | None = None
    SENTRY_DSN: AnyUrl | None = None

    # Operational Settings
    LOG_LEVEL: str = "INFO"
    HEALTH_PORT: int = 8080
    SESSION_DIR: str = "/tmp/mev_og_session" # For durable state files

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

try:
    settings = Settings()
except Exception as e:
    log.critical("FAILED_TO_LOAD_SETTINGS", error=str(e))
    # In a container, a hard exit is often appropriate if config fails.
    exit(1)
