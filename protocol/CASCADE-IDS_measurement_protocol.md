# CASCADE-IDS Measurement Protocol v1.2

Oct 19, 2026 · @Dr. Bashar ALHAJAHMAD

## Purpose and hypotheses

This study measures the cost, detection value and dependencies of Suricata components on labeled traffic, fits the CASCADE model to those measurements, and tests whether exact optimization of the fitted model keeps more detection as the CPU budget shrinks. Everything below is fixed before the main experiments start; changes after that are logged as deviations (section 9).

**Research questions**

1. What CPU, memory and detection contribution does each Suricata component have on CIC-IDS2017 traffic?
2. Do components show measurable dependencies, and does the CASCADE model predict the detection of configurations it was not fitted on?
3. Under shrinking CPU budgets, do configurations chosen by exact optimization of the fitted model retain more detection than dependency-unaware and rule-of-thumb choices, when actually run in Suricata?

**Hypotheses** (thresholds frozen with v1.0, 23 Oct 2026)

- H1: At least one component pair has a fitted dependency strength of 0.5 or more.
- H2: On held-out configurations, the CASCADE model predicts macro window recall with a mean absolute error of 0.05 or less, and lower than a model without dependencies.
- H3: At budgets of 60% or less of full-configuration CPU, dependency-aware optimal configurations retain at least 5 percentage points more measured recall than the dependency-unaware optimum.

A negative result on H2 or H3 is still reported; it would mean the dependency model needs revising, which is itself a finding.

## Environment

All measurements run on the existing `cascade-testbed` VM, with Suricata reading recorded traffic files offline (`-r`). No network namespaces or live traffic are used, so the earlier testbed stays untouched.

| Item | Value (checked 19 Oct 2026) |
| --- | --- |
| Host | AMD Ryzen 7 7735HS laptop, 8 cores / 16 threads, base 3.2 GHz, 15.2 GB RAM; VirtualBox VM |
| vCPUs | 4 |
| Memory | 7.8 GiB, 4.0 GiB swap |
| OS | Ubuntu 24.04 |
| Suricata | 7.0.3 RELEASE (Ubuntu package) |
| Python | 3.12.3 |
| Data disk | `/data`, 147 GB ext4, 0% reserved |
| System disk | 35 GB free |

**Measurement hygiene**

- Suricata runs with `--runmode single`, pinned to one vCPU with `taskset -c 1`, so CPU times are comparable across runs.
- No Suricata or rule updates during the study. Record `suricata --build-info` once and store it with the results.
- Host plugged in, power mode set to best performance, heavy applications closed during measurement runs.
- Each run uses a fresh output directory. Only alerts and end-of-run stats are logged, to keep disk use and I/O cost low.
- The page cache is warmed by one discarded run per traffic file, so file reading does not distort the first measured run.
- The host runs near its memory limit (12.6 of 15.2 GB in use with the VM running), so close browsers and other large applications before measurement runs.
- The laptop CPU boosts above its base clock and slows when hot, so the pilot measures run-to-run CPU variation; if it exceeds 5%, boost is capped in the Windows power plan for all phases.

## Data and ground truth

The traffic is the CIC-IDS2017 packet captures (Monday to Friday) from the official UNB site, labeled with the improved flow labels of Liu, Engelen, Lynar, Essam and Joosen ("Error Prevalence in NIDS datasets: A Case Study on CIC-IDS-2017 and CSE-CIC-IDS-2018", IEEE CNS 2022), which supersede the authors' earlier 2021 correction. Labels come as one CSV per day (`CICIDS2017_improved.zip`, 328 MB, downloaded 21 Oct 2026, SHA-256 in `/data/manifests/labels.sha256`). Each flow row gives source and destination address and port, protocol, start timestamp, duration in microseconds, `Label` and `Attempted Category`.

**Attempted flows.** The improved labels mark attack flows that were launched but carried no effective attack as "Attempted". They are excluded from the recall denominator, alerts on them are not counted as false positives, and both counts are reported separately per class. The definition is cited from the authors' documentation page.

**Attack classes covered:** FTP and SSH brute force; DoS (Hulk, GoldenEye, Slowloris, Slowhttptest); Heartbleed; web attacks (brute force, XSS, SQL injection); infiltration; botnet; port scan; DDoS. Monday is benign only and serves as the false-positive and pure-cost reference.

**Ruleset:** Emerging Threats Open, downloaded once with `suricata-update`, saved as a dated snapshot with its SHA-256 and rule count, and used unchanged for every run.

**Matching alerts to labels**

