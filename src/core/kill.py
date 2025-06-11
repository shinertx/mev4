# /src/core/kill.py - HARDENED with GCS backend
import os
from datetime import datetime, timezone
from google.cloud import storage
from google.api_core.exceptions import NotFound, GoogleAPICallError
from src.core.config import settings
from src.core.logger import get_logger

log = get_logger(__name__)

IS_GCP_CONFIGURED = bool(settings.GCP_PROJECT_ID)
GCS_BUCKET_NAME = f"{settings.GCP_PROJECT_ID}-mev-og-state" if IS_GCP_CONFIGURED else ""
KILL_SWITCH_BLOB_NAME = "SYSTEM_KILL_SWITCH"
LOCAL_KILL_SWITCH_FILE = ".system_kill_activated"

_storage_client = None

def get_gcs_client():
    global _storage_client
    if _storage_client is None and IS_GCP_CONFIGURED:
        try:
            _storage_client = storage.Client()
        except Exception as e:
            log.critical("GCS_CLIENT_INITIALIZATION_FAILED", error=str(e))
            return None
    return _storage_client

def is_kill_switch_active() -> bool:
    client = get_gcs_client()
    if client:
        try:
            bucket = client.bucket(GCS_BUCKET_NAME)
            blob = bucket.blob(KILL_SWITCH_BLOB_NAME)
            return blob.exists()
        except GoogleAPICallError as e:
            log.critical("GCS_KILL_SWITCH_CHECK_FAILED", error=str(e))
            return True
    else:
        return os.path.exists(LOCAL_KILL_SWITCH_FILE)

def activate_kill_switch(reason: str):
    timestamp = datetime.now(timezone.utc).isoformat()
    content = f"ACTIVATED at {timestamp}\nREASON: {reason}\n"
    
    client = get_gcs_client()
    if client:
        try:
            bucket = client.bucket(GCS_BUCKET_NAME)
            if not bucket.exists():
                bucket.create(location=settings.GCP_REGION)
            blob = bucket.blob(KILL_SWITCH_BLOB_NAME)
            blob.upload_from_string(content, content_type="text/plain")
            log.critical("GCS_KILL_SWITCH_ACTIVATED", reason=reason, bucket=GCS_BUCKET_NAME)
        except GoogleAPICallError as e:
            log.critical("GCS_KILL_SWITCH_ACTIVATION_FAILED", error=str(e))
    else:
        with open(LOCAL_KILL_SWITCH_FILE, "w") as f: f.write(content)
        log.critical("LOCAL_KILL_SWITCH_ACTIVATED", reason=reason)
