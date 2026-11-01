#!/usr/bin/env python3
"""CASCADE-IDS run harness for Snort 3: run ONE configuration offline and record cost + alerts.
(Port of run_config.py; same capabilities, levels file levels_snort.json, same outputs.)

Usage:
  python3 run_config_snort.py --config cfg.json --pcap traffic.pcap --out /data/runs/phase0/R001 \
      [--startup-pcap tiny.pcap] [--cpu 1] [--rule-seed 20261019]

cfg.json: {"run_id": "...", "phase": "...", "levels": {"K1": 1, "K2": 0.5, ...}}
Capabilities not listed run at level 1 (full). Outputs in --out:
  run.json     configuration, hashes, cost, packet stats, exit status
  alerts.csv   one row per alert (for label matching)
  snort.log    Snort's own console output (the rule file used is recorded by hash and then deleted)
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


DROP_LUA = ("local function drop(t) for i = #binder, 1, -1 do local u = binder[i].use "
            "if u and u.type == t then table.remove(binder, i) end end end")


def lua_args(levels, spec):
    """Settings for K1-K5 as ONE Lua chunk appended to the configuration (--lua).

    v1.4 fix: with several --lua options, the K1 setting was lost whenever an inspector was also
    removed; all settings now go into a single chunk (set statements first, then binder removals).
    """
    sets, drops, applied = [], [], {}
    for k, s in spec.items():
        if s.get("kind") != "lua":
            continue
        lv = level_key(levels.get(k, 1))
        if lv not in s["levels"]:
            sys.exit(f"Level {lv} not defined for {k}")
        d = s["levels"][lv]
        for stmt in d.get("set", []):
            sets.append(stmt); applied.setdefault(k, []).append(stmt)
        for t in d.get("drop_inspectors", []):
            drops.append(t); applied.setdefault(k, []).append(f"drop inspector {t}")
    if not sets and not drops:
        return [], applied
    chunk = "\n".join(sets)
    if drops:
        chunk += "\n" + DROP_LUA + "\n" + "\n".join(f"drop('{t}')" for t in drops)
    return ["--lua", chunk], applied


def run_snort(cfg, rules, pcap, out, extra, cpu):
    os.makedirs(out, exist_ok=True)
    cmd = ["taskset", "-c", str(cpu), "snort", "-c", cfg, "-R", rules, "-r", pcap, "-U", "-y",
           "-A", "alert_json", "-l", out,
           "--lua", "alert_json = { file = true, fields = 'timestamp proto src_addr src_port dst_addr dst_port sid msg class' }"] + extra
    t0 = time.perf_counter()
    with open(os.path.join(out, "snort.log"), "w") as log:
        p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
        _, status, ru = os.wait4(p.pid, 0)
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


def snort_time(ts):
    """'17/07/06-12:01:01.923103' (with -y: yy/mm/dd; -U: UTC) -> ISO 8601 with +00:00."""
    d, t = ts.split("-", 1)
    parts = d.split("/")
    if len(parts) == 3:
        yy, mm, dd = parts
    else:                                   # without -y: mm/dd, no year (should not happen with -y)
        mm, dd = parts; yy = "17"
    return f"20{int(yy):02d}-{int(mm):02d}-{int(dd):02d}T{t}+00:00"


def parse_snort(out):
    alerts, stats = [], {}
    path = os.path.join(out, "alert_json.txt")
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                alerts.append([snort_time(e["timestamp"]), "", e.get("src_addr"), e.get("src_port"),
                               e.get("dst_addr"), e.get("dst_port"), e.get("proto"), e.get("sid"),
                               e.get("class"), e.get("msg")])
    log = os.path.join(out, "snort.log")
    if os.path.exists(log):
        txt = open(log, errors="replace").read()
        for key in ("received", "analyzed"):
            m = re.findall(rf"^\s*{key}:\s*(\d+)", txt, re.M)
            if m:
                stats[key] = int(m[0])
    return alerts, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--pcap", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--base-cfg", default="/data/config/snort/snort_base.lua")
    ap.add_argument("--ruleset", default="/data/rules_snort/et_snort3_20261028_clean.rules")
    ap.add_argument("--levels-spec", default=os.path.join(HERE, "levels_snort.json"))
    ap.add_argument("--startup-pcap", help="near-empty pcap; its CPU is subtracted as startup cost")
    ap.add_argument("--rule-seed", type=int, default=20261019)
    ap.add_argument("--cpu", type=int, default=1)
    ap.add_argument("--calib-baseline", type=float, default=4.25,
                    help="calibration CPU seconds in undisturbed runs on this machine (pilot batch 3b: about 4.25 s)")
    ap.add_argument("--calib-tolerance", type=float, default=0.10,
                    help="flag the run as disturbed if calibration is this much slower than baseline, or drifts this much")
    ap.add_argument("--no-calibration", action="store_true",
                    help="skip the calibration workload run before and after Snort")
    a = ap.parse_args()

    spec = {k: v for k, v in json.load(open(a.levels_spec)).items() if not k.startswith("_")}
    if os.path.exists(a.out):
        sys.exit(f"Refusing to overwrite existing run directory {a.out}")
    os.makedirs(a.out)
    cfg = json.load(open(a.config))
    unknown = set(cfg["levels"]) - set(spec)
    if unknown:
        sys.exit(f"Unknown capabilities: {unknown}")

    rules = os.path.join(a.out, "rules.rules")
    rule_counts = build_rules(a.ruleset, cfg["levels"], spec, a.rule_seed, rules)
    extra, applied = lua_args(cfg["levels"], spec)

    rec = {"run_id": cfg.get("run_id"), "phase": cfg.get("phase"), "levels": cfg["levels"],
           "rule_seed": a.rule_seed, "rule_counts": rule_counts, "settings_applied": applied,
           "started_utc": datetime.now(timezone.utc).isoformat(),
           "hashes": {"pcap": sha256(a.pcap), "ruleset": sha256(a.ruleset), "rules_used": sha256(rules),
                      "base_cfg": sha256(a.base_cfg), "levels_spec": sha256(a.levels_spec),
                      "harness": sha256(os.path.abspath(__file__))},
           "snort_version": [l.strip() for l in subprocess.run(["snort", "-V"], capture_output=True, text=True).stdout.splitlines() if "Version" in l or "Using" in l],
           "pcap": a.pcap, "pcap_bytes": os.path.getsize(a.pcap)}

    if not a.no_calibration:
        rec["calib_before_s"] = calibrate(a.cpu)
    if a.startup_pcap:
        s = run_snort(a.base_cfg, rules, a.startup_pcap, os.path.join(a.out, "startup"), extra, a.cpu)
        rec["startup"] = s
    r = run_snort(a.base_cfg, rules, a.pcap, a.out, extra, a.cpu)
    rec["main"] = r
    if not a.no_calibration:
        rec["calib_after_s"] = calibrate(a.cpu)
        cb, ca = rec["calib_before_s"], rec["calib_after_s"]
        rec["calib_mean_s"] = (cb + ca) / 2
        rec["calib_drift"] = abs(ca - cb) / min(cb, ca)     # large drift = host disturbance during the run
    alerts, stats = parse_snort(a.out)
    rec["n_alerts"] = len(alerts)
    rec["packets"] = stats.get("analyzed") or stats.get("received")
    rec["stats"] = stats
    if a.startup_pcap and rec["startup"]["exit_code"] == 0:
        proc = r["cpu_s"] - rec["startup"]["cpu_s"]
        rec["processing_cpu_s"] = proc
        rec["processing_cpu_s_per_gb"] = proc / (rec["pcap_bytes"] / 1e9)
        if "calib_mean_s" in rec:
            rec["processing_cpu_calib_units"] = proc / rec["calib_mean_s"]   # clock-independent cost

    problems = []
    if r["exit_code"] != 0:
        problems.append(f"snort exit code {r['exit_code']}")
    if not rec["packets"]:
        problems.append("no packet statistics in snort.log")
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
    for f in ("alert_json.txt", "rules.rules"):          # alerts.csv + run.json (with rule hash) keep what is needed
        if os.path.exists(os.path.join(a.out, f)):
            os.remove(os.path.join(a.out, f))
    st = os.path.join(a.out, "startup", "alert_json.txt")
    if os.path.exists(st):
        os.remove(st)
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
