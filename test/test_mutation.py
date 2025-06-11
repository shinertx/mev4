import os
import asyncio
import pytest

from src.core.state import State
from src.core.mutation import sandboxed_mutate
from src.core.config import settings
from src.strategies.cross_domain import CrossDomainArbitrageStrategy
from src.adapters.mock import MockTransactionManager, MockDexAdapter

@pytest.mark.asyncio
async def test_sandboxed_mutate(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MANUAL_APPROVAL", False)
    settings.SESSION_DIR = str(tmp_path)
    strategy = CrossDomainArbitrageStrategy("dexA", "dexB", ["A","B"], 1, 1)
    state = State()
    adapters = {"tx_manager": MockTransactionManager()}
    result = await sandboxed_mutate(strategy, state, adapters)
    assert result in (True, False)
    assert os.path.exists(os.path.join(settings.SESSION_DIR, "audit.log"))
