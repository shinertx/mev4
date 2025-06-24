from fastapi import FastAPI, HTTPException, Header, Depends, Body
from src.core.kill import activate_kill_switch, deactivate_kill_switch, is_kill_switch_active
from src.core import drp
from src.core.logger import get_logger
from src.core.config import settings

app = FastAPI()
log = get_logger(__name__)

def verify(authorization: str | None = Header(None)):
    token = settings.CONTROL_API_TOKEN
    if not token:
        raise HTTPException(status_code=500, detail="Control token not configured")
    if authorization != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.post("/kill/toggle")
async def toggle_kill(reason: str = "", auth: None = Depends(verify)):
    if is_kill_switch_active():
        deactivate_kill_switch()
    else:
        activate_kill_switch(reason or "manual override")
    return {"kill_switch_active": is_kill_switch_active()}

@app.post("/drp/restore")
async def restore(snapshot_path: str = Body(..., embed=True), auth: None = Depends(verify)):
    state = await drp.load_snapshot(snapshot_path)
    log.warning("DRP_RESTORED", snapshot=snapshot_path)
    return {"session_id": str(state.session_id)}
