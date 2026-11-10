#!/usr/bin/env bash
# Pilot batch 2 (protocol phase 0). Run with the laptop left alone (about 2 hours).
#   A: full configuration on the other four days (detection baseline per day)
#   B: cost curves for K1 and K2 levels on Thursday, 3 repeats, full reference run at the start of each repeat
#   C: sensitivity run with EXTERNAL_NET = any on Thursday
# Existing run folders are skipped, so the script can simply be restarted after an interruption.
set -u
H=/data/harness; R=/data/runs/phase0; C=/data/config
declare -A PCAP=([monday]=Monday-WorkingHours.pcap [tuesday]=Tuesday-WorkingHours.pcap
                 [wednesday]=Wednesday-workingHours.pcap [thursday]=Thursday-WorkingHours.pcap
                 [friday]=Friday-WorkingHours.pcap)
cd "$H"

run() {  # run <id> <day> <levels-json> [base-yaml]
  local id=$1 day=$2 levels=$3 base=${4:-$C/base_suricata.yaml}
  if [ -d "$R/$id" ]; then echo "skip $id (exists)"; return; fi
  echo "{\"run_id\":\"$id\",\"phase\":\"pilot\",\"levels\":$levels}" > "$C/$id.json"
  python3 run_config.py --config "$C/$id.json" --pcap "/data/pcap/${PCAP[$day]}" --out "$R/$id" \
      --startup-pcap "$C/tiny.pcap" --base-yaml "$base" > "$R/$id.out" 2>&1
  python3 label_match.py --labels "/data/labels/$day.csv" --run "$R/$id" --offset-hours 0 >> "$R/$id.out" 2>&1
  echo "$(date +%H:%M) $id done ($day $levels)"
}

# A: other days, full configuration
run P020 monday    '{}'
run P021 tuesday   '{}'
run P022 wednesday '{}'
run P023 friday    '{}'

# B: K1 and K2 cost curves on Thursday
n=30
for rep in 1 2 3; do
  run P$n thursday '{}'; n=$((n+1))                       # reference
  for lv in 0.25 0.5 0.75; do
    run P$n thursday "{\"K1\":$lv}"; n=$((n+1))
    run P$n thursday "{\"K2\":$lv}"; n=$((n+1))
  done
done

# C: EXTERNAL_NET = any
[ -f "$C/base_any.yaml" ] || python3 prepare_base.py /etc/suricata/suricata.yaml "$C/base_any.yaml" --external-net any \
    | tee /data/manifests/base_any_yaml.sha256
run P060 thursday '{}' "$C/base_any.yaml"

python3 summarize.py "$R"
