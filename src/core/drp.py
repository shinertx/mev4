from __future__ import annotations
import json
import aiofiles
from datetime import datetime, timezone
from pathlib import Path

from src.core.state import State
from src.core.logger import get_logger, SNAPSHOTS_TAKEN
from src.core.config import settings

log = get_logger(__name__)
SNAPSHOT_DIR = Path(settings.SESSION_DIR) / "snapshots"

async def save_snapshot(state: State) -> str:
    """Persist state to a timestamped JSON snapshot."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = SNAPSHOT_DIR / f"{state.session_id}_{ts}.json"
    async with aiofiles.open(path, "w") as f:
        await f.write(state.model_dump_json(indent=2))
    SNAPSHOTS_TAKEN.inc()
    ttl = getattr(settings, "MUTATION_TTL_SECONDS", 0)
    if ttl:
        now = datetime.now().timestamp()
        for fp in SNAPSHOT_DIR.glob("*.json"):
            if now - fp.stat().st_mtime > ttl:
                fp.unlink(missing_ok=True)
    log.info("DRP_SNAPSHOT_SAVED", path=str(path))
    return str(path)

async def load_snapshot(path: str) -> State:
    """Load a snapshot file back into a State object."""
    async with aiofiles.open(path, "r") as f:
        data = await f.read()
    obj = json.loads(data)
    return State.model_validate(obj)