1. Each alert is mapped to a flow with the same protocol and endpoint pair (either direction) whose time span, widened by 2 seconds on each side, contains the alert time. The label clock offset is checked once per day by trying offsets of -6 to +6 hours and keeping the one with the highest match rate. Suricata's own flow ID is never used, because it is random per run.
2. A labeled attack flow counts as detected if at least one alert maps to it.
3. An attack episode, defined as a run of same-class attack flows with no gap longer than 5 minutes between start times, counts as detected if any of its flows is detected.
4. Alerts mapping to benign flows count as false positives; alerts mapping to no labeled flow are reported as unmatched, and a high unmatched share means the matching needs checking.

The primary detection measure is window recall per attack class (section 5), changed from flow recall after the pilot. Flow recall and episode-level detection are reported alongside it.

**Storage layout:** `/data/pcap` (traffic, read-only after download), `/data/rules` (snapshot), `/data/runs/<phase>/<run-id>` (outputs), `/data/manifests` (hashes and run logs).

**Traffic files (downloaded 19–20 Oct 2026).** From the official UNB download site; each matched its official MD5 file on Windows and again after copying into the VM.

| File | Size | SHA-256 |
| --- | --- | --- |
| Monday-WorkingHours.pcap | 11 GB | `f6eac599358f216b074338813a1cf7be3cc4e91d116e13efc0dc71f2cca11972` |
| Tuesday-WorkingHours.pcap | 11 GB | `080c2250154c5a174c03660ed0f75a3858d41a27511ba716e780d7bcb1ec4c57` |
| Wednesday-workingHours.pcap | 13 GB | `cd2674db7559a53f24bc03be3239b315700174ccaef72d10f5edc4c1a08f6186` |
| Thursday-WorkingHours.pcap | 7.8 GB | `38f8b1bb276849bf1721f7c4de22bebfa7f59a74e52286d4c0a37edbb118fe01` |
| Friday-WorkingHours.pcap | 8.3 GB | `beff0dcce1eebc9b2454582f4dc8ed0ba0112b2c619a710bf03af93147254cd0` |

## Capabilities and operating levels

Eleven capabilities are varied; everything else (packet decoding, flow tracking, detection-engine profile `medium`) stays at default in every run. Level 1.0 is the default or full setting; 0 is off or minimal.

| ID | Capability | Suricata setting varied | Levels | Hypothesized upstream dependency | Attack classes expected to rely on it |
| --- | --- | --- | --- | --- | --- |
| K1 | Stream reassembly | `stream.reassembly.depth` | 6: depth 1 B, 512 B, 2 KB, 8 KB, 32 KB, 1 MB (levels 0, 0.2, 0.4, 0.6, 0.8, 1) | none | all payload-based detection |
| K2 | HTTP parser | `app-layer.protocols.http.enabled`, request-body limit | off / on | K1 | web attacks, DoS Hulk/GoldenEye/Slowloris |
| K3 | TLS parser | `app-layer.protocols.tls.enabled` | off / on | K1 | Heartbleed, encrypted botnet traffic |
| K4 | DNS parser | `app-layer.protocols.dns.*.enabled` | off / on | none (UDP) | botnet, infiltration |
| K5 | SSH and FTP parsers | `app-layer.protocols.ssh/ftp.enabled` | off / on | K1 | SSH and FTP brute force |
| K6 | Web-attack rules | ET web-server and web-application categories | fraction 0, .25, .5, .75, 1 | K2 | web attacks |
| K7 | Scan rules | ET scan category | fraction 0, .25, .5, .75, 1 | none | port scan |
| K8 | Exploit rules | ET exploit category | fraction 0, .25, .5, .75, 1 | K1, K3 | Heartbleed, infiltration |
| K9 | Malware and C2 rules | ET MALWARE and CNC categories | fraction 0, .25, .5, .75, 1 | K2, K3, K4 | botnet, infiltration |
| K10 | DoS rules | ET DoS category | fraction 0, .25, .5, .75, 1 | none | DoS, DDoS |

**K11, low-confidence rules (added after the pilot).** ET categories INFO, HUNTING, DYN\_DNS and JA3, about 12,100 rules, levels as for K6 to K10 (rule fractions). On Monday's benign traffic, three JA3 "Possible Adware" rules alone produced about 6,100 of 11,917 false alarms, and operators commonly disable these categories first. No upstream dependency is hypothesized.

**Level changes from the pilot.** K2 is off/on only: request and response body limits from 4 KB to 100 KB changed neither detection nor cost measurably, because the CIC-IDS2017 web attacks sit in the URL. K1 levels were moved below 64 KB, because detection was unchanged from 64 KB to 1 MB (cost within 9%), while 1 byte cut cost by 37% and removed all payload-based detection.

