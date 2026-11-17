"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
from numbers import Integral
import math

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    if len(human) != len(judge):
        raise ValueError("human and judge must have the same length")
    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for expected, predicted in zip(human, judge):
        if expected not in ("PASS", "FAIL") or predicted not in ("PASS", "FAIL"):
            raise ValueError("labels must be PASS or FAIL")
        if predicted == POS:
            key = "tp" if expected == POS else "fp"
        else:
            key = "fn" if expected == POS else "tn"
        counts[key] += 1
    return counts


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    cm = confusion(human, judge)
    predicted_positive = cm["tp"] + cm["fp"]
    actual_positive = cm["tp"] + cm["fn"]
    precision = cm["tp"] / predicted_positive if predicted_positive else 0.0
    recall = cm["tp"] / actual_positive if actual_positive else 0.0
    return precision, recall


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """Chance-corrected agreement; raise ValueError when undefined."""
    cm = confusion(human, judge)
    n = len(human)
    if not n:
        raise ValueError("kappa requires at least one labelled item")
    observed_agreements = cm["tp"] + cm["tn"]
    expected_numerator = (
        (cm["tp"] + cm["fn"]) * (cm["tp"] + cm["fp"])
        + (cm["tn"] + cm["fp"]) * (cm["tn"] + cm["fn"])
    )
    # (p_o - p_e) / (1 - p_e), multiplied through by n squared.
    denominator = n * n - expected_numerator
    if denominator == 0:
        raise ValueError("kappa is undefined when expected agreement is 1")
    return (n * observed_agreements - expected_numerator) / denominator


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    if not all(math.isfinite(v) and 0.0 <= v <= 1.0
               for v in (observed_rate, sensitivity, specificity)):
        raise ValueError("rates must be finite probabilities in [0, 1]")
    denominator = sensitivity + specificity - 1.0
    if denominator == 0.0:
        raise ValueError("Rogan-Gladen is undefined when sensitivity + specificity = 1")
    corrected = (observed_rate + specificity - 1.0) / denominator
    return min(1.0, max(0.0, corrected))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    import numpy as np
    from scipy.stats import bootstrap

    pr, base = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if pr.ndim != 1 or base.ndim != 1 or pr.size != base.size or not pr.size:
        raise ValueError("paired samples must be non-empty 1D arrays of equal length")
    if not np.isfinite(pr).all() or not np.isfinite(base).all():
        raise ValueError("paired samples must contain only finite values")
    if isinstance(n_resamples, bool) or not isinstance(n_resamples, int) or n_resamples < 1:
        raise ValueError("n_resamples must be a positive integer")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be strictly between 0 and 1")
    if np.array_equal(pr, base):
        return 0.0, 0.0, 0.0
    delta = float(pr.mean() - base.mean())
    if pr.size == 1:
        return delta, delta, delta

    def difference(x, y, axis=-1):
        return np.mean(x, axis=axis) - np.mean(y, axis=axis)

    result = bootstrap(
        (pr, base), difference, paired=True, vectorized=True,
        n_resamples=n_resamples, method="percentile", confidence_level=confidence,
        rng=np.random.default_rng(rng),
    )
    return delta, float(result.confidence_interval.low), float(result.confidence_interval.high)


def _validate_pass_counts(n: int, c: int, k: int) -> None:
    if any(isinstance(value, bool) or not isinstance(value, Integral) for value in (n, c, k)):
        raise ValueError("n, c and k must be integers")
    if n < 1 or not 0 <= c <= n or not 1 <= k <= n:
        raise ValueError("require n >= 1, 0 <= c <= n and 1 <= k <= n")


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    _validate_pass_counts(n, c, k)
    n, c, k = int(n), int(c), int(k)
    if n - c < k:
        return 1.0
    # log1p/expm1 avoids cancellation when successes are rare.
    return -math.expm1(sum(math.log1p(-c / (n - i)) for i in range(k)))


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    _validate_pass_counts(n, c, k)
    n, c, k = int(n), int(c), int(k)
    return 0.0 if c < k else math.comb(c, k) / math.comb(n, k)
