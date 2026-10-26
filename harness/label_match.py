#!/usr/bin/env python3
"""CASCADE-IDS label matching (protocol section 3).

Maps every Suricata alert (alerts.csv from run_config.py) to a labeled flow in the
CIC-IDS2017 "improved" dataset (Liu, Engelen et al., CNS 2022) and computes detection.

Matching rule: same protocol and the same pair of endpoints (either direction), and the
alert time falls inside [flow start - tol, flow end + tol]. If several flows qualify, the
one whose interval contains the alert (or is nearest to it) is chosen. Suricata's flow_id
is never used (it is random per run).

Usage:
  python3 label_match.py --labels /data/labels/thursday.csv --run /data/runs/phase0/R001
  python3 label_match.py --labels /data/labels/thursday.csv --run ... --check-offset
      (tries label-clock offsets of -6..+6 h and reports the match rate for each)

Writes into the run directory: matched_alerts.csv, detection.json
"""
import argparse, bisect, csv, json, os, sys
from collections import defaultdict
import pandas as pd

PROTO = {"TCP": 6, "UDP": 17, "ICMP": 1, "IPV6-ICMP": 58}
COLS = ["id", "Src IP", "Src Port", "Dst IP", "Dst Port", "Protocol", "Timestamp",
        "Flow Duration", "Label", "Attempted Category"]


def norm_key(proto, a_ip, a_port, b_ip, b_port):
    if proto in (1, 58):                       # ICMP: no ports
        a_port = b_port = 0
    x, y = (str(a_ip), int(a_port)), (str(b_ip), int(b_port))
    return (proto,) + (x + y if x <= y else y + x)


def load_labels(path, offset_h):
    df = pd.read_csv(path, usecols=COLS, low_memory=False).rename(columns={
        "Src IP": "sip", "Src Port": "sport", "Dst IP": "dip", "Dst Port": "dport", "Protocol": "proto",
        "Timestamp": "ts", "Flow Duration": "dur", "Attempted Category": "att_cat"})
    t0 = pd.to_datetime(df["ts"], format="mixed")
    start = (t0 - pd.Timestamp("1970-01-01")).dt.total_seconds() - offset_h * 3600.0
    df["start"] = start
    df["end"] = start + df["dur"].clip(lower=0) / 1e6      # duration is in microseconds
    df["attempted"] = (df["att_cat"] != -1) | df["Label"].str.contains("Attempted", case=False)
    df["cls"] = df["Label"].str.replace(r"\s*-\s*Attempted$", "", regex=True).str.strip()
    index = defaultdict(list)
    for row in df.itertuples(index=False):
        k = norm_key(int(row.proto), row.sip, row.sport, row.dip, row.dport)
        index[k].append((row.start, row.end, row.id))
    for k in index:
        index[k].sort()
        index[k] = ([c[0] for c in index[k]], index[k])     # (sorted start times, flows)
    return df, index


