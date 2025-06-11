import os
import pytest
from fastapi.testclient import TestClient

from src.core.kill import activate_kill_switch, deactivate_kill_switch, check, KillSwitchActiveError, KILL_SWITCH_FILE
from src.core.control_api import app
from src.core.config import settings

@pytest.fixture(autouse=True)
def cleanup():
    yield
    if os.path.exists(KILL_SWITCH_FILE):
        os.remove(KILL_SWITCH_FILE)

def test_kill_check_raises():
    activate_kill_switch("test")
    with pytest.raises(KillSwitchActiveError):
        check()


def test_control_api_toggle(monkeypatch):
    monkeypatch.setattr(settings, "CONTROL_API_TOKEN", "tok")
    client = TestClient(app)
    r = client.post("/kill/toggle", headers={"Authorization": "Bearer tok"}, json={"reason": "t"})
    assert r.status_code == 200
    assert os.path.exists(KILL_SWITCH_FILE)
    r = client.post("/kill/toggle", headers={"Authorization": "Bearer tok"}, json={"reason": "t"})
    assert r.status_code == 200
    assert not os.path.exists(KILL_SWITCH_FILE)
