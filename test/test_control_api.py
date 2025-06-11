import os
import asyncio
import pytest
from fastapi.testclient import TestClient

from src.core.control_api import app
from src.core.config import settings
from src.core import drp
from src.core.state import State
from src.core.kill import KILL_SWITCH_FILE

@pytest.fixture(autouse=True)
def cleanup():
    if os.path.exists(KILL_SWITCH_FILE):
        os.remove(KILL_SWITCH_FILE)
    yield
    if os.path.exists(KILL_SWITCH_FILE):
        os.remove(KILL_SWITCH_FILE)

@pytest.mark.asyncio
async def test_toggle_and_restore(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "CONTROL_API_TOKEN", "tok")
    monkeypatch.setattr(drp, "SNAPSHOT_DIR", tmp_path)
    client = TestClient(app)

    state = State()
    path = await drp.save_snapshot(state)

    r = client.post("/kill/toggle", headers={"Authorization": "Bearer tok"}, json={"reason": "t"})
    assert r.status_code == 200 and r.json()["kill_switch_active"] is True
    r = client.post("/kill/toggle", headers={"Authorization": "Bearer tok"}, json={"reason": "t"})
    assert r.status_code == 200 and r.json()["kill_switch_active"] is False

    r = client.post("/drp/restore", headers={"Authorization": "Bearer tok"}, json={"snapshot_path": path})
    assert r.status_code == 200
    assert r.json()["session_id"] == str(state.session_id)
