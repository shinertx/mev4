import os
import json
import asyncio
import importlib
import pytest

from src.core.state import State
from src.core import drp

@pytest.mark.asyncio
async def test_snapshot_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(drp, "LOCAL_DIR", tmp_path)
    state = State()
    path = await drp.save_snapshot(state)
    assert os.path.exists(path)
    loaded = await drp.load_snapshot(path)
    assert loaded.session_id == state.session_id