**How rule fractions are formed.** Rules in a category are shuffled once with a fixed seed (20261019); level 0.25 keeps the first quarter, and so on, so each level contains the one below it. Two extra seeds (20261119 and 20261219) are run at level 0.5 for each rule capability, to check that results do not depend on which rules happen to be kept.

**Dependencies in the last-but-one column are hypotheses only.** They decide which pairs are tested first; their strengths come only from the measurements in section 6. Rules in categories not listed here stay enabled in every run and count as fixed background cost.

**Ruleset snapshot (19 Oct 2026).** ET Open for Suricata 7.0.3, 53,150 enabled rules, SHA-256 `6c051c4c137058938bea64524207addf7049cc76109f8f8397f0b0edc886569b`.

| Capability | Categories | Enabled rules |
| --- | --- | --- |
| K6 | WEB\_SERVER, WEB\_SPECIFIC\_APPS | 6,776 |
| K7 | SCAN | 274 |
| K8 | EXPLOIT | 1,669 |
| K9 | MALWARE, CNC | 19,322 |
| K10 | DOS | 61 |
| Fixed background | all other categories (largest: DYN\_DNS 6,096, INFO 4,553, PHISHING 2,952, EXPLOIT\_KIT 2,788) | 25,048 |

Rules marked `noalert` (flowbit setters, which other rules rely on) are never removed, so a dependent rule is not silently broken by a reduced rule fraction. About 47% of enabled rules sit in the fixed background, so the lowest reachable CPU budget is set by them; whether to add an informational-rules capability (INFO, HUNTING, DYN\_DNS) is an open decision.

## Metrics

The budgeted resource is traffic-processing CPU time; memory and false positives are reported but not optimized in the primary analysis.

| Metric | Definition | Role |
| --- | --- | --- |
| Processing CPU (s/GB) | User + system CPU of the Suricata process, minus the startup CPU of the same configuration on a near-empty traffic file, divided by GB processed | Primary cost; the budget constraint |
| Startup CPU (s) | CPU on the near-empty file (rule loading, initialization) | Reported |
| Peak memory (MB) | Maximum resident set size | Secondary constraint in a sensitivity analysis |
| Wall time (s) | End-to-end run time | Reported |
| Recall per class | Detected labeled attack flows / all labeled attack flows of that class | Building block of protection |
| Macro recall | Unweighted mean of per-class recall | Secondary protection measure |
| Episode detection | Share of attack episodes with at least one detected flow | Secondary protection measure |
| False positives (per hour) | Alerts mapped to benign flows, per hour of traffic | Reported; Monday gives the clean reference |

**Primary protection measure: macro window recall.** For each attack class, the one-minute windows in which at least one of its real (not attempted) flows starts; window recall is the share of those windows in which at least one such flow raised an alert. Macro window recall is the unweighted mean over all 15 attack classes of the week, and is the model's P. Classes with zero detection stay in the mean.

This replaces flow recall as primary measure after the pilot: floods and scans consist of tens of thousands of near-identical flows while rules alert once per many events, so flow recall stayed near zero for attacks Suricata clearly noticed (for example DoS Hulk 1.5% of flows but 18 of 19 minutes; Friday port scan 0.1% of flows but all 5 episodes).

Macro window recall weights every attack class equally, so rare classes such as Heartbleed count as much as DoS. A sensitivity analysis repeats the main results with classes weighted by episode count.

## Experimental design

The study runs in six phases: 150 configurations in phases 1 to 4, plus about 35 in phase 5 after model fitting.

| Phase | Configurations | Runs per configuration | Purpose | In model fitting? |
| --- | --- | --- | --- | --- |
| 0. Pilot | full config + 3 reduced configs, on Thursday only | 2 | Time per run, determinism of detection, level values for K1 and K2, non-zero recall per class | No, excluded |
| 1. Baseline | full config | 5 cost, 1 detection | Reference cost and detection | Yes |
| 2. Single-factor | each capability at each lower level, others full: 9 configs for K1 to K5, 24 for K6 to K11, plus K6 to K11 at level 0.5 with two extra rule seeds (45 in total) | 3 cost, 1 detection | Direct cost and value per capability | Yes |
| 3. Pairwise | all 55 pairs with both off; 9 hypothesized edges at middle levels (64 in total) | 3 cost, 1 detection | Dependency strengths | Yes |
| 4. Validation | 40 random configurations, drawn with seed 20261020 before any results exist | 3 cost, 1 detection | Test model predictions | No, held out |
| 5. Verification | optimal and baseline configurations at 7 budgets (section 8) | 3 cost, 1 detection | Check optimization in real runs | No |

