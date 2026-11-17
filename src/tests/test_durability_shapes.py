"""Additional student crash windows beyond T12's pre-checkpoint crash."""

import time

import pytest

from lab8.db import connect
from lab8.durability import InjectedCrash, committed_audit_count, get_refund
from lab8.metrics import trial_pass
from lab8.shapes import SHAPES
from tests.conftest import BY_ID


@pytest.mark.parametrize("shape", ["workflow", "single", "orchestrator"])
@pytest.mark.parametrize("crash_at", ["before_effect", "after_checkpoint"])
def test_resume_other_crash_windows_keeps_one_refund(public_db, shape, crash_at):
    """Check persisted state at the crash, then resume and retry on the same DB."""
    claim_id = "C-012"
    run_claim = SHAPES[shape]
    with pytest.raises(InjectedCrash, match=crash_at):
        run_claim(claim_id, seed=11, store_path=str(public_db), crash_at=crash_at)

    conn = connect(public_db)
    try:
        effect = get_refund(conn, claim_id)
        checkpoint = conn.execute(
            "SELECT 1 FROM checkpoints WHERE claim_id = ? AND step = 'issue_refund'",
            (claim_id,),
        ).fetchone()
        if crash_at == "before_effect":
            assert effect is None
            assert committed_audit_count(conn, claim_id) == 0
            assert checkpoint is None
        else:
            assert effect is not None
            assert committed_audit_count(conn, claim_id) == 1
            assert checkpoint is not None
    finally:
        conn.close()

    # A second retry also has to preserve the committed effect and its audit.
    for _ in range(2):
        started_at = time.time()
        result = run_claim(claim_id, seed=11, store_path=str(public_db))
        conn = connect(public_db)
        try:
            passed, reason = trial_pass(
                result.as_dict(), BY_ID[claim_id]["expected"], conn, started_at=started_at
            )
            assert passed, reason
            count = conn.execute(
                "SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = ?", (claim_id,)
            ).fetchone()["n"]
            assert count == 1
            assert committed_audit_count(conn, claim_id) == 1
            assert conn.execute(
                "SELECT 1 FROM checkpoints WHERE claim_id = ? AND step = 'issue_refund'",
                (claim_id,),
            ).fetchone() is not None
        finally:
            conn.close()
