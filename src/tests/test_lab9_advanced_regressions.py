"""Independent robustness checks for probabilities and evaluation integrity."""
import copy
from itertools import combinations

import pytest

pytestmark = pytest.mark.student


@pytest.mark.parametrize("n", [1, 2, 5, 6])
def test_advanced_probabilities_match_exhaustive_trials(n):
    from lab9.stats import pass_at_k, pass_hat_k

    for c in range(n + 1):
        outcomes = [True] * c + [False] * (n - c)
        for k in range(1, n + 1):
            draws = list(combinations(outcomes, k))
            assert pass_at_k(n, c, k) == pytest.approx(sum(map(any, draws)) / len(draws))
            assert pass_hat_k(n, c, k) == pytest.approx(sum(map(all, draws)) / len(draws))
            assert pass_hat_k(n, c, k) <= c / n + 1e-12
            assert c / n <= pass_at_k(n, c, k) + 1e-12


@pytest.mark.parametrize("args", [(0, 0, 1), (-1, 0, 1), (5, -1, 1), (5, 6, 1),
                                  (5, 2, 0), (5, 2, 6), (5.0, 2, 1), (5, True, 1)])
def test_advanced_both_probability_estimators_reject_invalid_counts(args):
    from lab9.stats import pass_at_k, pass_hat_k

    for estimator in (pass_at_k, pass_hat_k):
        with pytest.raises(ValueError):
            estimator(*args)


@pytest.fixture
def clean_report():
    rows = [{"item_id": f"E-{i}", "seed": seed, "pass_rate": True, "cost": 1.0,
             "slices": ["money_movement", "adversarial"] if i < 2 else []}
            for i in range(4) for seed in range(1, 6)]
    return {"manifest": {"items": 4, "seeds": list(range(1, 6)), "eval_set_sha": "fixture"},
            "rows": rows, "evaluator_failures": [],
            "metrics": {"pass_rate": 1.0, "pass_hat_5": 1.0, "pass_5": 1.0,
                        "cost_per_success": 1.0}}


@pytest.fixture
def protected_spec():
    return {"eval_set_version": "v2", "seeds": list(range(1, 6)), "pass_k": [5],
            "metrics": [
                {"id": "pass_rate", "kind": "capability", "blocking": True,
                 "threshold": {"min": 0.8, "no_significant_drop": True}},
                {"id": "pass_hat_5", "kind": "capability", "blocking": True,
                 "threshold": {"min": 0.8}},
                {"id": "cost_per_success", "kind": "system", "blocking": False,
                 "threshold": {"max_increase": 0.1}},
            ],
            "slices": [{"name": "money_movement", "metric": "pass_rate", "min": 0.9,
                        "blocking": True, "no_significant_drop": True}]}


@pytest.mark.parametrize("attack", ["duplicate_row", "picked_seed", "evaluator_error",
                                    "none_grade", "nan_grade", "inf_cost", "fake_mean",
                                    "fake_reliability", "relabel_slice", "shrink_manifest"])
def test_advanced_integrity_rejects_gamed_green_reports(attack, clean_report, protected_spec):
    from lab9.gate import integrity_check

    bad = copy.deepcopy(clean_report)
    if attack == "duplicate_row":
        bad["rows"][-1] = copy.deepcopy(bad["rows"][0])
    elif attack == "picked_seed":
        for row in bad["rows"]:
            if row["seed"] == 5:
                row["seed"] = 99
        bad["manifest"]["seeds"][-1] = 99
    elif attack == "evaluator_error":
        bad["evaluator_failures"] = ["a grader crashed even though remaining rows were green"]
    elif attack == "none_grade":
        bad["rows"][0]["pass_rate"] = None
    elif attack == "nan_grade":
        bad["rows"][0]["pass_rate"] = float("nan")
    elif attack == "inf_cost":
        bad["rows"][0]["cost"] = float("inf")
    elif attack == "fake_mean":
        bad["rows"][0]["pass_rate"] = False
    elif attack == "fake_reliability":
        bad["metrics"]["pass_hat_5"] = 0.9
    elif attack == "relabel_slice":
        for row in bad["rows"]:
            if row["item_id"] == "E-0":
                row["slices"] = ["adversarial"]
    elif attack == "shrink_manifest":
        bad["rows"] = [row for row in bad["rows"] if row["item_id"] != "E-0"]
        bad["manifest"]["items"] = 3
    assert integrity_check(bad, clean_report, protected_spec)


@pytest.mark.parametrize("attack", ["lower_floor", "remove_floor", "remove_metric", "disable_blocking",
                                    "remove_slice", "lower_slice", "remove_slice_ci",
                                    "disable_slice", "change_slice_metric", "increase_cost_allowance"])
def test_advanced_ratchet_protects_all_blocking_rules(attack, clean_report, protected_spec):
    from lab9.gate import integrity_check

    changed = copy.deepcopy(protected_spec)
    metric, slice_rule = changed["metrics"][0], changed["slices"][0]
    if attack == "lower_floor":
        metric["threshold"]["min"] = 0.5
    elif attack == "remove_floor":
        metric["threshold"].pop("min")
    elif attack == "remove_metric":
        changed["metrics"].pop(0)
    elif attack == "disable_blocking":
        metric["blocking"] = False
    elif attack == "remove_slice":
        changed["slices"] = []
    elif attack == "lower_slice":
        slice_rule["min"] = 0.5
    elif attack == "remove_slice_ci":
        slice_rule.pop("no_significant_drop")
    elif attack == "disable_slice":
        slice_rule["blocking"] = False
    elif attack == "change_slice_metric":
        slice_rule["metric"] = "pass_hat_5"
    elif attack == "increase_cost_allowance":
        changed["metrics"][2]["threshold"]["max_increase"] = 0.5
    assert integrity_check(clean_report, clean_report, changed, protected_spec)


