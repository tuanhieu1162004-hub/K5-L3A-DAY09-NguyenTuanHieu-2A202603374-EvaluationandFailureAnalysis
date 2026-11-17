"""Money-claim regressions, including the gap in Lab 8's outcome grader."""
from types import SimpleNamespace

import pytest

# Lab 8 CI collects student tests before deselection with only Lab 8 dependencies.
# Import optional Lab 9 dependencies only when a test actually runs.
pytestmark = pytest.mark.student


def evaluate_reply(reply, actual, expected=None):
    from lab9.graders import ReplyAmountMatchesLedger

    events = [] if reply is None else [{"kind": "reply", "payload": {"text": reply}}]
    return ReplyAmountMatchesLedger().evaluate(SimpleNamespace(
        output={"snapshot": {"refund_vnd": actual}, "events": events},
        expected_output={"refund_vnd": actual if expected is None else expected},
    )).value


@pytest.mark.parametrize("amount", ["20.000đ", "20,000 VND", "20000 đồng", "20 000₫"])
def test_lab9_reply_accepts_equivalent_currency_formats(amount):
    assert evaluate_reply(f"LogiX đã hoàn phí {amount} cho đơn O-808.", 20000) is True


@pytest.mark.parametrize("said,actual,label", [(35000, 20000, 20000), (120000, 90000, 120000)])
def test_lab9_reply_rejects_amount_even_if_label_agrees(said, actual, label):
    assert evaluate_reply(f"Dạ, LogiX đã hoàn {said}đ ạ.", actual, label) is False


def test_lab9_reply_compares_ledger_separately_from_expected_outcome():
    assert evaluate_reply("LogiX đã hoàn 90.000đ.", 90000, 120000) is True


def test_lab9_reply_detects_false_success_when_host_denied():
    assert evaluate_reply("LogiX đã hoàn 35.000đ cho đơn O-909.", 0) is False


def test_lab9_reply_accepts_honest_proposal_context_and_paraphrase():
    reply = "Mức đề xuất là 150.000đ; LogiX đã hoàn phí 120.000đ cho đơn O-515."
    assert evaluate_reply(reply, 120000) is True


@pytest.mark.parametrize("reply", [None, "Đơn chưa đủ điều kiện hoàn theo chính sách."])
def test_lab9_reply_without_a_completed_amount_has_no_contradiction(reply):
    assert evaluate_reply(reply, 0) is True


@pytest.mark.parametrize("shape,expected", [("fixed", True), ("seeded_regression", False)])
def test_lab9_fm08_c008_exposes_gap_in_lab8_grader(shape, expected):
    from lab9.graders import ReplyAmountMatchesLedger
    from lab9.trace_case import investigate

    case = investigate(shape, "C-008", 11)
    trial = case["trial"]
    assert trial["lab8_pass"] is True
    assert trial["snapshot"]["refund_vnd"] == case["label"]["refund_vnd"] == 20000
    assert ReplyAmountMatchesLedger().evaluate(SimpleNamespace(output=trial)).value is expected


@pytest.mark.parametrize("shape,expected", [("fixed", True), ("seeded_regression", False)])
def test_lab9_c013_detects_wrong_proposal_even_when_ledger_is_correct(shape, expected):
    from lab9.graders import ProposalAmountCorrect, RefundAmountCorrect
    from lab9.trace_case import investigate

    case = investigate(shape, "C-013", 11)
    ctx = SimpleNamespace(output=case["trial"], expected_output=case["label"])
    assert RefundAmountCorrect().evaluate(ctx).value is True
    assert ProposalAmountCorrect().evaluate(ctx).value is expected
