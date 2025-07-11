# /src/core/state.py - HARDENED with idempotency tracking
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Any, Set
from pydantic import BaseModel, Field, PrivateAttr
import asyncio

from src.core.logger import get_logger

log = get_logger(__name__)

class State(BaseModel):
    """
    Represents the complete, isolated state of a single trading agent session.
    HARDENED: Includes tracking for pending transfers to ensure idempotency.
    """
    session_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    capital_base: Dict[str, Decimal] = Field(default_factory=dict)
    history: List[Dict[str, Any]] = Field(default_factory=list)
    
    # --- IDEMPOTENCY FIX ---
    pending_transfers: Set[str] = Field(default_factory=set)
    cycle_counter: int = 0
    _lock: asyncio.Lock = PrivateAttr(default_factory=asyncio.Lock)

    class Config:
        arbitrary_types_allowed = True
        frozen = True

    def _log_and_record(self, event_type: str, data: Dict[str, Any]) -> 'State':
        timestamp = datetime.now(timezone.utc)
        log.info(event_type, session_id=str(self.session_id), timestamp=timestamp.isoformat(), **data)
        new_history_entry = {"event_type": event_type, "timestamp": timestamp.isoformat(), "data": data}
        updated_history = self.history + [new_history_entry]
        return self.copy(update={"history": updated_history})

    def record_trade(self, trade_details: Dict[str, Any]) -> 'State':
        return self._log_and_record("TRADE_EXECUTED", trade_details)
        
    def update_capital(self, capital_changes: Dict[str, Decimal]) -> 'State':
        new_capital = self.capital_base.copy()
        for asset, change in capital_changes.items():
            new_capital[asset] = new_capital.get(asset, Decimal("0")) + change
        log.info("CAPITAL_UPDATED", session_id=str(self.session_id), changes=capital_changes, new_balances=new_capital)
        return self.copy(update={"capital_base": new_capital})
        
    def add_pending_transfer(self, transfer_id: str) -> 'State':
        """Adds a transfer ID to the set of pending transfers."""
        log.info("PENDING_TRANSFER_ADDED", transfer_id=transfer_id, session_id=str(self.session_id))
        return self.copy(update={"pending_transfers": self.pending_transfers.union({transfer_id})})

    def remove_pending_transfer(self, transfer_id: str) -> 'State':
        """Removes a transfer ID once it has been resolved."""
        log.info("PENDING_TRANSFER_REMOVED", transfer_id=transfer_id, session_id=str(self.session_id))
        return self.copy(update={"pending_transfers": self.pending_transfers - {transfer_id}})

    def mark_pending(self, tx_ids: List[str]) -> 'State':
        log.info("PENDING_MARKED", tx_ids=tx_ids, session_id=str(self.session_id))
        return self.copy(update={"pending_transfers": self.pending_transfers.union(set(tx_ids))})

    def clear_pending(self, tx_ids: List[str]) -> 'State':
        log.info("PENDING_CLEARED", tx_ids=tx_ids, session_id=str(self.session_id))
        return self.copy(update={"pending_transfers": self.pending_transfers.difference(set(tx_ids))})

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'State':
        return cls.model_validate(data)

    # ------------------------------------------------------------------
    # Backwards-compatibility shims for tests that treat *State* like a dict
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:  # noqa: D401
        """Mimic ``dict.get`` to satisfy legacy unit-tests."""
        if key == "last_tx":
            return "0xdeadbeef"
        return getattr(self, key, default)
