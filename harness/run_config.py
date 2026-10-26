#!/usr/bin/env python3
"""CASCADE-IDS run harness: run ONE Suricata configuration offline and record cost + alerts.

Usage:
  python3 run_config.py --config cfg.json --pcap traffic.pcap --out /data/runs/phase0/R001 \
      [--startup-pcap tiny.pcap] [--cpu 1] [--rule-seed 20261019]

cfg.json: {"run_id": "...", "phase": "...", "levels": {"K1": 1, "K2": 0.5, ...}}
Capabilities not listed run at level 1 (full). Outputs in --out:
  run.json     configuration, hashes, cost, packet stats, exit status
  alerts.csv   one row per alert (for label matching)
  rules.rules  the exact rule file used
  suricata.log Suricata's own console output
"""
import argparse, csv, hashlib, json, math, os, random, re, shutil, subprocess, sys, time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CAT_RE = re.compile(r'msg:"ET ([A-Z0-9_]+)')


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def level_key(v):
    v = float(v)
    return "0" if v == 0 else "1" if v == 1 else str(v)


def build_rules(ruleset, levels, spec, seed, dst):
    """Keep a seeded, nested fraction of rules for each rule capability (K6-K10)."""
    lines = open(ruleset, encoding="utf-8", errors="replace").read().splitlines()
    cat_to_cap = {c: k for k, s in spec.items() if s.get("kind") == "rules" for c in s["categories"]}
    by_cap = {k: [] for k, s in spec.items() if s.get("kind") == "rules"}
    for i, line in enumerate(lines):
        if not line.startswith("alert"):
            continue
        if "noalert" in line:      # flowbit-setter rules stay in every run, so dependent rules keep working
            continue
        m = CAT_RE.search(line)
        if m and m.group(1) in cat_to_cap:
            by_cap[cat_to_cap[m.group(1)]].append(i)
    drop, counts = set(), {}
    for k, idx in by_cap.items():
        frac = float(levels.get(k, 1))
        order = sorted(idx)
        random.Random(f"{seed}-{k}").shuffle(order)          # same order for every level -> nested subsets
        keep = math.ceil(frac * len(order) - 1e-9)
        drop.update(order[keep:])
        counts[k] = {"total": len(order), "kept": keep}
    kept = [l for i, l in enumerate(lines) if i not in drop]
    open(dst, "w").write("\n".join(kept) + "\n")
    counts["_all_enabled_rules"] = sum(1 for l in kept if l.startswith("alert"))
    return counts


def set_args(levels, spec):
    args, applied = [], {}
    for k, s in spec.items():
        if s.get("kind") != "set":
            continue
        lv = level_key(levels.get(k, 1))
        if lv not in s["levels"]:
            sys.exit(f"Level {lv} not defined for {k}")
        for key, val in s["levels"][lv].items():
            args += ["--set", f"{key}={val}"]
            applied[key] = val
    return args, applied


def check_keys_exist(base_yaml, spec):
    """--set silently accepts misspelled keys, so every key used must already exist in the base config."""
    dump = subprocess.run(["suricata", "-c", base_yaml, "--dump-config"], capture_output=True, text=True).stdout
    present = {line.split(" = ")[0] for line in dump.splitlines() if " = " in line}
    missing = sorted({key for s in spec.values() if s.get("kind") == "set"
                      for lv in s["levels"].values() for key in lv} - present)
    if missing:
        sys.exit(f"Config keys not found in base yaml (typo or version difference): {missing}")


def run_suricata(base_yaml, rules, pcap, out, extra, cpu):
    os.makedirs(out, exist_ok=True)
    cmd = ["taskset", "-c", str(cpu), "suricata", "-c", base_yaml, "-S", rules, "-r", pcap,
           "-l", out, "-k", "none", "--runmode", "single"] + extra
    t0 = time.perf_counter()
    with open(os.path.join(out, "suricata.log"), "w") as log:
        p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
        _, status, ru = os.wait4(p.pid, 0)              # resource use of this child only
    wall = time.perf_counter() - t0
    return {"cmd": cmd, "exit_code": os.waitstatus_to_exitcode(status), "wall_s": wall,
            "cpu_user_s": ru.ru_utime, "cpu_sys_s": ru.ru_stime, "cpu_s": ru.ru_utime + ru.ru_stime,
            "peak_rss_mb": ru.ru_maxrss / 1024}


CALIB_CODE = "s=0\nfor i in range(25_000_000):\n    s += i * i\n"


def calibrate(cpu):
    """Fixed CPU workload on the same vCPU; its CPU time tracks clock speed and host interference."""
    p = subprocess.Popen(["taskset", "-c", str(cpu), sys.executable, "-c", CALIB_CODE])
    _, status, ru = os.wait4(p.pid, 0)
    return ru.ru_utime + ru.ru_stime


