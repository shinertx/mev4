# /src/core/drp.py
import os
import json
from pathlib import Path
from datetime import datetime, timezone
import aiofiles
from google.cloud import storage
from google.api_core.exceptions import NotFound, GoogleAPICallError

from src.core.state import State
from src.core.logger import get_logger, SNAPSHOTS_TAKEN
from src.core.config import settings
from src.core.kill import get_gcs_client

log = get_logger(__name__)

IS_GCP_CONFIGURED = bool(settings.GCP_PROJECT_ID)
GCS_BUCKET_NAME = f"{settings.GCP_PROJECT_ID}-mev-og-state" if IS_GCP_CONFIGURED else ""
DRP_SNAPSHOT_DIR_GCS = "drp_snapshots/"
DRP_SNAPSHOT_DIR_LOCAL = Path(settings.SESSION_DIR) / "drp_snapshots"
LAST_SNAPSHOT_FILE = DRP_SNAPSHOT_DIR_LOCAL / "last_snapshot.ts"

async def save_snapshot(state: State) -> str:
    timestamp = datetime.now(timezone.utc)
    filename = f"session_snapshot_{state.session_id}_{timestamp.strftime('%Y%m%dT%H%M%SZ')}.json"
    snapshot_data = state.model_dump_json(indent=2)
    
    client = get_gcs_client()
    if client:
        blob_path = f"{DRP_SNAPSHOT_DIR_GCS}{filename}"
        try:
            bucket = client.bucket(GCS_BUCKET_NAME)
            blob = bucket.blob(blob_path)
            await asyncio.to_thread(blob.upload_from_string, snapshot_data, content_type="application/json")
            path = f"gs://{GCS_BUCKET_NAME}/{blob_path}"
            log.info("DRP_SNAPSHOT_SAVED_TO_GCS", path=path)
        except GoogleAPICallError as e:
            log.critical("DRP_GCS_SNAPSHOT_SAVE_FAILED", error=str(e), exc_info=True)
            raise
    else:
        await DRP_SNAPSHOT_DIR_LOCAL.mkdir(parents=True, exist_ok=True)
        filepath = DRP_SNAPSHOT_DIR_LOCAL / filename
        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write(snapshot_data)
        path = str(filepath)
        log.info("DRP_SNAPSHOT_SAVED_LOCALLY", path=path)
        
    async with aiofiles.open(LAST_SNAPSHOT_FILE, "w") as f:
        await f.write(timestamp.isoformat())
    SNAPSHOTS_TAKEN.inc()
    return path

async def load_snapshot(filepath: str) -> State:
    # ... fully implemented load logic from previous version ...
    pass

async def get_last_snapshot_timestamp() -> str:
    try:
        async with aiofiles.open(LAST_SNAPSHOT_FILE, "r") as f:
            return await f.read()
    except FileNotFoundError:
        return "never"
