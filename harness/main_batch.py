#!/usr/bin/env python3
"""CASCADE-IDS main study runner (protocol v1.1). Two independent, resumable modes:

  detection  one run per day (Mon-Fri) for every configuration, then label matching and week
             scoring. Timing is not used, so it may run while the laptop is in use. Several runs
             go in parallel on different vCPUs (default 3: vCPUs 1, 2, 3).
  cost       Thursday cost runs (3 per configuration, 5 for the baseline, 1 per reference item),
             one at a time on vCPU 1, with calibration; disturbed runs are retried. Laptop untouched.

Only one mode can run at a time (a lock file prevents cost runs from overlapping detection runs).

Usage:
  python3 main_batch.py --mode detection                 # daytime, while you work
  python3 main_batch.py --mode cost --until 07:30        # evening, laptop untouched
  python3 main_batch.py --status
Ctrl+C stops safely; an interrupted run is redone from scratch next time.
"""
import argparse, datetime as dt, json, os, shutil, signal, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, FIRST_COMPLETED, wait

DAYS = {"monday": "Monday-WorkingHours.pcap", "tuesday": "Tuesday-WorkingHours.pcap",
        "wednesday": "Wednesday-workingHours.pcap", "thursday": "Thursday-WorkingHours.pcap",
        "friday": "Friday-WorkingHours.pcap"}
HERE = os.path.dirname(os.path.abspath(__file__))
MIN = {"detection": 4.0, "cost": 3.5}           # rough minutes per run, for ETA and --until


def units(item, mode):
    if mode == "detection":
        if item["type"] != "config" or item.get("cost_only"):
            return []
        return [(d, d) for d in DAYS]
    reps = 1 if item["type"] == "reference" else item["extra_cost_reps"] + 1
    return [("thursday", f"cost{i}") for i in range(1, reps + 1)]


def done(path):
    return os.path.isfile(os.path.join(path, "run.json"))


class Runner:
    def __init__(self, a, log):
        self.a, self.log = a, log
        self.match_lock = threading.Lock()      # label matching one at a time (memory)
        self.week_lock = threading.Lock()

    def run(self, item, day, name, cpu, cost):
        a = self.a
        out = os.path.join(a.runs, item["id"], name)
        if done(out):
            return True
        if os.path.exists(out):
            os.rename(out, out + f"_incomplete_{int(time.time())}")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        cfg = os.path.join(a.runs, item["id"], "config.json")
        if not os.path.exists(cfg):
            json.dump({"run_id": item["id"], "phase": item.get("phase", "reference"),
                       "levels": item["levels"], "rule_seed": item["rule_seed"]}, open(cfg, "w"))
        cmd = [sys.executable, os.path.join(HERE, "run_config.py"), "--config", cfg,
               "--pcap", os.path.join(a.pcap_dir, DAYS[day]), "--out", out, "--rule-seed", str(item["rule_seed"]),
               "--base-yaml", a.base_yaml, "--ruleset", a.ruleset, "--cpu", str(cpu)]
        cmd += (["--startup-pcap", a.tiny, "--calib-baseline", str(a.calib_baseline)] if cost
                else ["--no-calibration"])
        for attempt in (1, 2, 3):
            with open(out + ".log", "w") as f:
                rc = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT)
            if rc == 2 and cost:
                self.log(f"{item['id']}/{name} disturbed (attempt {attempt}); retry in 2 min")
                shutil.move(out, out + f"_disturbed{attempt}")
                shutil.move(out + ".log", out + f"_disturbed{attempt}.log")
                time.sleep(int(os.environ.get("CASCADE_RETRY_SLEEP", "120")))
                continue
            break
        if rc == 2 and cost and not done(out):
            self.log(f"{item['id']}/{name} disturbed 3 times; skipped for now, retried in the next cost session")
            return "skipped"
        if rc not in (0, 2) or not done(out):
            self.log(f"{item['id']}/{name} FAILED (exit {rc}); see {out}.log")
            return False
        if not cost:
            with self.match_lock:
                subprocess.call([sys.executable, os.path.join(HERE, "label_match.py"), "--labels",
                                 os.path.join(a.labels_dir, f"{day}.csv"), "--run", out, "--offset-hours", "0"],
                                stdout=open(out + ".match.log", "w"), stderr=subprocess.STDOUT)
            self.finish(item)
        return True

    def finish(self, item):
        base = os.path.join(self.a.runs, item["id"])
        week = os.path.join(base, "week.json")
        with self.week_lock:
            if item.get("cost_only") or os.path.isfile(week):
                return
            dirs = [os.path.join(base, d) for d in DAYS]
            if all(os.path.isfile(os.path.join(d, "detection.json")) for d in dirs):
                subprocess.call([sys.executable, os.path.join(HERE, "week_score.py"), *dirs, "--out", week],
                                stdout=open(os.path.join(base, "week.log"), "w"), stderr=subprocess.STDOUT)
                w = json.load(open(week))
                self.log(f"{item['id']} detection complete: macro window recall "
                         f"{w['macro_window_recall']:.3f}  levels {item['levels']}")


