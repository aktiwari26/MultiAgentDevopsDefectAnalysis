"""Evaluate the pipeline against the labelled cases in eval/cases.py.

Offline (default, no API key, deterministic):
    python -m eval.run_eval                      # BM25 retrieval (current)
    python -m eval.run_eval --scorer legacy      # original keyword scorer (baseline)
  Reports retrieval recall@1 / recall@k / MRR over cases that have expected KB
  sources, and the keyword log-type heuristic's accuracy.

Live (calls the real LLMs through OpenRouter; costs tokens):
    python -m eval.run_eval --mode live [--limit 5] [--ids pg_deadlock,k8s_oomkilled]
  Runs the full graph per case (Jira/notification forced to mock, dedup off) and
  reports severity accuracy (exact / within one level), the share of cases fooled
  by an injected instruction, log-type accuracy (LLM label), root-cause keyword
  hit-rate, and latency (sum of per-node elapsed_s; mean and p95). Token and cost
  tracking are not measured.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
import uuid
from pathlib import Path

from eval.cases import CASES

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _select(cases, ids, limit):
    if ids:
        wanted = set(ids.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    return cases[:limit] if limit else cases


def _pct(x: float) -> str:
    return f"{100 * x:5.1f}%"


# ── offline: retrieval + log-type heuristic ────────────────────────────────

def _parse_expected(entries):
    """'Doc' -> (doc, None); 'Doc::text' -> (doc, 'text')."""
    out = []
    for e in entries:
        src, _, heading = e.partition("::")
        out.append((src, heading or None))
    return out


def retrieval_hits(case, scorer: str, k: int):
    """Top-k hits as {'source','title','chars'} for this case's query."""
    from devops_rag import WHOLE_KB_DOCS, build_rag_query, retrieve

    query = build_rag_query(case["log_type"], [], "", case["log"])
    if scorer == "legacy":
        from eval.legacy_retrieval import legacy_search
        docs = legacy_search(query, WHOLE_KB_DOCS, top_k=k)
        return [{"source": d["title"], "title": d["title"], "chars": len(d["content"])} for d in docs]
    hits = retrieve(query, top_k=k)
    return [{"source": h["source"], "title": h["title"], "chars": min(len(h["content"]), 1500)} for h in hits]


def _first_rank(hits, expected, passage_level: bool):
    for i, h in enumerate(hits, start=1):
        for src, heading in expected:
            if h["source"] != src:
                continue
            if not passage_level or heading is None or heading.lower() in h["title"].lower():
                return i
    return None


def run_offline(args) -> dict:
    from devops_parsers import detect_log_type

    cases = _select(CASES, args.ids, args.limit)
    rows = []
    for case in cases:
        if not case["expected_sources"]:
            continue
        expected = _parse_expected(case["expected_sources"])
        hits = retrieval_hits(case, args.scorer, args.k)
        rows.append({
            "id": case["id"],
            "source_rank": _first_rank(hits, expected, passage_level=False),
            # whole-document results cannot be judged at passage level; legacy
            # gets the lenient source-level rank here
            "passage_rank": _first_rank(hits, expected, passage_level=args.scorer != "legacy"),
            "context_chars": sum(h["chars"] for h in hits),
            "top_is_playbooks": bool(hits) and hits[0]["source"] == "Remediation Playbooks",
            "hits": [h["title"] for h in hits],
        })

    n = len(rows)

    def rate(key, k):
        return sum(1 for r in rows if r[key] is not None and r[key] <= k) / n if n else 0.0

    def mrr(key):
        return sum(1 / r[key] for r in rows if r[key]) / n if n else 0.0

    type_hits = sum(detect_log_type(c["log"]) == c["log_type"] for c in cases)
    k = args.k
    result = {
        "mode": "offline", "scorer": args.scorer, "k": k, "retrieval_cases": n,
        "source_recall@1": rate("source_rank", 1), f"source_recall@{k}": rate("source_rank", k),
        "passage_recall@1": rate("passage_rank", 1), f"passage_recall@{k}": rate("passage_rank", k),
        f"passage_mrr@{k}": mrr("passage_rank"),
        "avg_context_chars": statistics.mean(r["context_chars"] for r in rows) if rows else 0,
        "top1_is_catch_all_playbooks": sum(r["top_is_playbooks"] for r in rows) / n if n else 0.0,
        "heuristic_log_type_accuracy": type_hits / len(cases) if cases else 0.0,
        "log_type_cases": len(cases),
        "per_case": rows,
    }

    note = " (whole documents: lenient source-level)" if args.scorer == "legacy" else ""
    print(f"Scorer: {args.scorer}   retrieval cases: {n}   k={k}")
    print(f"  source recall@1 / @{k}        {_pct(result['source_recall@1'])} / {_pct(result[f'source_recall@{k}'])}")
    print(f"  passage recall@1 / @{k}       {_pct(result['passage_recall@1'])} / {_pct(result[f'passage_recall@{k}'])}{note}")
    print(f"  passage MRR@{k}               {result[f'passage_mrr@{k}']:.3f}")
    print(f"  avg context returned         {result['avg_context_chars']:.0f} chars")
    print(f"  top-1 is catch-all playbooks {_pct(result['top1_is_catch_all_playbooks'])}")
    print(f"  heuristic log-type accuracy  {_pct(result['heuristic_log_type_accuracy'])} ({type_hits}/{len(cases)})")
    if args.verbose:
        for r in rows:
            print(f"    {r['id']:26s} src@{r['source_rank']} psg@{r['passage_rank']}  {r['hits']}")
    return result


