import os
import hmac
import hashlib
import json
from src.core.logger import get_logger, AUDIT_FILE, SIGNING_KEY, TRADES_EXECUTED


def test_audit_log_and_prometheus(tmp_path, monkeypatch):
    monkeypatch.setattr("src.core.logger.AUDIT_FILE", tmp_path / "audit.log")
    log = get_logger("test")
    log.info("UNIT_TEST_EVENT", data=1)
    with open(tmp_path / "audit.log") as f:
        line = f.readline().strip()
    payload, sig = line.split("|")
    expected = hmac.new(SIGNING_KEY, payload.encode(), hashlib.sha256).hexdigest()
    assert sig == expected

    c = TRADES_EXECUTED.labels("unit")
    initial = c._value.get()
    c.inc()
    assert c._value.get() == initial + 1