def take_lock(path, mode):
    if os.path.exists(path):
        try:
            other = json.load(open(path))
            os.kill(other["pid"], 0)
            sys.exit(f"Another run is active ({other['mode']} mode, pid {other['pid']}). "
                     f"Stop it first (Ctrl+C in its terminal).")
        except (ProcessLookupError, ValueError, KeyError, json.JSONDecodeError):
            pass                                  # stale lock from a crashed run
    json.dump({"mode": mode, "pid": os.getpid()}, open(path, "w"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["detection", "cost"])
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--schedule", default="/data/config/main_schedule.json")
    ap.add_argument("--runs", default="/data/runs/main")
    ap.add_argument("--pcap-dir", default="/data/pcap")
    ap.add_argument("--labels-dir", default="/data/labels")
    ap.add_argument("--base-yaml", default="/data/config/base_suricata.yaml")
    ap.add_argument("--ruleset", default="/data/rules/et-open-2026-10-19.rules")
    ap.add_argument("--tiny", default="/data/config/tiny.pcap")
    ap.add_argument("--detection-cpus", default="1,2,3", help="vCPUs for parallel detection runs")
    ap.add_argument("--cost-cpu", type=int, default=1)
    ap.add_argument("--calib-baseline", type=float, default=4.25)
    ap.add_argument("--until", help="HH:MM; do not start a run that could end after this time")
    a = ap.parse_args()

    sched = json.load(open(a.schedule))
    os.makedirs(a.runs, exist_ok=True)
    items = sched["items"]

    def remaining(mode):
        plan = [(it, u) for it in items for u in units(it, mode)]
        todo = [(it, u) for it, u in plan if not done(os.path.join(a.runs, it["id"], u[1]))]
        return plan, todo

    if a.status or not a.mode:
        workers = len(a.detection_cpus.split(","))
        for mode in ("detection", "cost"):
            plan, todo = remaining(mode)
            hours = len(todo) * MIN[mode] / 60 / (workers if mode == "detection" else 1)
            print(f"{mode:9s}: {len(plan) - len(todo)}/{len(plan)} runs done, about {hours:.1f} h left")
        det_items = [it for it in items if it["type"] == "config" and not it.get("cost_only")]
        weeks = sum(os.path.isfile(os.path.join(a.runs, it["id"], "week.json")) for it in det_items)
        print(f"configurations with complete detection: {weeks}/{len(det_items)}")
        return

    lock = os.path.join(a.runs, ".active.lock")
    take_lock(lock, a.mode)
    logf = open(os.path.join(a.runs, "progress.log"), "a")
    def log(msg):
        line = f"{dt.datetime.now():%Y-%m-%d %H:%M} [{a.mode}] {msg}"
        print(line, flush=True); logf.write(line + "\n"); logf.flush()

    deadline = None
    if a.until:
        h, m = map(int, a.until.split(":"))
        now = dt.datetime.now()
        deadline = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if deadline <= now:
            deadline += dt.timedelta(days=1)
    def time_left_ok():
        return not deadline or dt.datetime.now() + dt.timedelta(minutes=MIN[a.mode] * 1.5) <= deadline

    r = Runner(a, log)
    plan, todo = remaining(a.mode)
    log(f"start: {len(todo)} of {len(plan)} runs left" + (f", stopping before {deadline:%H:%M}" if deadline else ""))
    try:
        if a.mode == "cost":
            for it, (day, name) in todo:
                if not time_left_ok():
                    log("stopping: next run could pass --until"); break
                res = r.run(it, day, name, a.cost_cpu, cost=True)
                if res is False:
                    log("stopping after failure"); break
            else:
                left = len(remaining("cost")[1])
                log("all cost runs complete" if left == 0 else f"pass finished; {left} skipped runs left for next session")
        else:
            for it in items:                         # configs whose days were all run earlier
                if it["type"] == "config" and not it.get("cost_only"):
                    r.finish(it)
            cpus = [int(c) for c in a.detection_cpus.split(",")]
            free, queue, running, failed = list(cpus), list(todo), {}, False
            with ThreadPoolExecutor(max_workers=len(cpus)) as ex:
                while (queue and not failed) or running:
                    while free and queue and not failed and time_left_ok():
                        it, (day, name) = queue.pop(0)
                        cpu = free.pop(0)
                        running[ex.submit(r.run, it, day, name, cpu, False)] = cpu
                    if not running:
                        break
                    fin, _ = wait(running, return_when=FIRST_COMPLETED)
                    for f in fin:
                        free.append(running.pop(f))
                        if not f.result():
                            failed = True
            if failed:
                log("stopped after a failure; fix the cause and start again")
            elif queue:
                log("stopping: next run could pass --until")
            else:
                log("all detection runs complete")
    except KeyboardInterrupt:
        log("stopped by user (Ctrl+C); interrupted runs will be redone next time")
    finally:
        try:
            os.remove(lock)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