# ── live: full pipeline ────────────────────────────────────────────────────

def run_live(args) -> dict:
    from api.main import AnalyzeRequest, _build_request_graph
    from devops_state import base_state

    cases = _select(CASES, args.ids, args.limit)
    extra = {"dedup": False} if "dedup" in AnalyzeRequest.model_fields else {}
    rows = []
    for case in cases:
        payload = AnalyzeRequest(raw_logs=case["log"], jira_mock=True, notif_mock=True, **extra)
        graph = _build_request_graph(payload)
        started = time.time()
        error = None
        try:
            state = graph.invoke(base_state(case["log"], {"source": "eval", "request_id": str(uuid.uuid4())}))
        except Exception as exc:  # keep going; record the failure
            state, error = {}, str(exc)
        wall = time.time() - started

        sev = state.get("severity", "")
        expected_n, got_n = int(case["severity"][1]), int(sev[1]) if sev[:1] == "P" and sev[1:].isdigit() else 0
        text = f"{state.get('root_cause_analysis', '')}\n{state.get('remediation_plan', '')}".lower()
        kws = case["rca_keywords"]
        kw_hit = (sum(bool(re.search(k, text)) for k in kws) / len(kws)) if kws else None
        status = state.get("pipeline_status", {})
        rows.append({
            "id": case["id"],
            "severity_expected": case["severity"], "severity_got": sev,
            "severity_exact": sev == case["severity"],
            "severity_within_1": bool(got_n) and abs(got_n - expected_n) <= 1,
            "fooled": sev in case.get("forbidden_severity", []),
            "has_forbidden": "forbidden_severity" in case,
            "log_type_expected": case["log_type"], "log_type_got": state.get("log_type"),
            "rca_keyword_hit": kw_hit,
            "latency_s": round(sum(v.get("elapsed_s", 0) for v in status.values() if isinstance(v, dict)), 2),
            "wall_s": round(wall, 2),
            "errors": state.get("errors", []) or ([error] if error else []),
        })
        print(f"  {case['id']:28s} sev {case['severity']}->{sev or '?':3s}  type {case['log_type']}->{state.get('log_type')}  "
              f"kw {('%.0f%%' % (100 * kw_hit)) if kw_hit is not None else ' - '}  {rows[-1]['latency_s']}s")

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return statistics.mean(vals) if vals else 0.0

    lat = sorted(r["latency_s"] for r in rows)
    inj = [r for r in rows if r["has_forbidden"]]
    result = {
        "mode": "live", "cases": len(rows),
        "severity_exact": mean([r["severity_exact"] for r in rows]),
        "severity_within_1": mean([r["severity_within_1"] for r in rows]),
        "injection_cases": len(inj),
        "injection_fooled": mean([r["fooled"] for r in inj]) if inj else None,
        "log_type_accuracy": mean([r["log_type_got"] == r["log_type_expected"] for r in rows]),
        "rca_keyword_hit_rate": mean([r["rca_keyword_hit"] for r in rows]),
        "latency_mean_s": mean(lat),
        "latency_p95_s": lat[min(len(lat) - 1, int(0.95 * len(lat)))] if lat else 0.0,
        "runs_with_errors": sum(bool(r["errors"]) for r in rows),
        "per_case": rows,
    }
    print("\nLive summary")
    print(f"  severity exact       {_pct(result['severity_exact'])}")
    print(f"  severity within 1    {_pct(result['severity_within_1'])}")
    if inj:
        print(f"  injection fooled     {_pct(result['injection_fooled'])} of {len(inj)} case(s)")
    print(f"  log-type accuracy    {_pct(result['log_type_accuracy'])}")
    print(f"  RCA keyword hit-rate {_pct(result['rca_keyword_hit_rate'])}")
    print(f"  latency mean / p95   {result['latency_mean_s']:.1f}s / {result['latency_p95_s']:.1f}s (LLM stages, excl. integrations)")
    print(f"  runs with errors     {result['runs_with_errors']}")

    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"live_{time.strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"  saved {path.relative_to(ROOT)}")
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode", choices=["offline", "live"], default="offline")
    p.add_argument("--scorer", choices=["bm25", "legacy"], default="bm25", help="offline retrieval scorer")
    p.add_argument("--k", type=int, default=3)
    p.add_argument("--ids", help="comma-separated case ids")
    p.add_argument("--limit", type=int)
    p.add_argument("--json", help="also write the result to this path")
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args(argv)

    result = run_live(args) if args.mode == "live" else run_offline(args)
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    main()
