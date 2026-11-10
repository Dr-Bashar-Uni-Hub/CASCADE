#!/usr/bin/env bash
# Pilot batch 3 (protocol v0.2): new K1 depth levels and K11 cost on Thursday, K11 false-alarm effect on Monday.
# Laptop must be left alone (about 1 hour). Existing run folders are skipped, so it can be restarted.
set -u
H=/data/harness; R=/data/runs/phase0; C=/data/config
declare -A PCAP=([monday]=Monday-WorkingHours.pcap [thursday]=Thursday-WorkingHours.pcap)
cd "$H"
run() {
  local id=$1 day=$2 levels=$3
  if [ -d "$R/$id" ]; then echo "skip $id (exists)"; return; fi
  echo "{\"run_id\":\"$id\",\"phase\":\"pilot\",\"levels\":$levels}" > "$C/$id.json"
  python3 run_config.py --config "$C/$id.json" --pcap "/data/pcap/${PCAP[$day]}" --out "$R/$id" \
      --startup-pcap "$C/tiny.pcap" > "$R/$id.out" 2>&1
  python3 label_match.py --labels "/data/labels/$day.csv" --run "$R/$id" --offset-hours 0 >> "$R/$id.out" 2>&1
  echo "$(date +%H:%M) $id done ($day $levels)"
}
n=70
for rep in 1 2 3; do
  run P$n thursday '{}'; n=$((n+1))
  for lv in 0.2 0.4 0.6 0.8; do run P$n thursday "{\"K1\":$lv}"; n=$((n+1)); done
  run P$n thursday '{"K11":0}'; n=$((n+1))
done
run P090 monday '{"K11":0}'
python3 summarize.py "$R" | grep -E '^run|^P0(20|7|8|90)|^P09'
