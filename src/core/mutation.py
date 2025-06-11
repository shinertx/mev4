import asyncio
import json
import os
import difflib
import time
from copy import deepcopy

from src.core import drp
from src.core.logger import (
    get_logger,
    MUTATION_ATTEMPT,
    MUTATION_APPROVED,
    MUTATION_REVERTED,
)
from src.core.kill import check
from src.core.config import settings
import sentry_sdk

log = get_logger(__name__)
APPROVAL_FILE = os.path.join(settings.SESSION_DIR, "manual_mutation.approved")
APPROVAL_DIR = os.path.join(settings.SESSION_DIR, "mutation_approvals")

async def sandboxed_mutate(strategy, state, adapters):
    """Execute strategy.mutate in a sandbox with DRP snapshots and audit."""
    check()
    MUTATION_ATTEMPT.inc()
    pre = await drp.save_snapshot(state)
    before = json.dumps(getattr(strategy, "get_params", lambda: deepcopy(strategy.__dict__))(), sort_keys=True, default=str)
    result = await strategy.mutate(adapters)
    after = json.dumps(getattr(strategy, "get_params", lambda: deepcopy(strategy.__dict__))(), sort_keys=True, default=str)
    post = await drp.save_snapshot(state)
    diff = list(difflib.unified_diff(before.splitlines(), after.splitlines()))
    log.warning("MUTATION", diff=diff, pre_snapshot=pre, post_snapshot=post)
    sentry_sdk.capture_message("Mutation executed")
    if settings.MANUAL_APPROVAL:
        log.warning("AWAITING_MANUAL_APPROVAL")
        start = time.time()
        ttl = getattr(settings, "MUTATION_TTL_SECONDS", 0)
        while not os.path.exists(APPROVAL_FILE):
            await asyncio.sleep(1)
            if ttl and time.time() - start > ttl:
                state = await drp.load_snapshot(pre)
                await drp.save_snapshot(state)
                MUTATION_REVERTED.inc()
                log.warning("MUTATION_AUTO_REVERTED", snapshot=pre)
                return None
        os.remove(APPROVAL_FILE)

    now = time.time()
    ttl = getattr(settings, "MUTATION_TTL_SECONDS", 0)
    if ttl:
        for fname in os.listdir(APPROVAL_DIR):
            if fname.endswith(".pending.json"):
                fp = os.path.join(APPROVAL_DIR, fname)
                if now - os.path.getmtime(fp) > ttl:
                    os.remove(fp)
                    state = await drp.load_snapshot(pre)
                    await drp.save_snapshot(state)
                    MUTATION_REVERTED.inc()
                    log.warning("MUTATION_AUTO_REVERTED", snapshot=pre, pending=fname)
                    return None

    MUTATION_APPROVED.inc()
    return result
