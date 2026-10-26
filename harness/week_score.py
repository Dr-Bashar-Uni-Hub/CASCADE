#!/usr/bin/env python3
"""Combine the five day runs of one configuration into week-level detection.

Usage: python3 week_score.py /data/runs/phase1/C001_mon /data/runs/phase1/C001_tue ... [--out week.json]
Macro window recall = unweighted mean of window recall over all attack classes in the given runs.
"""
import argparse, json, os

ap = argparse.ArgumentParser()
ap.add_argument("runs", nargs="+")
ap.add_argument("--out")
a = ap.parse_args()
per_class, benign, unmatched, total = {}, 0, 0, 0
for d in a.runs:
    det = json.load(open(os.path.join(d, "detection.json")))
    for c, v in det["per_class"].items():
        if c in per_class:
            raise SystemExit(f"class {c} appears in more than one run")
        per_class[c] = v
    benign += det["alerts_on_benign"]; unmatched += det["alerts_unmatched"]; total += det["alerts_total"]
w = [v["window_recall"] for v in per_class.values() if v.get("window_recall") is not None]
f = [v["recall"] for v in per_class.values() if v.get("recall") is not None]
res = {"runs": a.runs, "classes": len(per_class),
       "macro_window_recall": sum(w) / len(w) if w else None,
       "macro_flow_recall": sum(f) / len(f) if f else None,
       "episodes_detected": sum(v["episodes_detected"] for v in per_class.values()),
       "episodes": sum(v["episodes"] for v in per_class.values()),
       "alerts_total": total, "alerts_on_benign": benign, "alerts_unmatched": unmatched,
       "per_class_window_recall": {c: v.get("window_recall") for c, v in sorted(per_class.items())}}
if a.out:
    json.dump(res, open(a.out, "w"), indent=1)
print(json.dumps({k: res[k] for k in ["classes", "macro_window_recall", "macro_flow_recall",
                                      "episodes_detected", "episodes", "alerts_on_benign"]}, indent=1))
for c, v in res["per_class_window_recall"].items():
    print(f"  {c:30s} {v if v is None else round(v, 3)}")