**Repetitions.** Offline detection with one thread is expected to be deterministic; the pilot checks this by running the same configuration twice. If it is, detection is measured once per configuration on the full traffic, and cost is repeated three times. If it is not, detection is also repeated three times and reported as a mean.

**Cost sample.** Decided from the pilot: detection is measured once per configuration on the full week (five runs, one per day, about 15 minutes in total), and cost is measured on Thursday traffic in three repeats (about 3 minutes each). Thursday's processing CPU varied with a coefficient of variation of 2.7% in unattended runs.

**Order.** Within each phase, configurations run in a random order (seed 20261021) so drift in host performance does not line up with any capability. A full-configuration reference cost run is inserted before every 10th configuration.

## Model fitting and validation

The CASCADE model is fitted on phases 1 to 3 and judged only on the held-out phase 4 configurations.

The model, unchanged from the Colab notebooks:

```latex
e_i = x_i \prod_{p \in \mathrm{parents}(i)} \left(1 - d_{pi}\,(1 - e_p)\right), \qquad P(x) = \sum_i w_i\, e_i
```

**Cost side.** Each capability's cost at each level is measured directly in phase 2 as the drop from full-configuration cost. Total cost is modeled as additive; phase 4 checks this, and an additivity error above 10% is reported and handled with pairwise cost corrections.

**Protection side.** Weights w and dependency strengths d (bounded to 0 to 1) are fitted by bounded nonlinear least squares on measured macro window recall. Only edges in the hypothesized set, plus any pair whose phase 3 interaction exceeds 0.02 recall, are allowed, to avoid fitting noise.

**Competing models**, all fitted on the same data:

1. CASCADE (dependency-aware), as above.
2. Additive: the same model with every d set to 0.
3. Per-class noisy-OR: each attack class is detected if any enabled path detects it, a common alternative structure.

**Validation.** For each model, report mean absolute error and maximum error of predicted vs measured macro window recall on the 40 held-out configurations, with bootstrap 95% intervals. H2 is supported if CASCADE meets the 0.05 threshold and beats the additive model. If noisy-OR does better, the paper reports that and uses it in section 8.

**Protection-model results (24 Oct 2026; detection pass complete, 150 configurations).** Fitted on phases 1–3 (110 configurations), validated on the 40 held-out phase 4 configurations.

| Model | Parameters | Training RMSE | Held-out MAE \[95% CI\] | Held-out max error |
| --- | --- | --- | --- | --- |
| Additive (no dependencies) | 34 | 0.020 | 0.069 \[0.055, 0.085\] | 0.190 |
| CASCADE, pre-registered form | 21 | 0.016 | 0.025 \[0.020, 0.030\] | 0.071 |
| CASCADE + fitted level curves (exploratory) | 43 | 0.005 | 0.011 \[0.007, 0.014\] | 0.044 |
| Per-class noisy-OR on CASCADE | 161 | 0.007 | 0.010 \[0.008, 0.012\] | 0.031 |

- **H1 supported.** Fitted dependency strengths K1→K2 = 0.92 and K2→K6 = 0.94 (pre-registered form); all other hypothesized edges fitted at or near 0.
- **H2 supported** for the pre-registered model: MAE 0.025, below 0.05 and below the additive model (0.069, which itself fails the threshold).
- **Model adaptation, reported as such.** All CASCADE variants include an intercept b0 (fitted 0.27–0.28): detection by the always-on background rules, equivalent to a fixed capability at full level. The level curves were not pre-registered and are reported as exploratory.
- **Model for section 8.** The per-class noisy-OR model is not meaningfully better than CASCADE with level curves (overlapping intervals) at almost four times the parameters, so section 8 is run with both; any difference in the chosen configurations is reported.

## Optimization and verification

The fitted model is solved exactly with SCIP at budgets of 100%, 90%, 80%, 70%, 60%, 50% and 40% of full-configuration processing CPU, and every chosen configuration is then run in Suricata.

**Configurations compared at each budget**

| Method | How it chooses |
| --- | --- |
| Dependency-aware optimum | SCIP on the fitted CASCADE model (or the better model from section 7) |
| Dependency-unaware optimum | SCIP on the additive model, then evaluated in real runs |
| Rules first | Operator rule of thumb: reduce rule categories by cost per rule, keep parsers on |
| Most expensive first | Switch off or lower the costliest capability until within budget |
| CASCADE V2 heuristic | The existing greedy-plus-repair algorithm, for continuity with the earlier work |

