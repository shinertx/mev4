# /src/adapters/ai_model.py
# FINAL VERSION: Integrates with OpenAI for offline strategic analysis.
# This is "The Strategist" with built-in safety via validation and manual approval.

import os
import json
import aiohttp
from pydantic import BaseModel, ValidationError

from src.core.config import settings
from src.core.logger import get_logger

log = get_logger(__name__)
APPROVAL_DIR = os.path.join(settings.SESSION_DIR, "mutation_approvals")

class StrategyMutationRequest(BaseModel):
    """Defines the strict data schema for a parameter mutation suggestion."""
    trade_amount: str
    min_profit_usd: str
    rationale: str

class AIModelAdapter:
    """Interfaces with an LLM to provide strategic recommendations."""
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY.get_secret_value() if settings.OPENAI_API_KEY else None
        self.api_url = "https://api.openai.com/v1/chat/completions"
        os.makedirs(APPROVAL_DIR, exist_ok=True)
        if not self.api_key:
            log.warning("AI_MODEL_ADAPTER_NO_API_KEY", detail="Will not be able to fetch suggestions.")

    def _construct_prompt(self, strategy_name: str, performance_data: dict) -> str:
        """Constructs a detailed prompt for the LLM."""
        return f"""
        You are a quantitative analyst for a leading MEV firm optimizing a strategy named '{strategy_name}'.
        Performance Data: {json.dumps(performance_data.get('performance'), indent=2)}
        Current Parameters: {json.dumps(performance_data.get('current_params'))}
        Instruction: Provide your output as a single, valid JSON object matching this schema:
        {{
            "trade_amount": "<new_amount_as_string_decimal>",
            "min_profit_usd": "<new_threshold_as_string_decimal>",
            "rationale": "<A concise explanation for your changes>"
        }}
        """

    async def fetch_and_propose_mutation(self, strategy_name: str, performance_data: dict):
        """Calls the LLM API and writes a pending approval file."""
        if not self.api_key: return

        prompt = self._construct_prompt(strategy_name, performance_data)
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": "gpt-4-turbo", "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    result = await response.json()
                    suggestion_str = result['choices'][0]['message']['content']
                    
                    validated_params = StrategyMutationRequest.model_validate_json(suggestion_str)
                    
                    filepath = os.path.join(APPROVAL_DIR, f"{strategy_name}.pending.json")
                    with open(filepath, "w") as f:
                        f.write(validated_params.model_dump_json(indent=2))
                    log.warning("LLM_MUTATION_PROPOSED_AWAITING_APPROVAL", strategy=strategy_name, params=validated_params.model_dump())
        except Exception as e:
            log.error("LLM_MUTATION_FETCH_FAILED", strategy=strategy_name, error=str(e), exc_info=True)

    def get_approved_mutation(self, strategy_name: str) -> dict | None:
        """Checks for a file renamed by an operator from .pending.json to .approved.json."""
        approved_path = os.path.join(APPROVAL_DIR, f"{strategy_name}.approved.json")
        if os.path.exists(approved_path):
            with open(approved_path, "r") as f:
                params = json.load(f)
            os.remove(approved_path)
            log.info("APPROVED_MUTATION_FOUND_AND_CONSUMED", strategy=strategy_name, params=params)
            return params
        return None