def load_alerts(run_dir):
    a = pd.read_csv(os.path.join(run_dir, "alerts.csv"))
    if a.empty:
        return a
    a["t"] = (pd.to_datetime(a["timestamp"], utc=True, format="mixed")
              - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds()
    a["proto_n"] = a["proto"].str.upper().map(PROTO).fillna(-1).astype(int)
    for c in ("src_port", "dest_port"):
        a[c] = a[c].fillna(0).astype(int)
    return a


def match(alerts, index, tol):
    out = []
    for r in alerts.itertuples(index=False):
        starts, cands = index.get(norm_key(r.proto_n, r.src_ip, r.src_port, r.dest_ip, r.dest_port), ([], []))
        best, best_d = None, None
        if cands:
            hi = bisect.bisect_right(starts, r.t + tol)
            for s, e, fid in cands[max(0, hi - 50):hi]:             # flows starting before alert+tol
                if s - tol <= r.t <= e + tol:
                    d = 0.0 if s <= r.t <= e else min(abs(r.t - s), abs(r.t - e))
                    if best_d is None or d < best_d:
                        best, best_d = fid, d
        out.append(best)
    return out


def episodes(times, gap):
    """Number of runs of attack flows (sorted start times) separated by more than `gap` seconds."""
    times = sorted(times)
    if not times:
        return []
    eps, cur = [], [times[0]]
    for t in times[1:]:
        if t - cur[-1] > gap:
            eps.append(cur); cur = [t]
        else:
            cur.append(t)
    eps.append(cur)
    return eps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--offset-hours", type=float, default=0.0,
                    help="label clock minus UTC, in hours (set from --check-offset)")
    ap.add_argument("--tol", type=float, default=2.0, help="time tolerance in seconds")
    ap.add_argument("--episode-gap", type=float, default=300.0)
    ap.add_argument("--window", type=float, default=60.0,
                    help="window length in seconds for window recall")
    ap.add_argument("--check-offset", action="store_true")
    a = ap.parse_args()

    alerts = load_alerts(a.run)
    if alerts.empty:
        print("No alerts in this run."); return

    if a.check_offset:
        for off in range(-6, 7):
            _, idx = load_labels(a.labels, off)
            m = match(alerts, idx, a.tol)
            rate = sum(x is not None for x in m) / len(m)
            print(f"offset {off:+d} h: {rate:6.1%} of {len(m)} alerts matched a labeled flow")
        return

    df, idx = load_labels(a.labels, a.offset_hours)
    alerts["flow"] = pd.array(match(alerts, idx, a.tol), dtype="Int64")
    info = df.set_index("id")[["cls", "attempted", "start"]]
    alerts = alerts.join(info, on="flow")
    alerts.drop(columns=["t", "proto_n"]).to_csv(os.path.join(a.run, "matched_alerts.csv"), index=False)

    detected = set(alerts["flow"].dropna().astype(int))
    df["detected"] = df["id"].isin(detected)
    hours = (df["start"].max() - df["start"].min()) / 3600.0
    attack = df[df["cls"].str.upper() != "BENIGN"]

    per_class = {}
    for cls, g in attack.groupby("cls"):
        real = g[~g["attempted"]]
        eps = episodes(real["start"].tolist(), a.episode_gap)
        det_t = set(real.loc[real["detected"], "start"])
        win_all = set((real["start"] // a.window).astype(int))
        win_det = set((real.loc[real["detected"], "start"] // a.window).astype(int))
        per_class[cls] = {
            "flows": int(len(real)), "flows_detected": int(real["detected"].sum()),
            "recall": float(real["detected"].mean()) if len(real) else None,
            "windows": len(win_all), "windows_detected": len(win_det),
            "window_recall": len(win_det) / len(win_all) if win_all else None,
            "episodes": len(eps), "episodes_detected": sum(any(t in det_t for t in e) for e in eps),
            "attempted_flows": int(g["attempted"].sum()),
            "attempted_flows_alerted": int(g.loc[g["attempted"], "detected"].sum()),
        }
    recalls = [v["recall"] for v in per_class.values() if v["recall"] is not None]
    wrecalls = [v["window_recall"] for v in per_class.values() if v["window_recall"] is not None]
    benign_alerts = alerts[alerts["cls"].str.upper() == "BENIGN"] if "cls" in alerts else alerts.iloc[0:0]
    res = {
        "labels_file": a.labels, "offset_hours": a.offset_hours, "tol_s": a.tol,
        "episode_gap_s": a.episode_gap,
        "alerts_total": int(len(alerts)),
        "alerts_unmatched": int(alerts["flow"].isna().sum()),
        "alerts_on_benign": int(len(benign_alerts)),
        "false_positives_per_hour": len(benign_alerts) / hours if hours else None,
        "benign_flows_alerted": int(benign_alerts["flow"].nunique()),
        "macro_recall": sum(recalls) / len(recalls) if recalls else None,
        "macro_window_recall": sum(wrecalls) / len(wrecalls) if wrecalls else None,
        "window_s": a.window,
        "per_class": per_class,
    }
    json.dump(res, open(os.path.join(a.run, "detection.json"), "w"), indent=1)
    print(f"alerts {res['alerts_total']}, unmatched {res['alerts_unmatched']} "
          f"({res['alerts_unmatched']/res['alerts_total']:.1%}), on benign flows {res['alerts_on_benign']}")
    print(f"macro recall {res['macro_recall']}   macro window recall {res['macro_window_recall']}")
    for c, v in per_class.items():
        r = "" if v["recall"] is None else round(v["recall"], 3)
        w = "" if v["window_recall"] is None else round(v["window_recall"], 3)
        print(f"  {c:30s} flow {r!s:>6} ({v['flows_detected']}/{v['flows']})  "
              f"window {w!s:>5} ({v['windows_detected']}/{v['windows']})  "
              f"episodes {v['episodes_detected']}/{v['episodes']}  attempted alerted {v['attempted_flows_alerted']}/{v['attempted_flows']}")


if __name__ == "__main__":
    main()