**Gradual erosion.** A second analysis lowers the budget step by step from 100% to 40%. It compares re-solving from scratch at each step with a constrained variant that never re-enables a capability once lowered, and reports the recall difference and the number of reconfigurations each needs.

**Outcomes.** For each method and budget: measured macro recall, measured CPU (must not exceed the budget by more than the run-to-run noise from phase 1), predicted vs measured recall, and false positives. H3 is tested with a paired comparison across budgets of 60% or less, with bootstrap intervals over attack episodes.

**Cost-model results (25 Oct 2026; cost pass complete).** Reference runs: median 112.6 s, coefficient of variation 3.2%. Fitted on phases 1–3, validated on phase 4:

| Cost model | Held-out MAE | Max error |
| --- | --- | --- |
| Additive | 8.1 s (10.8%) | 23.6 s |
| Dependency-aware (cost of a capability scales with its upstream inputs) | 3.0 s (3.7%) | 8.9 s |

The additive model exceeds the 10% additivity limit, because costs cascade: with stream reassembly off, the HTTP, TLS and SSH/FTP parsers and the payload rules have little left to process, so switching them off as well saves almost nothing. Instead of the pairwise corrections named in section 7, the same dependency structure as the protection model is used for cost (a deviation, logged below); its error is close to run-to-run noise. Predicted cost floor with every capability at 0: 59.5 s, 53% of full.

**Model-based optimization (exact, by enumerating all 1.5 million configurations).** Predicted macro window recall (CASCADE + level curves) and predicted cost under the dependency-aware cost model:

| Budget | Dependency-aware optimum | Dependency-unaware optimum | CASCADE V2 heuristic | Most expensive first | Rules first |
| --- | --- | --- | --- | --- | --- |
| 100% | 0.578 | 0.574 | 0.578 | 0.578 | 0.578 |
| 90% | 0.577 | 0.574 | 0.577 | 0.442 | 0.425 |
| 80% | 0.575 | 0.574 | 0.574 | 0.442 | 0.292 |
| 70% | 0.560 | 0.573 (predicted cost 72% of full, over budget) | 0.556 | 0.442 | 0.281 |
| 60% | 0.431 | 0.441 (62%, over budget) | 0.430 | 0.431 | 0.281 |
| 50%, 40% | infeasible | 0.431 (56% and 54%, over budget) | infeasible | infeasible | infeasible |

The dependency-unaware method protects as well as the dependency-aware one at high budgets, but from 70% down it picks configurations whose real cost, under the cascading cost structure, exceeds the budget, and at 50% and 40% it believes it has met budgets no configuration can meet. Gradual erosion from 100% to 60% in 5% steps: re-solving at each step raised capability levels again 6 times; the never-re-enable path lost on average 0.002 macro window recall (at most 0.015, at 65%). Phase 5 verifies 25 distinct configurations from this table in Suricata (schedule `verify_schedule.json`, SHA-256 `3c81cd4a0ef40c3098ebf8c4605a8de889954afbd031ad58e4d0ba280924af0a`, order seed 20261025); the full configuration is taken from C001.

**Verification results (phase 5, 25 Oct 2026).** All 25 configurations measured (detection on the full week, cost on Thursday in 3 repeats). The cost pass ran in two sessions, interrupted by a Windows restart; session references were 115.5 and 106.3 s (session 1) and 120.3 s (session 2), so costs are also reported normalized to the 112.6 s full-configuration reference of each session (sensitivity analysis).

- **Detection predictions hold.** Predicted vs measured macro window recall: mean absolute difference about 0.003, largest 0.008, across all 25.
- **Cost predictions are optimistic for the chosen configurations.** Dependency-aware cost model: mean absolute error 5.0 s (5.7%), mean bias −4.2 s; additive cost model: 9.7 s (12.9%), bias −9.5 s. Selecting the configurations the model believes are cheapest biases the error in this direction.

| Budget | Dependency-aware optimum | Dependency-unaware optimum | CASCADE V2 | Most expensive first | Rules first |
| --- | --- | --- | --- | --- | --- |
| 100% | 0.579, 96% | 0.579, 74% | full config (C001) | full config | full config |
| 90% | 0.575, 87% | 0.579, 74% | 0.579, 92% | 0.442, 87% | 0.427, 91% |
| 80% | 0.575, 88% | 0.579, 74% | 0.575, 82% | 0.442, 81% | 0.295, 78% |
| 70% | 0.562, 80% | 0.579, 84% | 0.558, 73% | 0.437, 74% | 0.275, 55% |
| 60% | 0.432, 60% | 0.437, 72% | 0.432, 53% | 0.432, 55% | 0.275, 55% |
| 50% | infeasible | 0.432, 55% | infeasible | infeasible | infeasible |
| 40% | infeasible | 0.432, 57% | infeasible | infeasible | infeasible |

