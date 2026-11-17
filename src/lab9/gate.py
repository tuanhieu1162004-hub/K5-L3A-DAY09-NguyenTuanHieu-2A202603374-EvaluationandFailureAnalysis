"""Paired evaluation gate with slice checks, report integrity and spec ratchets."""
from __future__ import annotations

import argparse
import json
import math
import re
from numbers import Real
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, aggregate, load_spec, per_item
from lab9.graders import GRADERS


def _finite(value) -> bool:
    return isinstance(value, Real) and math.isfinite(value)


def _report_problems(report: dict, name: str, spec: dict):
    """Validate one complete Cartesian grid and verify its published aggregates."""
    problems, pairs, item_tags = [], set(), {}
    if not isinstance(report, dict):
        return [f"{name}: report must be an object"], pairs, item_tags
    manifest, rows, metrics = (report.get(k) for k in ("manifest", "rows", "metrics"))
    if not isinstance(manifest, dict) or not isinstance(rows, list) or not isinstance(metrics, dict):
        return [f"{name}: missing manifest/rows/metrics"], pairs, item_tags
    failures = report.get("evaluator_failures")
    if not isinstance(failures, list) or failures:
        problems.append(f"{name}: evaluator_failures must be an empty list")
    if not isinstance(manifest.get("eval_set_sha"), str) or not manifest["eval_set_sha"]:
        problems.append(f"{name}: missing eval_set_sha")
    items, seeds = manifest.get("items"), manifest.get("seeds")
    if isinstance(items, bool) or not isinstance(items, int) or items < 1:
        return problems + [f"{name}: invalid manifest item count"], pairs, item_tags
    if (not isinstance(seeds, list) or not seeds
            or any(isinstance(s, bool) or not isinstance(s, int) for s in seeds)):
        return problems + [f"{name}: invalid manifest seeds"], pairs, item_tags
    if len(set(seeds)) != len(seeds):
        problems.append(f"{name}: duplicate manifest seeds")
    if spec.get("seeds") is not None and set(seeds) != set(spec["seeds"]):
        problems.append(f"{name}: seeds differ from the spec")
    if len(rows) != items * len(seeds):
        problems.append(f"{name}: row count {len(rows)} != items x seeds ({items * len(seeds)})")

    spec_ids = {m["id"] for m in spec.get("metrics", [])}
    required = {m["id"] for m in spec.get("metrics", [])
                if m.get("blocking") or m["id"] in GRADERS}
    for mid in required:
        if mid not in metrics or metrics[mid] is None:
            problems.append(f"{name}: missing aggregate {mid}")
    for mid, value in metrics.items():
        # A cost per success can legitimately be undefined when nothing passes.
        if value is not None and not _finite(value):
            problems.append(f"{name}: non-finite/non-numeric metric {mid}")
    graded = sorted((spec_ids | set(metrics)) & GRADERS.keys())
    need_cost = "cost_per_success" in metrics and metrics["cost_per_success"] is not None
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            problems.append(f"{name}: row {index} is not an object")
            continue
        item, seed = row.get("item_id"), row.get("seed")
        if (not isinstance(item, str) or not item or isinstance(seed, bool)
                or not isinstance(seed, int)):
            problems.append(f"{name}: invalid item/seed at row {index}")
            continue
        pair = (item, seed)
        if pair in pairs:
            problems.append(f"{name}: duplicate item/seed {pair}")
        pairs.add(pair)
        if seed not in seeds:
            problems.append(f"{name}: undeclared seed {pair}")
        tags = row.get("slices", [])
        if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
            problems.append(f"{name}: malformed slice tags at {pair}")
        else:
            tag_set = frozenset(tags)
            if len(tags) != len(tag_set):
                problems.append(f"{name}: duplicate slice tag at {pair}")
            if item in item_tags and item_tags[item] != tag_set:
                problems.append(f"{name}: inconsistent slice tags for {item}")
            item_tags[item] = tag_set
        for mid in graded:
            value = row.get(mid)
            if not _finite(value) or not 0 <= value <= 1:
                problems.append(f"{name}: missing/invalid grade {mid} at {pair}")
        if "cost" in row or need_cost:
            if not _finite(row.get("cost")) or row["cost"] < 0:
                problems.append(f"{name}: missing/invalid cost at {pair}")
    item_ids = {item for item, _ in pairs}
    if len(item_ids) != items:
        problems.append(f"{name}: unique item count differs from manifest")
    if pairs != {(item, seed) for item in item_ids for seed in seeds}:
        problems.append(f"{name}: incomplete item x seed grid")

    if not problems:
        k_values = set(spec.get("pass_k", []))
        for mid in metrics:
            match = re.fullmatch(r"pass_(?:at|hat)_(\d+)", mid)
            if match:
                k_values.add(int(match.group(1)))
        try:
            # Minimal in-memory fixtures need no cost unless they publish cost metrics.
            normalized_rows = [{"cost": 0.0, **row} for row in rows]
            recomputed = aggregate(normalized_rows, graded, k_values=sorted(k_values))
            for mid, actual in metrics.items():
                if mid not in recomputed:
                    continue
                expected = recomputed[mid]
                if actual is None or expected is None:
                    same = actual is expected
                else:
                    same = math.isclose(actual, expected, rel_tol=1e-9, abs_tol=5e-5)
                if not same:
                    problems.append(f"{name}: aggregate {mid} disagrees with rows")
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            problems.append(f"{name}: cannot recompute aggregates ({type(exc).__name__})")
    return problems, pairs, item_tags


