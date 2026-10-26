#!/usr/bin/env python3
"""Summarize all runs in a phase folder into one table (prints it and writes summary.csv).

Usage: python3 summarize.py /data/runs/phase0
"""
import csv, json, os, sys

root = sys.argv[1] if len(sys.argv) > 1 else "/data/runs/phase0"
rows = []
for name in sorted(os.listdir(root)):
    d = os.path.join(root, name)
    rj = os.path.join(d, "run.json")
    if not os.path.isfile(rj):
        continue
    r = json.load(open(rj))
    det = json.load(open(os.path.join(d, "detection.json"))) if os.path.isfile(os.path.join(d, "detection.json")) else {}
    row = {
        "run": r.get("run_id"), "valid": r.get("valid"),
        "pcap": os.path.basename(r.get("pcap", "")).split("-")[0],
        "base": r.get("hashes", {}).get("base_yaml", "")[:8],
        "levels": json.dumps(r.get("levels", {}), separators=(",", ":")),
        "proc_cpu_s": round(r["processing_cpu_s"], 1) if r.get("processing_cpu_s") is not None else "",
        "startup_cpu_s": round(r["startup"]["cpu_s"], 1) if r.get("startup") else "",
        "calib_drift": round(r["calib_drift"], 3) if r.get("calib_drift") is not None else "",
        "calib_s": round(max(r["calib_before_s"], r["calib_after_s"]), 2) if r.get("calib_before_s") else "",
        "disturbed": r.get("disturbed", ""),
        "rss_mb": round(r["main"]["peak_rss_mb"]) if r.get("main") else "",
        "alerts": r.get("n_alerts"),
        "benign_alerts": det.get("alerts_on_benign", ""),
        "macro_recall": round(det["macro_recall"], 3) if det.get("macro_recall") is not None else "",
        "macro_win": round(det["macro_window_recall"], 3) if det.get("macro_window_recall") is not None else "",
    }
    for cls, v in det.get("per_class", {}).items():
        row["R:" + cls] = "" if v["recall"] is None else round(v["recall"], 3)
        if v.get("window_recall") is not None:
            row["W:" + cls] = round(v["window_recall"], 3)
    rows.append(row)

cols = []
for row in rows:
    cols += [k for k in row if k not in cols]
with open(os.path.join(root, "summary.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)

short = ["run", "pcap", "levels", "proc_cpu_s", "calib_s", "disturbed", "rss_mb", "benign_alerts", "macro_recall", "macro_win"]
print(" | ".join(short))
for row in rows:
    print(" | ".join(str(row.get(c, "")) for c in short))
print(f"\nFull table with per-class recall: {os.path.join(root, 'summary.csv')}")
