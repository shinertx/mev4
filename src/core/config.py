# /src/core/config.py - HARDENED with Vault integration
import os
import hvac
from pydantic import BaseSettings, SecretStr, AnyUrl
from src.core.logger import get_logger

log = get_logger(__name__)

def get_secret_from_vault(secret_path: str, secret_key: str) -> str | None:
    vault_addr = os.getenv("VAULT_ADDR")
    vault_token = os.getenv("VAULT_TOKEN")
    
    if not vault_addr or not vault_token:
        return None
        
    try:
        client = hvac.Client(url=vault_addr, token=vault_token)
        if not client.is_authenticated():
            log.error("VAULT_AUTHENTICATION_FAILED")
            return None
        
        response = client.secrets.kv.v2.read_secret_version(path=secret_path)
        return response['data']['data'][secret_key]
    except Exception as e:
        log.error("VAULT_SECRET_FETCH_FAILED", path=secret_path, key=secret_key, error=str(e))
        return None

class Settings(BaseSettings):
    VAULT_EXECUTOR_PATH: str = "kv/mev-og/executor"
    VAULT_EXECUTOR_KEY: str = "privateKey"
    
    EXECUTOR_PRIVATE_KEY: SecretStr | None = None
    
    LOG_LEVEL: str = "INFO"
    ETH_RPC_URL_1: SecretStr
    ETH_RPC_URL_2: SecretStr | None = None
    ETH_RPC_URL_3: SecretStr | None = None
    GCP_PROJECT_ID: str | None = None
    GCP_REGION: str | None = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def load_settings() -> Settings:
    s = Settings()
    pk_from_vault = get_secret_from_vault(s.VAULT_EXECUTOR_PATH, s.VAULT_EXECUTOR_KEY)
    if pk_from_vault:
        s.EXECUTOR_PRIVATE_KEY = SecretStr(pk_from_vault)
        log.info("EXECUTOR_PRIVATE_KEY_LOADED_FROM_VAULT")
    elif os.getenv("EXECUTOR_PRIVATE_KEY"):
        s.EXECUTOR_PRIVATE_KEY = SecretStr(os.getenv("EXECUTOR_PRIVATE_KEY"))
        log.warning("EXECUTOR_PRIVATE_KEY_LOADED_FROM_ENV_FALLBACK")
    
    if not s.EXECUTOR_PRIVATE_KEY:
        raise ValueError("Executor private key not found in Vault or environment variables.")
        
    return s

settings = load_settings()