def _ratchet_problems(spec: dict, base_spec: dict | None) -> list[str]:
    if base_spec is None or spec.get("eval_set_version") != base_spec.get("eval_set_version"):
        return []
    problems = []

    def bounds(old, new, context):
        for key in ("min", "max", "max_increase"):
            if key not in old:
                continue
            value = new.get(key)
            if not _finite(value):
                problems.append(f"RATCHET {context}: removed/invalid {key}")
            elif (key == "min" and value < old[key]) or (key != "min" and value > old[key]):
                problems.append(f"RATCHET {context}: loosened {key}")
        if old.get("no_significant_drop") and not new.get("no_significant_drop"):
            problems.append(f"RATCHET {context}: removed no_significant_drop")

    for group, key in (("metrics", "id"), ("slices", "name")):
        current = {entry[key]: entry for entry in spec.get(group, [])}
        if len(current) != len(spec.get(group, [])):
            problems.append(f"RATCHET: duplicate {group} identifiers")
        for old in base_spec.get(group, []):
            identifier = old[key]
            new = current.get(identifier)
            context = f"{group}:{identifier}"
            if new is None:
                problems.append(f"RATCHET {context}: removed")
                continue
            if old.get("blocking") and not new.get("blocking"):
                problems.append(f"RATCHET {context}: disabled blocking")
            if group == "slices":
                if old.get("metric") != new.get("metric"):
                    problems.append(f"RATCHET {context}: changed metric")
                bounds(old, new, context)
            else:
                if old.get("kind") != new.get("kind"):
                    problems.append(f"RATCHET {context}: changed metric kind")
                bounds(old.get("threshold", {}), new.get("threshold", {}), context)
    return problems


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    problems = _ratchet_problems(spec, base_spec)
    pr_errors, pr_pairs, pr_tags = _report_problems(pr, "PR", spec)
    base_errors, base_pairs, base_tags = _report_problems(base, "baseline", spec)
    problems.extend(pr_errors)
    problems.extend(base_errors)
    if pr_pairs != base_pairs:
        problems.append("PR item/seed set differs from baseline (dropped or cherry-picked trials)")
    for item in pr_tags.keys() & base_tags.keys():
        if pr_tags[item] != base_tags[item]:
            problems.append(f"PR slice tags differ from baseline for {item}")
    if isinstance(pr, dict) and isinstance(base, dict):
        pm, bm = pr.get("manifest", {}), base.get("manifest", {})
        if isinstance(pm, dict) and isinstance(bm, dict):
            if pm.get("items") != bm.get("items"):
                problems.append("PR manifest item count differs from baseline")
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for entry in spec.get("slices", []):
        name, metric = entry["name"], entry["metric"]
        identifier = f"slice:{name}/{metric}"
        a, b = per_item(pr, metric, slice_name=name), per_item(base, metric, slice_name=name)
        failed, note, value = False, "", None
        if not a or set(a) != set(b):
            failed, note = True, "missing or unaligned slice items"
        else:
            keys = sorted(a)
            value = sum(a.values()) / len(a)
            failed = not math.isfinite(value) or ("min" in entry and value < entry["min"])
            if entry.get("no_significant_drop"):
                delta, lo, hi = stats.paired_bootstrap(
                    [a[k] for k in keys], [b[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                    confidence=bs.get("confidence", 0.95),
                )
                note = f"Δ {delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                failed = failed or hi < 0
        if failed and entry.get("blocking"):
            blocked.append(identifier)
        verdict = "BLOCK" if failed and entry.get("blocking") else "warn" if failed else "ok"
        lines.append(f"  {identifier:<42} {value!s:<8} {note:<32} {verdict}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from baseline: re-run the baseline on the same eval set"]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for metric in spec["metrics"]:
        mid, th = metric["id"], metric.get("threshold", {})
        value = pr["metrics"].get(mid)
        failed, note = value is None, ""
        if value is not None:
            failed = ("max" in th and value > th["max"]) or ("min" in th and value < th["min"])
            if "max_increase" in th and base["metrics"].get(mid):
                failed = failed or value > base["metrics"][mid] * (1 + th["max_increase"])
            if th.get("no_significant_drop"):
                a, b = per_item(pr, mid), per_item(base, mid)
                keys = sorted(a)
                if not keys or set(a) != set(b):
                    failed, note = True, "missing or unaligned paired items"
                else:
                    delta, lo, hi = stats.paired_bootstrap(
                        [a[k] for k in keys], [b[k] for k in keys],
                        n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                        confidence=bs.get("confidence", 0.95),
                    )
                    note = f"Δ {delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                    failed = failed or hi < 0
        if failed and metric.get("blocking"):
            blocked.append(mid)
        verdict = "BLOCK" if failed and metric.get("blocking") else "warn" if failed else "ok"
        lines.append(f"  {mid:<28} {value!s:<9} {json.dumps(th):<48} {note:<32} {verdict}")
    sb, sl = slice_check(pr, base, spec)
    return blocked + sb, lines + sl


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(prog="lab9.gate")
    parser.add_argument("--pr", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--spec", default=str(SPEC))
    parser.add_argument("--base-spec", help="trusted baseline metric spec for the ratchet check")
    args = parser.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr.get('run_id', '?')} vs main {base.get('run_id', '?')}")
    print("\n".join(lines))
    print(f"exit 1 — blocked: {', '.join(blocked)}" if blocked else "exit 0 — merge")
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
