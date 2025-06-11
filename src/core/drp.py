# /src/core/drp.py - HARDENED with GCS backend for remote snapshots
import os
import json
from pathlib import Path
from datetime import datetime, timezone
from google.cloud import storage
from google.api_core.exceptions import NotFound, GoogleAPICallError

from src.core.state import State
from src.core.logger import get_logger
from src.core.config import settings
from src.core.kill import get_gcs_client

log = get_logger(__name__)

IS_GCP_CONFIGURED = bool(settings.GCP_PROJECT_ID)
GCS_BUCKET_NAME = f"{settings.GCP_PROJECT_ID}-mev-og-state" if IS_GCP_CONFIGURED else ""
DRP_SNAPSHOT_DIR_GCS = "drp_snapshots/"
DRP_SNAPSHOT_DIR_LOCAL = Path("./drp_snapshots")

def save_snapshot(state: State) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"session_snapshot_{state.session_id}_{timestamp}.json"
    snapshot_data = state.model_dump_json(indent=2)
    
    client = get_gcs_client()
    if client:
        blob_path = f"{DRP_SNAPSHOT_DIR_GCS}{filename}"
        try:
            bucket = client.bucket(GCS_BUCKET_NAME)
            if not bucket.exists(): bucket.create(location=settings.GCP_REGION)
            blob = bucket.blob(blob_path)
            blob.upload_from_string(snapshot_data, content_type="application/json")
            log.info("DRP_SNAPSHOT_SAVED_TO_GCS", path=f"gs://{GCS_BUCKET_NAME}/{blob_path}")
            return f"gs://{GCS_BUCKET_NAME}/{blob_path}"
        except GoogleAPICallError as e:
            log.critical("DRP_GCS_SNAPSHOT_SAVE_FAILED", error=str(e), exc_info=True)
            raise
    else:
        DRP_SNAPSHOT_DIR_LOCAL.mkdir(parents=True, exist_ok=True)
        filepath = DRP_SNAPSHOT_DIR_LOCAL / filename
        with open(filepath, "w", encoding="utf-8") as f: f.write(snapshot_data)
        log.info("DRP_SNAPSHOT_SAVED_LOCALLY", path=str(filepath))
        return str(filepath)

def load_snapshot(filepath: str) -> State:
    log.warning("DRP_SNAPSHOT_LOAD_ATTEMPT", path=filepath)
    if filepath.startswith("gs://"):
        client = get_gcs_client()
        if not client: raise FileNotFoundError("GCS client not available")
        try:
            bucket_name, blob_path = filepath.replace("gs://", "").split("/", 1)
            blob = client.bucket(bucket_name).blob(blob_path)
            snapshot_data = blob.download_as_string()
        except (NotFound, GoogleAPICallError) as e:
            raise FileNotFoundError(f"GCS snapshot not found or access failed: {e}")
    else:
        if not os.path.exists(filepath): raise FileNotFoundError(f"Local snapshot not found at {filepath}")
        with open(filepath, "r", encoding="utf-8") as f: snapshot_data = f.read()

    restored_state = State.model_validate_json(snapshot_data)
    log.warning("DRP_SNAPSHOT_LOADED_SUCCESSFULLY", path=filepath, session_id=str(restored_state.session_id))
    return restored_state
