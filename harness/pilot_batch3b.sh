#!/usr/bin/env bash
# Pilot batch 3b: repeat the CPU cost runs of batch 3 (disturbed) for K1 levels and K11 on Thursday.
# A run flagged DISTURBED (calibration more than 10% slow) is moved to <id>_disturbed and retried
# after a 2-minute pause, up to 3 attempts. Leave the laptop alone (about 70 minutes).
set -u
H=/data/harness; R=/data/runs/phase0; C=/data/config
PCAP=/data/pcap/Thursday-WorkingHours.pcap
cd "$H"
run() {
  local id=$1 levels=$2 attempt
  if [ -d "$R/$id" ]; then echo "skip $id (exists)"; return; fi
  echo "{\"run_id\":\"$id\",\"phase\":\"pilot\",\"levels\":$levels}" > "$C/$id.json"
  for attempt in 1 2 3; do
    python3 run_config.py --config "$C/$id.json" --pcap "$PCAP" --out "$R/$id" \
        --startup-pcap "$C/tiny.pcap" > "$R/$id.out" 2>&1
    rc=$?
    if [ $rc -eq 2 ]; then
      echo "$(date +%H:%M) $id disturbed (attempt $attempt), retrying in 2 min"
      mv "$R/$id" "$R/${id}_disturbed$attempt"; mv "$R/$id.out" "$R/${id}_disturbed$attempt.out"
      sleep 120; continue
    fi
    break
  done
  [ -d "$R/$id" ] && python3 label_match.py --labels /data/labels/thursday.csv --run "$R/$id" --offset-hours 0 >> "$R/$id.out" 2>&1
  echo "$(date +%H:%M) $id done ($levels)"
}
n=100
for rep in 1 2 3; do
  run P$n '{}'; n=$((n+1))
  for lv in 0 0.2 0.4 0.6 0.8; do run P$n "{\"K1\":$lv}"; n=$((n+1)); done
  run P$n '{"K11":0}'; n=$((n+1))
done
python3 summarize.py "$R" | grep -E '^run|^P1[0-2][0-9] '
