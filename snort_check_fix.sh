#!/bin/bash
# Check the single-chunk Lua fix on Thursday (day mode, ~15 min). Expected: D1 and D2 near the K1-only value (pilot SP05: 0.253), not 0.409.
set -u
H=/data/harness; R=/data/runs/snort_fixcheck; C=/data/config/snort_fixcheck; mkdir -p $R $C; cd $H
for spec in 'D1|{"K1":0,"K3":0}' 'D2|{"K1":0,"K2":0}' 'D3|{"K1":0}'; do
  id=${spec%%|*}; lv=${spec#*|}; rm -rf $R/$id
  echo "{\"run_id\":\"$id\",\"phase\":\"fixcheck\",\"levels\":$lv}" > $C/$id.json
  python3 run_config_snort.py --config $C/$id.json --pcap /data/pcap/Thursday-WorkingHours.pcap --out $R/$id --no-calibration > $R/$id.out 2>&1
  python3 label_match.py --labels /data/labels/thursday.csv --run $R/$id --offset-hours 0 > $R/$id.match 2>&1
  python3 -c "import json;d=json.load(open('$R/$id/detection.json'));r=json.load(open('$R/$id/run.json'));print('$id',r['levels'],'alerts',r['n_alerts'],'macro_win',round(d['macro_window_recall'],3),{k[:14]:round(v['window_recall'],3) for k,v in d['per_class'].items()})"
done
