# /src/core/drp.py
# Aligns with PROJECT_BIBLE.md: Section 2, 3, 8
# - Implements DRP snapshot/restore logic for Agent/Session state.
# - Leverages the Pydantic model for atomic, auditable state serialization and validation.
# - Fulfills the "DRP must snapshot/restore/export/import all critical state" rule.

import json
from pathlib import Path
from datetime import datetime, timezone

from src.core.state import State
from src.core.logger import get_logger

log = get_logger(__name__)

# Base directory for all DRP snapshots. This should be a persistent volume in production.
DRP_SNAPSHOT_DIR = Path("./drp_snapshots")

def save_snapshot(state: State) -> str:
    """
    Serializes the given State object to a JSON file for DRP.
    The filename is constructed from the session ID and a timestamp for uniqueness
    and easy identification.

    Args:
        state: The State object to snapshot.

    Returns:
        The full path to the saved snapshot file as a string.
        
    Raises:
        IOError or other filesystem exceptions on failure.
    """
    # Ensure the DRP directory exists, creating it if necessary.
    DRP_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"session_snapshot_{state.session_id}_{timestamp}.json"
    filepath = DRP_SNAPSHOT_DIR / filename

    try:
        # Pydantic's `model_dump_json` is the ideal tool here. It correctly
        # handles special types like UUID, Decimal, and datetime.
        snapshot_data = state.model_dump_json(indent=2)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(snapshot_data)
        
        log.info(
            "DRP_SNAPSHOT_SAVED",
            session_id=str(state.session_id),
            path=str(filepath)
        )
        return str(filepath)
        
    except Exception as e:
        log.critical(
            "DRP_SNAPSHOT_SAVE_FAILED",
            session_id=str(state.session_id),
            path=str(filepath),
            error=str(e),
            exc_info=e
        )
        raise

def load_snapshot(filepath: str) -> State:
    """
    Loads and deserializes a session State from a DRP snapshot file.
    Performs validation against the State model during loading.

    Args:
        filepath: The path to the snapshot file.

    Returns:
        A new State object restored from the snapshot.
        
    Raises:
        FileNotFoundError: If the snapshot file does not exist.
        ValidationError (from Pydantic): If the data is malformed or doesn't match the State model.
        JSONDecodeError: If the file is not valid JSON.
    """
    log.warning("DRP_SNAPSHOT_LOAD_ATTEMPT", path=filepath)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Pydantic's `model_validate` method does the heavy lifting of parsing
        # and validating the data structure and types. This prevents us from
        # loading corrupted or incompatible state.
        restored_state = State.model_validate(data)
        
        log.warning(
            "DRP_SNAPSHOT_LOADED_SUCCESSFULLY",
            path=filepath,
            session_id=str(restored_state.session_id),
            session_start_time=restored_state.start_time.isoformat()
        )
        return restored_state
        
    except FileNotFoundError:
        log.error("DRP_SNAPSHOT_NOT_FOUND", path=filepath)
        raise
    except Exception as e:
        log.critical(
            "DRP_SNAPSHOT_LOAD_FAILED",
            path=filepath,
            error=str(e),
            exc_info=e
        )
        raise
