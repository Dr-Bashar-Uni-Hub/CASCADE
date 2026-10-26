# CASCADE-IDS run harness

Runs ONE Suricata configuration offline and records cost and alerts. Implements
protocol v0.1 sections 2, 4 and 5.

## One-time setup on the VM

    mkdir -p /data/harness /data/config /data/runs /data/manifests
    cp run_config.py prepare_base.py levels.json /data/harness/
    cd /data/harness
    python3 prepare_base.py /etc/suricata/suricata.yaml /data/config/base_suricata.yaml \
        | tee /data/manifests/base_yaml.sha256

## Self-test (before the real dataset arrives)

Uses the synthetic traffic from the earlier suricata_feasibility package.
With the real ET ruleset, the synthetic attacks may trigger few or no ET rules;
the test only checks that the harness runs end to end.

    cd ~/suricata_feasibility && python3 make_pcap.py
    tcpdump -r traffic.pcap -c 50 -w tiny.pcap
    cd /data/harness
    python3 run_config.py --config examples/full.json --pcap ~/suricata_feasibility/traffic.pcap \
        --out /data/runs/selftest/full --startup-pcap ~/suricata_feasibility/tiny.pcap
    python3 run_config.py --config examples/red.json --pcap ~/suricata_feasibility/traffic.pcap \
        --out /data/runs/selftest/red --startup-pcap ~/suricata_feasibility/tiny.pcap

Each run prints a summary and writes run.json, alerts.csv, rules.rules and suricata.log.
Exit code 0 = valid run, 1 = invalid (reasons in run.json "problems").
If Suricata reports a permission error, prefix the command with sudo.

## Behaviour worth knowing

- Capabilities not listed in a config run at full level (1).
- Rule fractions are nested: with the same seed, the rules kept at 0.25 are a subset of those at 0.5.
- Every `--set` key must already exist in the base config; a misspelled key stops the run
  (Suricata itself would silently ignore it).
- The harness refuses to overwrite an existing run directory.
- Suricata pinned to vCPU 1 by default (`--cpu`).
- Detection was deterministic across repeated runs in testing EXCEPT flow_id, which Suricata
  randomises per run. Label matching must use the 5-tuple and timestamp, never flow_id.
- K1/K2 level values and the rule-category lists in levels.json are provisional until the
  pilot and the ruleset snapshot.

## Label matching (label_match.py)

Maps each alert of a run to a labeled flow in the CIC-IDS2017 improved labels
(Liu, Engelen et al., CNS 2022) and writes matched_alerts.csv and detection.json into the run folder.

    # first run on each day: find the label clock offset (expect one offset to match far better)
    python3 label_match.py --labels /data/labels/thursday.csv --run /data/runs/phase0/P001 --check-offset
    # then
    python3 label_match.py --labels /data/labels/thursday.csv --run /data/runs/phase0/P001 --offset-hours <best>

"Attempted" flows are excluded from recall and reported separately; alerts on them are
not counted as false positives. Alerts matching no labeled flow are reported as unmatched.

## Main study (protocol v1.1)

One-time setup:

    cp main_schedule.json /data/config/main_schedule.json
    sha256sum /data/config/main_schedule.json     # must match the hash in the protocol
    python3 main_batch.py --status

Daytime, while you work (detection, 3 runs in parallel on vCPUs 1-3; timing not used):

    python3 main_batch.py --mode detection 2>&1 | tee -a /data/runs/main/console.log

Evening, laptop untouched (CPU cost runs, one at a time, with disturbance check and retry):

    python3 main_batch.py --mode cost --until 07:30 2>&1 | tee -a /data/runs/main/console.log

Both modes resume where they stopped, redo an interrupted run from scratch, and log to
/data/runs/main/progress.log. Only one mode can run at a time (a lock file enforces it), so
stop detection with Ctrl+C before starting cost runs in the evening.
make_schedule.py regenerates the identical schedule from its fixed seeds (for audit only).

## Window-length sensitivity (re-analysis, no Suricata runs)

    python3 window_sensitivity.py --runs /data/runs/main /data/runs/verify --out /data/runs/window_sensitivity.csv

Recomputes macro window recall for 30 s, 60 s, 120 s and 300 s windows from the existing
matched alerts; the 60 s column must reproduce week.json exactly (the script reports the check).

## Phase 5b (exploratory, protocol amendment v1.2)

    cp verify2_schedule.json /data/config/verify2_schedule.json
    V2="--schedule /data/config/verify2_schedule.json --runs /data/runs/verify2"
    python3 main_batch.py $V2 --mode detection        # 4 new safety-margin configurations
    python3 main_batch.py $V2 --mode cost --until 10:00   # those 4 + re-measure of all 25, one session

Items marked cost_only are re-measurements of the phase 5 configurations; they get no detection runs.
