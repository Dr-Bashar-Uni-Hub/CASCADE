#!/usr/bin/env python3
"""Window-length sensitivity of macro window recall (re-analysis of existing alerts; no Suricata runs).

For every configuration folder with five day runs (monday ... friday), reads the already matched
alerts (matched_alerts.csv) and recomputes window recall for several window lengths, using the
same rules as label_match.py: real (non-attempted) attack flows only, a window counts as detected
if at least one of that class's real flows starting in it raised an alert.

Usage:
  python3 window_sensitivity.py --runs /data/runs/main /data/runs/verify --out /data/runs/window_sensitivity.csv
Check: the 60 s column must reproduce week.json (the script reports the largest difference).
"""
import argparse, csv, json, os, sys
import pandas as pd

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]
COLS = ["id", "Timestamp", "Label", "Attempted Category"]


def load_day(labels_dir, day):
    df = pd.read_csv(os.path.join(labels_dir, f"{day}.csv"), usecols=COLS, low_memory=False)
    t0 = pd.to_datetime(df["Timestamp"], format="mixed")
    df["start"] = (t0 - pd.Timestamp("1970-01-01")).dt.total_seconds()
    att = (df["Attempted Category"] != -1) | df["Label"].str.contains("Attempted", case=False)
    df["cls"] = df["Label"].str.replace(r"\s*-\s*Attempted$", "", regex=True).str.strip()
    real = df[(~att) & (df["cls"].str.upper() != "BENIGN")]
    return {int(i): (c, s) for i, c, s in zip(real["id"], real["cls"], real["start"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--labels-dir", default="/data/labels")
    ap.add_argument("--windows", default="30,60,120,300")
    ap.add_argument("--out", default="/data/runs/window_sensitivity.csv")
    a = ap.parse_args()
    windows = [float(w) for w in a.windows.split(",")]

    print("loading labels ...", flush=True)
    real = {d: load_day(a.labels_dir, d) for d in DAYS}
    allwin = {}                                            # (cls, W) -> set of active windows
    for d in DAYS:
        for c, s in real[d].values():
            for W in windows:
                allwin.setdefault((c, W), set()).add(int(s // W))
    classes = sorted({c for c, _ in allwin})
    print(f"{len(classes)} attack classes", flush=True)

    rows, maxdiff, n = [], 0.0, 0
    for root in a.runs:
        for cid in sorted(os.listdir(root)):
            base = os.path.join(root, cid)
            files = [os.path.join(base, d, "matched_alerts.csv") for d in DAYS]
            if not all(os.path.isfile(f) for f in files):
                continue
            detwin = {}
            for d, f in zip(DAYS, files):
                m = pd.read_csv(f, usecols=["flow"])
                for fid in m["flow"].dropna().astype(int).unique():
                    hit = real[d].get(int(fid))
                    if hit:
                        c, s = hit
                        for W in windows:
                            detwin.setdefault((c, W), set()).add(int(s // W))
            for W in windows:
                per = {c: len(detwin.get((c, W), set())) / len(allwin[(c, W)]) for c in classes}
                macro = sum(per.values()) / len(per)
                rows.append({"set": os.path.basename(root.rstrip("/")), "config": cid, "window_s": int(W),
                             "macro_window_recall": round(macro, 6), **{f"W:{c}": round(v, 6) for c, v in per.items()}})
                if W == 60 and os.path.isfile(os.path.join(base, "week.json")):
                    ref = json.load(open(os.path.join(base, "week.json")))["macro_window_recall"]
                    maxdiff = max(maxdiff, abs(ref - macro))
            n += 1
            if n % 25 == 0:
                print(f"{n} configurations done", flush=True)
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"{n} configurations, {len(rows)} rows written to {a.out}")
    print(f"check against week.json at 60 s: largest difference {maxdiff:.2e}"
          + ("  OK" if maxdiff < 1e-6 else "  (investigate)"))


if __name__ == "__main__":
    main()