Cells: measured macro window recall, measured median processing CPU as a share of 112.6 s (raw). With session normalization the 70% configurations of every method except rules first exceed the budget by 6–7% (dependency-unaware 12%); at 60% only the dependency-unaware configuration exceeds it (by 22%); its 50% and 40% configurations exceed by 11% and 45%.

- **H3 not supported as stated:** at 60%, the dependency-unaware configuration measured 0.437 against 0.432, but used 22% more CPU than the budget allows.
- **Against operator rules of thumb** the dependency-aware optimum keeps full detection at 80–90% of the CPU, while most-expensive-first loses 13 points and rules-first 15–28 points.
- **Practical implication:** because the optimizer exploits small cost-model errors, budgets should be planned with a safety margin of about 5%.

**Results archive (25 Oct 2026).** `cascade_results_20261025.tar.gz`, 975 MB: all run records (1,498 `run.json`), the 175 week-level results, manifests, configuration, scripts, ruleset snapshot and label hashes; per-run rule-file copies, disturbed and incomplete runs excluded (each rule file is reproducible from the snapshot and its seed, and its hash is in `run.json`). SHA-256 `09c1fb65186c172dc84e034d5ab5ba7b85cd4cf697880c8beaf1d91bba9475e5`, stored on the VM data disk and on the host (`E:\cascade_backup`).

## Exclusions, reproducibility and deviations

Every run is logged, including failed ones; a run is excluded only for the reasons below, and excluded runs are kept and counted in the paper.

**A run is excluded if**

- Suricata exits with an error, or its stats show packets not processed or read errors;
- the traffic file or ruleset hash does not match the manifest;
- it is a Thursday cost run flagged as disturbed (calibration more than 10% slower than the 4.25 s baseline, or before–after drift above 10%), in which case it is moved aside and retried, up to three attempts.

**What is frozen, once per phase rather than per step**

- This protocol (version number and date), the ruleset snapshot, the base `suricata.yaml`, the traffic files, the cost sample and the analysis code, each with a SHA-256 in `/data/manifests`.
- All scripts and this protocol in one git repository; each phase starts from a tagged commit.

**Freeze record, v1.0 (23 Oct 2026).** Main-study schedule `main_schedule.json` (150 configurations in phases 1–4 plus 15 reference runs; seeds 20261019, 20261119, 20261219, 20261020, 20261021), generated by `make_schedule.py`.

| Artifact | SHA-256 |
| --- | --- |
| main\_schedule.json | `39596278c3aec536c4dd133754d0c338d2fe77720cb7164f55cffbe53be443f8` |
| levels.json | `e21a485b44fe9cb0d4dbe002a52a8229f13201d2fcee596f315e75a3fe4779b7` |
| run\_config.py | `dd53b74b21a754eca8ffe8ffc99e5cfa46d64a1bedbe77b370ba56375ca823ad` |
| label\_match.py | `f293d12bc29759043fb4002b5460fc77c0a60f0de963f40c8d3f75bd7dfdd254` |
| week\_score.py | `9e3f2ced0c25e816d97101845dff9c10e7c1bbbadbca0818f9c7b03f98c36328` |
| main\_batch.py | `73943a3716ee7ea31fcbbbcee71c130f632ac78fcb6351318a33ab762cd17369 (v1.1, with the 23 Oct fix)` |
| base\_suricata.yaml | `1286e2fd84bb8535bed1d69e1dedf006585e96aa58fe8a58099774f176d67d55` |
| ET Open ruleset | `6c051c4c137058938bea64524207addf7049cc76109f8f8397f0b0edc886569b` |

**Amendment v1.1 (23 Oct 2026, before any main-study run).** Detection and cost are run as two separate passes over the same frozen schedule. Detection pass: one run per day on the full traffic for every configuration, three runs in parallel on vCPUs 1–3, without timing, so it may run while the host is in use (detection was identical across all pilot repeats, including disturbed ones). Cost pass: three Thursday cost runs per configuration (five for the baseline) and one per reference item, one at a time on vCPU 1, unattended, with the disturbance check. A lock file prevents the two passes from overlapping. The schedule, levels and measures are unchanged; only `main_batch.py` changed. Estimated time: detection about 2–3 days in the background, cost about 25 hours (three nights).

