# /src/core/config_validator.py
# A script to be run at startup to validate all configs and secrets.
from src.core.config import settings
from src.core.logger import log

def validate():
    log.info("--- CONFIG VALIDATION START ---")
    required_vars = ['EXECUTOR_PRIVATE_KEY', 'ETH_RPC_URL_1', 'MEMPOOL_WSS_URL']
    errors = []

    for var in required_vars:
        if not getattr(settings, var, None):
            errors.append(f"Missing required configuration: {var}")
            
    if errors:
        for error in errors:
            log.critical(error)
        raise ValueError("System configuration is incomplete. Halting.")
        
    log.info("--- CONFIG VALIDATION PASSED ---")

if __name__ == "__main__":
    validate()
