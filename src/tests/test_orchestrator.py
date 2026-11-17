"""Unit tests for Shape C — orchestrator."""

from __future__ import annotations

import time

from lab8.db import connect
from lab8.metrics import trial_pass
from lab8.shapes.orchestrator import run_claim
from tests.conftest import BY_ID


def test_orchestrator_c001_resolves(public_db):
    started_at = time.time()
    result = run_claim("C-001", seed=11, store_path=str(public_db))
    conn = connect(public_db)
    try:
        passed, reason = trial_pass(result.as_dict(), BY_ID["C-001"]["expected"], conn, started_at=started_at)
    finally:
        conn.close()
    assert passed, reason
    assert result.status == "resolved"
    assert result.proposal_amount == 35000


def test_orchestrator_missing_order_needs_info(public_db):
    started_at = time.time()
    result = run_claim("C-004", seed=11, store_path=str(public_db))
    conn = connect(public_db)
    try:
        passed, reason = trial_pass(result.as_dict(), BY_ID["C-004"]["expected"], conn, started_at=started_at)
    finally:
        conn.close()
    assert passed, reason
    assert result.status == "needs_info"


def test_orchestrator_unknown_claim_fails(public_db):
    result = run_claim("C-999_NONEXISTENT", seed=11, store_path=str(public_db))
    assert result.status == "failed"
    assert result.error_reason == "unknown_claim"