**Amendment v1.2 (26 Oct 2026, after the phase 5 results; exploratory).** Phase 5b, schedule `verify2_schedule.json` (SHA-256 `64df7becc0236766d6046ddcda8296e88a4fd747377843b4dd7ab8f1b0a6a08c`, order seed 20261026): detection and cost for the four new configurations chosen by the dependency-aware optimum with a 5% or 10% safety margin, and a cost-only re-measurement of all 25 phase 5 configurations in one uninterrupted session, to address the session confound. `main_batch.py` gained a cost-only item type (SHA-256 `a792d3f293dda8a73499eeb258f05badb2dff5dc05247d965a3f6e0bb5f06db8`). Window-length sensitivity (30, 60, 120, 300 s) is computed from existing matched alerts with `window_sensitivity.py`. Both analyses are reported as exploratory; the phase 5 results remain the primary verification.

**Deviations.** Any change after phase 1 starts is added here as a dated line with its reason, and the paper reports all of them. Bug fixes in scripts are allowed; changes to levels, metrics, thresholds or held-out configurations are deviations.

| Date | Deviation | Reason |
| --- | --- | --- |
| 23 Oct 2026 | Script fix in `main_batch.py` (new SHA-256 `73943a3716ee7ea31fcbbbcee71c130f632ac78fcb6351318a33ab762cd17369`): a cost run disturbed three times in a row is skipped and retried in the next cost session instead of stopping the session. No measurement, level or schedule changed. | On the first night, C027/cost2 was disturbed three times in a row (05:32–05:43, host busy shortly before Windows restarted the laptop); under the old rule this would have ended the session. |

Further deviations (25 Oct 2026):

- **Model intercept.** All CASCADE protection and cost models include an intercept for the always-on background (rules outside K6–K11, packet decoding); without it the models cannot represent detection or cost with every capability at 0.
- **Level curves.** Fitted operating-level curves were added to CASCADE as an exploratory variant; H2 is tested on the pre-registered form.
- **Cost model.** The additive cost model failed the 10% limit (10.8%); a dependency-aware cost model replaces the pairwise corrections named in section 7.
- **Budgets.** 50% and 40% of full cost are below the predicted cost floor (53%); they are kept in the tables as infeasible, and H3 is tested at 60%, the only feasible budget at or below 60%. The dependency-unaware configurations chosen for 50% and 40% are still verified, to measure how far they overrun.
- **Ties.** Among configurations with equal predicted protection, every method takes the cheapest.
- **Phase 5 order.** Seed 20261025 for the verification order (not set in v1.0).

## Pilot findings so far

Phase 0 runs on Thursday traffic, full configuration, 21–22 Oct 2026. These are excluded from all results.

| Run | Base config | Processing CPU (s) | Alerts | Macro recall |
| --- | --- | --- | --- | --- |
| P001 | Ubuntu default HOME\_NET | 215.5 | 29,624 | 0.085 |
| P002 | same | 203.2 | 29,593 | 0.085 |
| P003 | same | 176.4 | 29,589 | 0.085 |
| P004 | HOME\_NET = 192.168.10.0/24 | 237.4 | 30,508 | 0.423 |

