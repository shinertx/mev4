# /src/core/state.py
# Aligns with PROJECT_BIBLE.md: Section 3 & 8
# - Defines the atomic, rollbackable, and auditable state for an agent session.
# - NO global/singleton state. Each agent gets its own State instance.
# - Designed for easy snapshotting and restoration (DRP).

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Any
from pydantic import BaseModel, Field

from src.core.logger import get_logger

log = get_logger(__name__)

class State(BaseModel):
    """
    Represents the complete, isolated state of a single trading agent session.
    This object is the "source of truth" for a session's capital, history,
    and configuration. It is designed to be snapshotted and restored.
    """
    session_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Capital tracking: Maps an asset identifier (e.g., "ETH_MAINNET", "USDC_BINANCE")
    # to its balance. Using Decimal for financial precision.
    capital_base: Dict[str, Decimal] = Field(default_factory=dict)
    
    # Audit trail: An immutable log of all actions taken during the session.
    # This is critical for DRP and post-mortem analysis.
    history: List[Dict[str, Any]] = Field(default_factory=list, const=True)

    class Config:
        # Allows use of Decimal type
        arbitrary_types_allowed = True
        # Make the model fields immutable by default
        frozen = True

    def _log_and_record(self, event_type: str, data: Dict[str, Any]) -> 'State':
        """Internal helper to log an event and create a new state object."""
        timestamp = datetime.now(timezone.utc)
        
        # Log the event with session context
        log.info(
            event_type,
            session_id=str(self.session_id),
            timestamp=timestamp.isoformat(),
            **data,
        )
        
        # Create the new history entry
        new_history_entry = {
            "event_type": event_type,
            "timestamp": timestamp.isoformat(),
            "data": data,
        }
        
        # Create a new State object with the updated history
        updated_history = self.history + [new_history_entry]
        # Pydantic's .copy() with update is perfect for creating modified immutable copies
        return self.copy(update={"history": updated_history})

    def record_trade(self, trade_details: Dict[str, Any]) -> 'State':
        """
        Records a trade, logs it, and returns a *new* immutable State object.
        This fulfills the "auditable" requirement.
        """
        return self._log_and_record("TRADE_EXECUTED", trade_details)
        
    def update_capital(self, capital_changes: Dict[str, Decimal]) -> 'State':
        """
        Applies capital changes and returns a *new* immutable State object.
        Example: {"ETH_MAINNET": Decimal("-1.0"), "USDC_MAINNET": Decimal("3000.0")}
        """
        # Create a mutable copy to perform the update
        new_capital = self.capital_base.copy()
        for asset, change in capital_changes.items():
            new_capital[asset] = new_capital.get(asset, Decimal("0")) + change
            
        # Log the change
        log.info(
            "CAPITAL_UPDATED",
            session_id=str(self.session_id),
            changes=capital_changes,
            new_balances=new_capital,
        )
        
        # Return a new State object with the updated capital
        return self.copy(update={"capital_base": new_capital})
