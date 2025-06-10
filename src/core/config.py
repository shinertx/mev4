# /src/core/config.py
# Aligns with PROJECT_BIBLE.md: Section 3 & 4
# - All secrets/config from .env or GCP Secret Manager
# - Central config loader with validation

import os
from pydantic import BaseSettings, SecretStr, AnyUrl

class Settings(BaseSettings):
    """
    Central configuration for the system, loaded from environment variables.
    Pydantic ensures that all required variables are present and valid at startup.
    """
    # General
    LOG_LEVEL: str = "INFO"

    # Blockchain
    EXECUTOR_PRIVATE_KEY: SecretStr
    ETH_RPC_URL: AnyUrl

    # CEX Adapters
    BINANCE_API_KEY: SecretStr | None = None
    BINANCE_API_SECRET: SecretStr | None = None

    # GCP
    GCP_PROJECT_ID: str | None = None
    GCP_REGION: str | None = None
    
    # Monitoring
    SENTRY_DSN: AnyUrl | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Instantiate the settings once. This object will be imported by other modules.
# This is a configuration object, not a mutable state object, and is therefore
# compliant with the "NO global/singleton state" rule for capital/session state.
settings = Settings()