- **Run time.** About 4–5 minutes per Thursday run (9.3 million packets), so roughly 30 minutes for a full week. Peak memory about 590 MB.
- **Label clock.** Label timestamps are UTC (offset 0): 99.3% of alerts match a labeled flow at offset 0 and none at any other offset.
- **Startup cost.** Loading 53,150 rules takes 31–41 CPU seconds per run, reported separately from processing cost.
- **Repeatability.** Flow-level detection was identical across P001–P003; total alert counts differed by up to 35. Detection is therefore measured once per configuration, to be rechecked on reduced configurations.
- **CPU variation.** Processing CPU varied by up to a factor of two in P001–P006 (103–237 s for identical configurations) because other work on the host inflated the VM's measured CPU time; VirtualBox exposes no hardware instruction counters, so instruction counting is not possible. In three runs with the laptop left alone (P010–P012) processing CPU was 114.7, 108.9 and 113.5 s (coefficient of variation 2.7%), within the 5% limit. A fixed calibration workload around each run did not reduce variation (6.6% spread when normalized), so raw processing CPU stays the cost measure and the calibration drift is kept only as a disturbance flag. Rules from now on: cost runs only in unattended sessions with boost capped, 3 repeats per configuration, median reported, a full-configuration reference run at the start of each repeat block, and any run more than 10% from its configuration's median is repeated.
- **HOME\_NET.** With the Ubuntu default, HOME\_NET includes 172.16.0.0/12, so the NAT address 172.16.0.1 that carries the external attacks counted as internal and most ET rules never fired: web-attack recall was 0. With HOME\_NET set to the victim network 192.168.10.0/24 and EXTERNAL\_NET to !$HOME\_NET, XSS recall rose to 1.0 and SQL injection to 0.69. This is now the frozen base configuration (base yaml SHA-256 `1286e2fd84bb8535bed1d69e1dedf006585e96aa58fe8a58099774f176d67d55`). A sensitivity run with EXTERNAL\_NET = any is planned for the internal port scan.
- **Undetected classes.** Web brute force (0/73 flows) and the internal port scan (0.6%) stay low with the corrected configuration; they are reported as genuine misses and kept in macro recall.
- **Full week, full configuration (P020–P023, P30).** Window recall per class: FTP brute force, DoS GoldenEye, DDoS, SQL injection and XSS 1.00; Infiltration–Portscan 0.97; DoS Hulk 0.95; SSH brute force 0.48; Friday port scan 0.46; Infiltration 0.32; Botnet 0.22; Slowhttptest 0.12; Heartbleed 0.09 (one detected episode spread over 11 minutes); Slowloris and web brute force 0. Mean over the 15 classes about 0.57. The 2017 botnet is still detected by the 2026 rules.
- **Unmatched alerts.** 4–7.5% of alerts on Tuesday, Wednesday and Friday match no labeled flow (0.7% on Thursday); widening the time tolerance from 2 to 10 seconds left the count unchanged, so they belong to traffic without a labeled flow and are excluded from all measures.
- **EXTERNAL\_NET = any (P060).** Internal port scan flow recall rose only from 0.6% to 1.1% while benign alerts rose from 4,738 to 5,065; the standard setting is kept.
- **Decisions (23 Oct 2026).** Primary measure macro window recall; K2 off/on; K1 levels moved below 64 KB; K11 added; detection on the full week, cost on Thursday.
- **K1 depth levels (batch 3, Thursday, detection).** Window recall 0.259 at 512 B (SQL injection and XSS lost), 0.598 at 2 KB (SQL injection 0.75, XSS 0.94), 0.659 at 8 KB, 32 KB and 1 MB. The new levels are confirmed: the trade-off lies between 512 B and 8 KB. Benign alerts vary non-monotonically with depth (4,059 at 512 B, 5,626 at 8 KB, 4,738 at 1 MB).
- **K11 off (batch 3).** Detection unchanged on Thursday (0.659); benign alerts fell from 4,738 to 3,557 on Thursday and from 11,917 to 4,075 on Monday (−66%); peak memory 589 → 518 MB.
- **Disturbance flag.** Batch 3 ran while the host was in use: calibration took 7–8.6 s instead of about 4.05 s, and processing CPU nearly doubled, but before-after drift stayed small because the host was busy throughout. From now on a run is flagged as disturbed, and automatically retried, if either calibration is more than 10% slower than the 4.05 s baseline or drift exceeds 10%. Batch 3 costs are discarded and repeated (batch 3b); its detection results stand.
- **Costs, batch 3b (P100–P120, unattended, Thursday, median of 3).** Full configuration 114.4 s. K1: 1 B 68.0 s (−41%), 512 B 87.4 s (−24%), 2 KB 91.9 s (−20%), 8 KB 100.9 s (−12%), 32 KB 102.3 s (−11%). K11 off 109.5 s (−4%), peak memory −70 to −100 MB. Repeats agreed within 2–6% (coefficient of variation); detection was identical in every repeat. 8 KB depth keeps full Thursday detection at 12% less CPU than the 1 MB default. Two runs were flagged as disturbed and retried automatically. Undisturbed calibration in this session took 4.14–4.37 s, so the baseline is raised to 4.25 s for the main study.

## Open decisions and next steps

All settled; the protocol was frozen as v1.0 on 23 Oct 2026.

**Open decisions**

- K1 levels confirmed by pilot batches 3 and 3b.
- H2 and H3 thresholds frozen as drafted, stated for macro window recall.

**Next steps**

- [x] Record host core count
- [x] Download CIC-IDS2017 traffic to `/data/pcap`, hash every file
- [x] Download corrected labels and check the citation
- [x] Take the ET Open snapshot with `suricata-update`, hash it, record rule counts per category
- [x] Write the run harness (one config in, cost and alerts out) and the label-matching script
- [ ] Run phase 0 pilot on Thursday traffic
- [ ] Settle open decisions, bump protocol to v1.0, start phase 1
- [ ] Literature review in parallel
