# /src/adapters/ai_model.py
# FINAL VERSION: Integrates with OpenAI for offline strategic analysis.
# This is "The Strategist" with built-in safety via validation and manual approval.
import os
import json
import aiohttp
from pydantic import BaseModel, ValidationError

from src.core.config import settings
from src.core.logger import get_logger
from src.core.kill import check, KillSwitchActiveError

log = get_logger(__name__)
# Use the session directory defined in config for durability
APPROVAL_DIR = os.path.join(settings.SESSION_DIR, "mutation_approvals")

class StrategyMutationRequest(BaseModel):
    """
    Defines the strict data schema for a parameter mutation suggestion from the LLM.
    This prevents the LLM from hallucinating invalid or dangerous parameters.
    """
    trade_amount: str
    min_profit_usd: str
    rationale: str # The LLM must explain WHY it's making the suggestion.

class AIModelAdapter:
    """
    Interfaces with a powerful LLM to provide strategic recommendations.
    This adapter runs OFFLINE to analyze performance and suggest parameter changes.
    """
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY.get_secret_value() if settings.OPENAI_API_KEY else None
        self.api_url = settings.AI_MODEL_API_URL
        os.makedirs(APPROVAL_DIR, exist_ok=True)
        if not self.api_key:
            log.warning("AI_MODEL_ADAPTER_NO_API_KEY", detail="Module will be inert.")
        else:
            log.info("AI_MODEL_ADAPTER_INITIALIZED_WITH_API_KEY")

    def _construct_prompt(self, strategy_name: str, performance_data: dict) -> str:
        """Constructs a detailed prompt for the LLM to elicit a structured JSON response."""
        return f"""
        You are a world-class quantitative analyst for a leading MEV firm.
        Your task is to optimize the parameters for a trading strategy named '{strategy_name}'.

        Current Performance Data (last cycle):
        - Performance: {json.dumps(performance_data.get('performance'), indent=2)}
        - Current Parameters: {json.dumps(performance_data.get('current_params'))}

        Instruction:
        Based on this data, suggest a new set of parameters to improve profitability.
        Your output MUST be a single, valid JSON object matching this exact schema, with no other text:
        {{
            "trade_amount": "<new_amount_as_string_decimal>",
            "min_profit_usd": "<new_threshold_as_string_decimal>",
            "rationale": "<A concise explanation for your changes. Mention why the previous values might be sub-optimal.>"
        }}
        """

    async def fetch_and_propose_mutation(self, strategy_name: str, performance_data: dict):
        """
        Calls the LLM API, validates the response, and writes a pending approval file.
        An operator must rename the file from '.pending.json' to '.approved.json' to activate.
        """
        if not self.api_key:
            return
        check()

        prompt = self._construct_prompt(strategy_name, performance_data)
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
                async with session.post(self.api_url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    result = await response.json()
                    llm_suggestion_str = result['choices'][0]['message']['content']
                    
                    # CRITICAL: Validate the JSON response against our Pydantic model
                    validated_params = StrategyMutationRequest.model_validate_json(llm_suggestion_str)
                    
                    # Write the validated suggestion to a pending file
                    filepath = os.path.join(APPROVAL_DIR, f"{strategy_name}.pending.json")
                    with open(filepath, "w") as f: f.write(validated_params.model_dump_json(indent=2))
                    
                    log.warning("LLM_MUTATION_PROPOSED_AWAITING_APPROVAL", strategy=strategy_name, params=validated_params.model_dump())

        except (aiohttp.ClientError, ValidationError, KeyError, json.JSONDecodeError) as e:
            log.error("LLM_MUTATION_FETCH_FAILED", strategy=strategy_name, error=str(e), exc_info=True)

    def get_approved_mutation(self, strategy_name: str) -> dict | None:
        """Checks for a file renamed by an operator from .pending.json to .approved.json."""
        check()
        approved_path = os.path.join(APPROVAL_DIR, f"{strategy_name}.approved.json")
        if os.path.exists(approved_path):
            try:
                with open(approved_path, "r") as f:
                    params = json.load(f)
                os.remove(approved_path) # Consume the approval to prevent re-application
                log.info("APPROVED_MUTATION_FOUND_AND_CONSUMED", strategy=strategy_name, params=params)
                return params
            except (json.JSONDecodeError, OSError) as e:
                log.error("FAILED_TO_CONSUME_APPROVED_MUTATION", file=approved_path, error=str(e))
                # Move corrupted file to avoid loops
                os.rename(approved_path, approved_path + ".corrupted")
                return None
        return None
