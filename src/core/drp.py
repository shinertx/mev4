# /src/core/drp.py

import os, json
from pathlib import Path
from datetime import datetime, timezone
import aiofiles
from google.cloud import storage
from google.api_core.exceptions import GoogleAPICallError

from src.core.state import State
from src.core.logger import get_logger, SNAPSHOTS_TAKEN
from src.core.config import settings
from src.core.kill import get_gcs_client

log = get_logger(__name__)
LOCAL_DIR = Path(settings.SESSION_DIR) / "drp_snapshots"
LAST_FILE = LOCAL_DIR / "last_snapshot.ts"
GCS_BUCKET = f"{settings.GCP_PROJECT_ID}-mev-og-state" if settings.GCP_PROJECT_ID else None

async def save_snapshot(state: State) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{state.session_id}_{ts}.json"
    payload = state.model_dump_json(indent=2)

    # Upload to GCS or write locally
    if GCS_BUCKET:
        client = get_gcs_client()
        blob = client.bucket(GCS_BUCKET).blob(f"drp/{filename}")
        try:
            await aiofiles.threadpool.wrap(blob.upload_from_string)(payload, content_type="application/json")
            path = f"gs://{GCS_BUCKET}/drp/{filename}"
            log.info("DRP_SNAPSHOT_GCS", path=path)
        except GoogleAPICallError as e:
            log.error("DRP_GCS_FAIL", error=str(e))
            raise
    else:
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        fp = LOCAL_DIR / filename
        async with aiofiles.open(fp, "w") as f:
            await f.write(payload)
        path = str(fp)
        log.info("DRP_SNAPSHOT_LOCAL", path=path)

    # Record last snapshot timestamp
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(LAST_FILE, "w") as f:
        await f.write(ts)
    SNAPSHOTS_TAKEN.inc()
    return path

async def load_snapshot(path: str) -> State:
    if path.startswith("gs://"):
        client = get_gcs_client()
        bucket, _, blob_name = path[5:].partition("/")
        blob = client.bucket(bucket).blob(blob_name)
        data = await aiofiles.threadpool.wrap(blob.download_as_text)()
    else:
        async with aiofiles.open(path, "r") as f:
            data = await f.read()
    obj = json.loads(data)
    return State.model_validate(obj)

async def get_last_snapshot_timestamp() -> str:
    try:
        async with aiofiles.open(LAST_FILE, "r") as f:
            return await f.read()
    except FileNotFoundError:
        return "never"