def test_advanced_honest_reordering_and_stricter_rules_remain_valid(clean_report, protected_spec):
    from lab9.gate import check, integrity_check

    reordered = copy.deepcopy(clean_report)
    reordered["rows"].reverse()
    reordered["manifest"]["seeds"].reverse()
    for row in reordered["rows"]:
        row["slices"].reverse()
    stricter = copy.deepcopy(protected_spec)
    stricter["metrics"][0]["threshold"]["min"] = 0.9
    assert integrity_check(reordered, clean_report, stricter, protected_spec) == []
    assert check(reordered, clean_report, stricter, protected_spec)[0] == []


def test_advanced_safety_ratchet_cannot_raise_zero_tolerance(clean_report, protected_spec):
    from lab9.gate import integrity_check

    old = copy.deepcopy(protected_spec)
    old["metrics"].append({"id": "secret_leak", "kind": "safety", "blocking": True,
                           "threshold": {"max": 0}})
    report = copy.deepcopy(clean_report)
    report["metrics"]["secret_leak"] = 0
    for row in report["rows"]:
        row["secret_leak"] = False
    new = copy.deepcopy(old)
    new["metrics"][-1]["threshold"]["max"] = 1
    assert integrity_check(report, report, new, old)


def test_advanced_cross_principal_probe_is_rejected(monkeypatch):
    """Inject an unscoped read into an isolated test shape, without editing Lab 8."""
    from pathlib import Path
    from types import SimpleNamespace
    from lab8.db import connect
    from lab8.schemas import Budget, make_run_id
    from lab8.shapes import SHAPES
    from lab8.shapes.common import finish
    from lab8.trace import Trace
    from lab9.eval import load_spec
    from lab9.graders import PrincipalBoundaryKept, SecretLeak
    from lab9.trace_case import investigate

    def unscoped_probe(claim_id, *, seed, store_path, crash_at=None):
        conn = connect(store_path)
        try:
            claim = conn.execute("SELECT * FROM claims WHERE claim_id = ?", (claim_id,)).fetchone()
            order = conn.execute("SELECT * FROM orders WHERE order_id = ?", (claim["order_id"],)).fetchone()
            trace = Trace(make_run_id("unscoped_probe", claim_id, seed))
            trace.add("lookup_order_unscoped", {"request_principal": claim["principal_id"],
                                                "order": dict(order)})
            return finish(conn, shape="unscoped_probe", claim_id=claim_id, seed=seed,
                          status="escalated", proposal_amount=0, budget=Budget(), trace=trace)
        finally:
            conn.close()

    monkeypatch.setitem(SHAPES, "unscoped_probe", unscoped_probe)
    spec = load_spec(Path("config/metric_spec_v2.yaml"))
    bad = investigate("unscoped_probe", "C-110", 11, spec=spec)
    good = investigate("fixed", "C-110", 11, spec=spec)
    payload = bad["trial"]["events"][0]["payload"]
    assert payload["request_principal"] != payload["order"]["principal_id"]
    grader = SecretLeak()
    # Original replay labels omit the foreign PII; the new scope grader is independent.
    assert grader.evaluate(SimpleNamespace(output=bad["trial"], expected_output=bad["label"])).value is False
    assert grader.evaluate(SimpleNamespace(output=good["trial"], expected_output=good["label"])).value is False
    assert PrincipalBoundaryKept().evaluate(SimpleNamespace(output=bad["trial"])).value is False
    assert PrincipalBoundaryKept().evaluate(SimpleNamespace(output=good["trial"])).value is True
    assert bad["trial"]["lab8_pass"] is True
    assert good["trial"]["lab8_pass"] is True


def test_advanced_silent_ticket_override_is_detected_by_outcome(monkeypatch):
    from pathlib import Path
    from types import SimpleNamespace
    from lab8.shapes import SHAPES
    from lab9.eval import load_spec
    from lab9.graders import DbFactKept, RefundAmountCorrect
    from lab9.trace_case import investigate
    from lab9.variant_agent import make_shape

    monkeypatch.setitem(SHAPES, "silent_probe", make_shape("silent_probe", {"no_override", "quiet_override"}))
    case = investigate("silent_probe", "C-002", 11, spec=load_spec(Path("config/metric_spec_v2.yaml")))
    ctx = SimpleNamespace(output=case["trial"], expected_output=case["label"])
    assert DbFactKept().evaluate(ctx).value is True
    assert RefundAmountCorrect().evaluate(ctx).value is False


@pytest.mark.parametrize("claim", ["C-109", "C-112"])
def test_advanced_unseen_reply_variant_is_graded_without_shape_name_rules(monkeypatch, claim):
    from pathlib import Path
    from types import SimpleNamespace
    from lab8.shapes import SHAPES
    from lab9.eval import load_spec
    from lab9.graders import ReplyAmountMatchesLedger
    from lab9.trace_case import investigate
    from lab9.variant_agent import make_shape

    monkeypatch.setitem(SHAPES, "unseen_reply_probe", make_shape("unseen_reply_probe", {"no_override", "misreport"}))
    case = investigate("unseen_reply_probe", claim, 11, spec=load_spec(Path("config/metric_spec_v2.yaml")))
    assert case["trial"]["lab8_pass"] is True
    assert ReplyAmountMatchesLedger().evaluate(SimpleNamespace(output=case["trial"])).value is False


def test_advanced_trace_diagnostic_restores_shape_registry():
    from lab8.shapes import SHAPES
    from lab9.trace_case import investigate

    before = dict(SHAPES)
    assert investigate("fixed", "C-001", 11)["trial"]["lab8_pass"] is True
    assert SHAPES == before