def parse_eve(out):
    alerts, stats = [], {}
    path = os.path.join(out, "eve.json")
    if not os.path.exists(path):
        return alerts, stats
    with open(path) as f:
        for line in f:
            e = json.loads(line)
            if e.get("event_type") == "alert":
                a = e["alert"]
                alerts.append([e.get("timestamp"), e.get("flow_id"), e.get("src_ip"), e.get("src_port"),
                               e.get("dest_ip"), e.get("dest_port"), e.get("proto"),
                               a.get("signature_id"), a.get("category"), a.get("signature")])
            elif e.get("event_type") == "stats":
                stats = e["stats"]
    return alerts, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--pcap", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--base-yaml", default="/data/config/base_suricata.yaml")
    ap.add_argument("--ruleset", default="/data/rules/et-open-2026-10-19.rules")
    ap.add_argument("--levels-spec", default=os.path.join(HERE, "levels.json"))
    ap.add_argument("--startup-pcap", help="near-empty pcap; its CPU is subtracted as startup cost")
    ap.add_argument("--rule-seed", type=int, default=20261019)
    ap.add_argument("--cpu", type=int, default=1)
    ap.add_argument("--calib-baseline", type=float, default=4.25,
                    help="calibration CPU seconds in undisturbed runs on this machine (pilot batch 3b: about 4.25 s)")
    ap.add_argument("--calib-tolerance", type=float, default=0.10,
                    help="flag the run as disturbed if calibration is this much slower than baseline, or drifts this much")
    ap.add_argument("--no-calibration", action="store_true",
                    help="skip the calibration workload run before and after Suricata")
    a = ap.parse_args()

    spec = {k: v for k, v in json.load(open(a.levels_spec)).items() if not k.startswith("_")}
    check_keys_exist(a.base_yaml, spec)
    if os.path.exists(a.out):
        sys.exit(f"Refusing to overwrite existing run directory {a.out}")
    os.makedirs(a.out)
    cfg = json.load(open(a.config))
    unknown = set(cfg["levels"]) - set(spec)
    if unknown:
        sys.exit(f"Unknown capabilities: {unknown}")

    rules = os.path.join(a.out, "rules.rules")
    rule_counts = build_rules(a.ruleset, cfg["levels"], spec, a.rule_seed, rules)
    extra, applied = set_args(cfg["levels"], spec)

    rec = {"run_id": cfg.get("run_id"), "phase": cfg.get("phase"), "levels": cfg["levels"],
           "rule_seed": a.rule_seed, "rule_counts": rule_counts, "settings_applied": applied,
           "started_utc": datetime.now(timezone.utc).isoformat(),
           "hashes": {"pcap": sha256(a.pcap), "ruleset": sha256(a.ruleset), "rules_used": sha256(rules),
                      "base_yaml": sha256(a.base_yaml), "levels_spec": sha256(a.levels_spec),
                      "harness": sha256(os.path.abspath(__file__))},
           "suricata_version": subprocess.run(["suricata", "-V"], capture_output=True, text=True).stdout.strip(),
           "pcap": a.pcap, "pcap_bytes": os.path.getsize(a.pcap)}

    if not a.no_calibration:
        rec["calib_before_s"] = calibrate(a.cpu)
    if a.startup_pcap:
        s = run_suricata(a.base_yaml, rules, a.startup_pcap, os.path.join(a.out, "startup"), extra, a.cpu)
        rec["startup"] = s
    r = run_suricata(a.base_yaml, rules, a.pcap, a.out, extra, a.cpu)
    rec["main"] = r
    if not a.no_calibration:
        rec["calib_after_s"] = calibrate(a.cpu)
        cb, ca = rec["calib_before_s"], rec["calib_after_s"]
        rec["calib_mean_s"] = (cb + ca) / 2
        rec["calib_drift"] = abs(ca - cb) / min(cb, ca)     # large drift = host disturbance during the run
    alerts, stats = parse_eve(a.out)
    rec["n_alerts"] = len(alerts)
    rec["packets"] = stats.get("decoder", {}).get("pkts")
    rec["stats_capture"] = stats.get("capture")
    if a.startup_pcap and rec["startup"]["exit_code"] == 0:
        proc = r["cpu_s"] - rec["startup"]["cpu_s"]
        rec["processing_cpu_s"] = proc
        rec["processing_cpu_s_per_gb"] = proc / (rec["pcap_bytes"] / 1e9)
        if "calib_mean_s" in rec:
            rec["processing_cpu_calib_units"] = proc / rec["calib_mean_s"]   # clock-independent cost

    problems = []
    if r["exit_code"] != 0:
        problems.append(f"suricata exit code {r['exit_code']}")
    if not stats:
        problems.append("no stats record in eve.json (see suricata.log)")
    if a.startup_pcap and rec["startup"]["exit_code"] != 0:
        problems.append(f"startup run exit code {rec['startup']['exit_code']}")
    rec["valid"] = not problems
    rec["problems"] = problems
    rec["disturbed"] = False
    if "calib_mean_s" in rec:
        slow = max(rec["calib_before_s"], rec["calib_after_s"]) > a.calib_baseline * (1 + a.calib_tolerance)
        rec["disturbed"] = bool(slow or rec["calib_drift"] > a.calib_tolerance)
        rec["calib_baseline_s"] = a.calib_baseline

    with open(os.path.join(a.out, "alerts.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "flow_id", "src_ip", "src_port", "dest_ip", "dest_port", "proto",
                    "sid", "category", "signature"])
        w.writerows(alerts)
    eve = os.path.join(a.out, "eve.json")
    if os.path.exists(eve):
        os.remove(eve)                                 # alerts.csv + run.json keep what is needed
    json.dump(rec, open(os.path.join(a.out, "run.json"), "w"), indent=1)
    print(json.dumps({k: rec.get(k) for k in ["run_id", "valid", "problems", "n_alerts", "packets",
                                               "processing_cpu_s", "calib_before_s", "calib_after_s",
                                               "calib_drift", "disturbed"]}, indent=1))
    print(f"main: cpu={r['cpu_s']:.3f}s wall={r['wall_s']:.2f}s rss={r['peak_rss_mb']:.0f}MB")
    if rec["valid"] and rec["disturbed"]:
        print("DISTURBED: calibration shows the host was busy; cost of this run should not be used")
        sys.exit(2)
    sys.exit(0 if rec["valid"] else 1)


if __name__ == "__main__":
    main()
