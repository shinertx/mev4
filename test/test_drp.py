import os
import json
import asyncio
import importlib
import time
import pytest

from src.core.state import State
from src.core import drp
from src.core.config import settings

@pytest.mark.asyncio
async def test_snapshot_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(drp, "SNAPSHOT_DIR", tmp_path)
    state = State()
    path = await drp.save_snapshot(state)
    assert os.path.exists(path)
    loaded = await drp.load_snapshot(path)
    assert loaded.session_id == state.session_id


@pytest.mark.asyncio
async def test_snapshot_ttl_cleanup(tmp_path, monkeypatch):
    monkeypatch.setattr(drp, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(settings, "MUTATION_TTL_SECONDS", 1)
    state = State()
    first = await drp.save_snapshot(state)
    os.utime(first, (time.time() - 2, time.time() - 2))
    await asyncio.sleep(1.1)
    second = await drp.save_snapshot(state)
    assert os.path.exists(second)
    assert not os.path.exists(first)
