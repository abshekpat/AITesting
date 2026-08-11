"""Local run history for the dashboard.

Every metric evaluation — whether triggered from the dashboard UI or from a
`pytest` / `deepeval test run` invocation — is appended here as one JSON line.
The "Runs" tab reads this back, grouped into sessions, so you can see each
chatbot run (answer relevancy, faithfulness, hallucination, bias, toxicity,
correctness, PII leakage) on a date/time basis WITHOUT going to Confident AI.

Storage: dashboard/runs.jsonl  (one JSON object per metric case, append-only).
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

RUNS_PATH = Path(__file__).resolve().parent / "runs.jsonl"

# Display order + canonical names for the chatbot metric family the user tracks.
CHATBOT_METRIC_ORDER = [
    "chatbot.answer_relevancy",
    "chatbot.faithfulness",
    "chatbot.hallucination",
    "chatbot.bias",
    "chatbot.toxicity",
    "chatbot.correctness",
    "chatbot.pii_leakage",
    "browserbash.answer_relevancy",
    "browserbash.faithfulness",
    "browserbash.hallucination",
    "browserbash.bias",
    "browserbash.toxicity",
    "browserbash.correctness",
    "browserbash.pii_leakage",
]

# Map a DeepEval metric_data "name" (as seen in .deepeval cache) -> (metric_id, category).
NAME_TO_METRIC = {
    "answer relevancy": ("chatbot.answer_relevancy", "quality"),
    "faithfulness": ("chatbot.faithfulness", "quality"),
    "hallucination": ("chatbot.hallucination", "quality"),
    "bias": ("chatbot.bias", "safety"),
    "toxicity": ("chatbot.toxicity", "safety"),
    "correctness": ("chatbot.correctness", "geval"),
    "pii": ("chatbot.pii_leakage", "safety"),
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def record(rec: dict[str, Any]) -> None:
    """Append one case record. Missing ts/run_id are filled in."""
    rec = dict(rec)
    rec.setdefault("ts", now_iso())
    rec.setdefault("run_id", "run-" + rec["ts"])
    RUNS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RUNS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def record_many(recs: Iterable[dict[str, Any]]) -> int:
    n = 0
    for r in recs:
        record(r)
        n += 1
    return n


def load() -> list[dict[str, Any]]:
    if not RUNS_PATH.exists():
        return []
    out = []
    for line in RUNS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _passed(score: float, threshold: float, higher_is_better: bool) -> bool:
    return score >= threshold if higher_is_better else score <= threshold


def map_metric_name(name: str) -> tuple[str, str] | None:
    """Best-effort map a DeepEval metric name -> (metric_id, category)."""
    n = (name or "").lower()
    for key, val in NAME_TO_METRIC.items():
        if key in n:
            return val
    return None


def sessions(target: str | None = None) -> list[dict[str, Any]]:
    """Group case records into sessions (by run_id), newest first."""
    recs = load()
    if target and target != "all":
        recs = [r for r in recs if r.get("target") == target]

    groups: dict[str, list[dict]] = {}
    for r in recs:
        groups.setdefault(r.get("run_id", "?"), []).append(r)

    out = []
    for run_id, cases in groups.items():
        by_metric: dict[str, dict] = {}
        for c in cases:
            mid = c.get("metric_id", "unknown")
            m = by_metric.setdefault(mid, {
                "metric_id": mid,
                "metric": c.get("metric", mid),
                "category": c.get("category", ""),
                "threshold": c.get("threshold"),
                "higher_is_better": c.get("higher_is_better", True),
                "cases": [],
            })
            m["cases"].append({
                "input": c.get("input", ""),
                "actual_output": c.get("actual_output", ""),
                "score": c.get("score"),
                "passed": c.get("passed"),
                "reason": c.get("reason", ""),
            })

        metrics = []
        for m in by_metric.values():
            scs = [x["score"] for x in m["cases"] if isinstance(x["score"], (int, float))]
            passed = sum(1 for x in m["cases"] if x["passed"])
            metrics.append({
                **m,
                "total": len(m["cases"]),
                "passed": passed,
                "failed": len(m["cases"]) - passed,
                "avg": round(sum(scs) / len(scs), 3) if scs else None,
            })
        # canonical order, unknowns last
        order = {mid: i for i, mid in enumerate(CHATBOT_METRIC_ORDER)}
        metrics.sort(key=lambda x: order.get(x["metric_id"], 99))

        ts = min((c.get("ts", "") for c in cases), default="")
        total = sum(m["total"] for m in metrics)
        passed = sum(m["passed"] for m in metrics)
        out.append({
            "run_id": run_id,
            "ts": ts,
            "source": cases[0].get("source", "run"),
            "judge": cases[0].get("judge", ""),
            "target": cases[0].get("target", ""),
            "metrics": metrics,
            "total": total,
            "passed": passed,
            "failed": total - passed,
        })

    out.sort(key=lambda s: s["ts"], reverse=True)
    return out


def cache_records(run_id: str, source: str, judge: str,
                  keys_to_skip: set[str] | None = None,
                  ts: str | None = None) -> list[dict[str, Any]]:
    """Read the DeepEval cache and turn chatbot metric results into case records.

    `keys_to_skip` lets a caller capture only the delta produced this session.
    Returns records (NOT yet written) so the caller controls persistence.
    """
    cache_path = Path(__file__).resolve().parent.parent / ".deepeval" / ".deepeval-cache.json"
    if not cache_path.exists():
        return []
    try:
        lut = json.loads(cache_path.read_text(encoding="utf-8"))["test_cases_lookup_map"]
    except Exception:
        return []
    keys_to_skip = keys_to_skip or set()
    ts = ts or now_iso()
    recs = []
    for key, val in lut.items():
        if key in keys_to_skip:
            continue
        try:
            tc = json.loads(key)
        except Exception:
            continue
        for cm in val.get("cached_metrics_data", []):
            md = cm.get("metric_data", {})
            mapped = map_metric_name(md.get("name", ""))
            if not mapped:
                continue
            metric_id, category = mapped
            recs.append({
                "ts": ts,
                "run_id": run_id,
                "source": source,
                "target": "chatbot",
                "metric_id": metric_id,
                "metric": md.get("name", metric_id),
                "category": category,
                "score": round(md.get("score", 0.0), 4),
                "threshold": md.get("threshold"),
                "higher_is_better": _hib(metric_id),
                "passed": bool(md.get("success")),
                "reason": md.get("reason", ""),
                "input": tc.get("input", ""),
                "actual_output": tc.get("actual_output", ""),
                "judge": (md.get("evaluationModel") or judge or ""),
            })
    return recs


def cache_keys() -> set[str]:
    """Snapshot the current set of cache test-case keys (for delta capture)."""
    cache_path = Path(__file__).resolve().parent.parent / ".deepeval" / ".deepeval-cache.json"
    if not cache_path.exists():
        return set()
    try:
        return set(json.loads(cache_path.read_text(encoding="utf-8"))["test_cases_lookup_map"].keys())
    except Exception:
        return set()


_LOWER_IS_BETTER = {"chatbot.hallucination", "chatbot.bias", "chatbot.toxicity", "chatbot.pii_leakage"}


def _hib(metric_id: str) -> bool:
    return metric_id not in _LOWER_IS_BETTER
