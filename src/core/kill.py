# /src/core/kill.py
# Aligns with PROJECT_BIBLE.md: Section 3 & 5
# - Implements the system-wide, non-bypassable kill switch.
# - Every component MUST check this before any capital move or external call.

import os
from datetime import datetime, timezone
from src.core.logger import get_logger

log = get_logger(__name__)

# A simple, file-based kill switch. It's robust, cross-process, and
# easily inspectable during an emergency.
KILL_SWITCH_FILE = ".system_kill_activated"

_is_active = None # In-memory cache

def _check_file_and_cache():
    """Checks the filesystem and updates the in-memory cache."""
    global _is_active
    _is_active = os.path.exists(KILL_SWITCH_FILE)
    return _is_active

def is_kill_switch_active() -> bool:
    """
    Checks if the system-wide kill switch has been activated.
    This function MUST be called before any trade, transaction, or capital-moving action.
    """
    # The cache avoids constant filesystem checks but re-verifies if cache is false.
    if _is_active:
        return True
    return _check_file_and_cache()

def activate_kill_switch(reason: str):
    """
    Activates the system-wide kill switch, halting all operations.
    Logs the event with extreme priority.
    """
    global _is_active
    if not is_kill_switch_active():
        try:
            with open(KILL_SWITCH_FILE, "w") as f:
                timestamp = datetime.now(timezone.utc).isoformat()
                f.write(f"ACTIVATED at {timestamp}\n")
                f.write(f"REASON: {reason}\n")
            _is_active = True
            log.critical(
                "KILL_SWITCH_ACTIVATED", 
                reason=reason,
                timestamp=timestamp,
            )
        except Exception as e:
            log.error("Failed to write kill switch file", error=str(e), exc_info=e)
            _is_active = False # Ensure state is consistent if write failed

def get_kill_reason() -> str | None:
    """Reads the reason and timestamp from the kill switch file."""
    if os.path.exists(KILL_SWITCH_FILE):
        try:
            with open(KILL_SWITCH_FILE, "r") as f:
                return f.read()
        except Exception as e:
            log.error("Failed to read kill switch file", error=str(e), exc_info=e)
    return None
