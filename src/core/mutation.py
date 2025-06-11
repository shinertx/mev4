import asyncio
import json
import os
import difflib
from copy import deepcopy

from src.core import drp
from src.core.logger import get_logger, MUTATION_ATTEMPT, MUTATION_APPROVED
from src.core.kill import check
from src.core.config import settings
import sentry_sdk

log = get_logger(__name__)
APPROVAL_FILE = os.path.join(settings.SESSION_DIR, "manual_mutation.approved")

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
        while not os.path.exists(APPROVAL_FILE):
            await asyncio.sleep(1)
        os.remove(APPROVAL_FILE)
    MUTATION_APPROVED.inc()
    return result
