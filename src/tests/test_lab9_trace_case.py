"""Regression case C-002@11: detect ticket data overriding DB facts."""
from types import SimpleNamespace

import pytest

# Keep optional Lab 9 imports inside the test so Lab 8 CI can collect this file.
pytestmark = pytest.mark.student


@pytest.mark.parametrize(
    "shape,expected_pass",
    [("fixed", True), ("seeded_regression", False)],
)
def test_lab9_c002_contract_detects_override(shape, expected_pass):
    from lab9.graders import DbFactKept
    from lab9.trace_case import investigate

    case = investigate(shape, "C-002", 11)
    trial, label = case["trial"], case["label"]

    verdict = DbFactKept().evaluate(SimpleNamespace(output=trial))
    assert verdict.value is expected_pass
    assert trial["lab8_pass"] is expected_pass
    assert (trial["result"]["status"] == label["status"]) is expected_pass
    for key in ("refund_vnd", "refund_count"):
        assert (trial["snapshot"][key] == label[key]) is expected_pass, key
    assert trial["unexpected_rows"] == 0
