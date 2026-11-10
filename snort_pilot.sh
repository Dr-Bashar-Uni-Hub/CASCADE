#!/bin/bash
# Snort pilot, part A (detection only, day mode): format check, determinism, key single-factor effects.
set -u
H=/data/harness; R=/data/runs/snort_pilot; C=/data/config/snort_pilot
mkdir -p $R $C; cd $H
run() {   # run <id> <levels-json>
  local id=$1 lv=$2
  if [ -d "$R/$id" ]; then echo "skip $id"; return; fi
  echo "{\"run_id\":\"$id\",\"phase\":\"snort-pilot\",\"levels\":$lv}" > $C/$id.json
  python3 run_config_snort.py --config $C/$id.json --pcap /data/pcap/Thursday-WorkingHours.pcap \
      --out $R/$id --no-calibration > $R/$id.out 2>&1
  echo "$(date +%H:%M) $id exit $? ($lv)"
}
run SP01 '{}'
python3 label_match.py --labels /data/labels/thursday.csv --run $R/SP01 --check-offset
python3 label_match.py --labels /data/labels/thursday.csv --run $R/SP01 --offset-hours 0
run SP02 '{}'
run SP03 '{"K2":0}'
run SP04 '{"K6":0}'
run SP05 '{"K1":0}'
run SP06 '{"K1":0.2}'
run SP07 '{"K1":0.6}'
for id in SP02 SP03 SP04 SP05 SP06 SP07; do
  [ -f $R/$id/run.json ] && python3 label_match.py --labels /data/labels/thursday.csv --run $R/$id --offset-hours 0 > $R/$id.match 2>&1
done
echo "=== summary"
for id in SP01 SP02 SP03 SP04 SP05 SP06 SP07; do
  python3 - "$R/$id" <<'PY'
import json, sys, os
d=sys.argv[1]; r=json.load(open(os.path.join(d,"run.json")))
det=json.load(open(os.path.join(d,"detection.json"))) if os.path.exists(os.path.join(d,"detection.json")) else {}
pc={c:round(v.get("window_recall") or 0,3) for c,v in det.get("per_class",{}).items()}
print(os.path.basename(d), r["levels"], "valid", r["valid"], r["problems"], "alerts", r["n_alerts"], "pkts", r["packets"],
      "cpu %.0f s" % r["main"]["cpu_s"], "unmatched", det.get("alerts_unmatched"), "macro_win", round(det.get("macro_window_recall") or 0,3), pc)
PY
done
cut -d, -f1,3,7,8 $R/SP01/alerts.csv | head -3
cmp <(cut -d, -f1,3-8 $R/SP01/alerts.csv | sort) <(cut -d, -f1,3-8 $R/SP02/alerts.csv | sort) && echo "SP01 and SP02 alerts identical"
