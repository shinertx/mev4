# /src/adapters/ai_model.py
import os
import json
from pydantic import BaseModel, ValidationError
from src.core.config import settings
from src.core.logger import get_logger

log = get_logger(__name__)
APPROVAL_DIR = os.path.join(settings.SESSION_DIR, "mutation_approvals")

class MutationRequest(BaseModel):
    """Schema for validating mutation suggestions."""
    trade_amount: str
    min_profit_usd: str

class AIModelAdapter:
    def __init__(self):
        os.makedirs(APPROVAL_DIR, exist_ok=True)
        log.info("HARDENED_AI_ADAPTER_INITIALIZED")

    def request_mutation(self, strategy_name: str, new_params: dict):
        """Writes a potential mutation to a file for external approval."""
        try:
            # 1. Validate the schema
            MutationRequest.model_validate(new_params)
            
            # 2. Write to a pending file
            filepath = os.path.join(APPROVAL_DIR, f"{strategy_name}.pending.json")
            with open(filepath, "w") as f:
                json.dump(new_params, f)
            log.warning("MUTATION_REQUESTED_AWAITING_APPROVAL", strategy=strategy_name, params=new_params)
        except ValidationError as e:
            log.error("INVALID_MUTATION_SUGGESTION", error=str(e))

    def get_approved_mutation(self, strategy_name: str) -> dict | None:
        """Checks for an approved mutation file."""
        pending_path = os.path.join(APPROVAL_DIR, f"{strategy_name}.pending.json")
        approved_path = os.path.join(APPROVAL_DIR, f"{strategy_name}.approved.json")

        # An external process (or operator) renames .pending. to .approved.
        if os.path.exists(approved_path):
            with open(approved_path, "r") as f:
                params = json.load(f)
            os.remove(approved_path) # Consume the approval
            log.info("APPROVED_MUTATION_FOUND_AND_CONSUMED", strategy=strategy_name, params=params)
            return params
        return None
