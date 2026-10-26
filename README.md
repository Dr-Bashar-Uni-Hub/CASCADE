# CASCADE

**Measuring and exploiting component dependencies to configure signature-based intrusion detection under CPU budgets.**

CASCADE measures how the components of a signature-based network intrusion detection system (NIDS) depend on one another, models those dependencies for detection and CPU cost, and uses the models to choose configurations under a CPU budget. The study behind this repository was run on Suricata 7.0.3 with the Emerging Threats Open ruleset and the CIC-IDS2017 traffic with the corrected labels of Liu et al. (CNS 2022).

> Manuscript in preparation for the *Journal of Information Security and Applications*. Please cite the paper once published (see `CITATION.cff`).

## What the study shows

| Finding | Status |
| --- | --- |
| Component dependencies can be measured, and modelling them improves prediction (held-out detection error 0.025 vs 0.069 for an additive model; CPU-cost error 3.7% vs 10.8%) | Established |
| Dependency-aware cost modelling makes CPU-budget decisions more reliable than additive costing | Partially established |
| Dependency-aware optimisation consistently produces better feasible configurations than dependency-unaware optimisation | Not established (pre-registered hypothesis H3 not supported) |

## Repository layout

| Folder | Contents |
| --- | --- |
| `protocol/` | The pre-registered measurement protocol, with all amendments, deviations, pilot findings and freeze hashes |
| `harness/` | Measurement harness: running one Suricata configuration (`run_config.py`), matching alerts to labelled flows (`label_match.py`), week-level scoring, the resumable batch runner (`main_batch.py`), schedule generation, window-length re-analysis |
| `schedules/` | Frozen run schedules (main study, verification, exploratory phase 5b) with SHA-256 sums |
| `analysis/` | Model fitting, exact optimisation, statistics and figure scripts |
| `results/` | Per-configuration summaries used by the analysis (see `results/README.md`) |
| `figures/` | Manuscript figures (PNG 300 dpi and PDF) |
| `legacy_synthetic/` | Earlier synthetic-graph notebooks (CASCADE V1/V2), kept for continuity; not used in the paper's results |
| `docs/` | Data sources, hashes and environment |

The full per-run records (1,498 run records, matched alerts, manifests; about 1 GB) are archived separately: **[Zenodo DOI to be added]**.

## Reproducing the analysis (no Suricata needed)

```bash
pip install -r requirements.txt
cd analysis
python3 costfit.py      # cost models (writes costA.npy, costC.npy)
python3 pc_fast.py      # per-class protection model (writes pc_params.npy)
python3 fit.py          # protection models: Table 4
python3 stats.py        # bootstrap intervals
python3 audit.py        # verification feasibility: Table 6
python3 optimize.py     # exact optimisation over 1.5 M configurations
python3 margin.py       # exploratory safety-margin analysis (Table 7)
python3 winfit.py       # window-length sensitivity (Table 8)
python3 make_figs.py    # figures
```

## Reproducing the measurements

Requires Ubuntu 24.04, Suricata 7.0.3, Python 3.12 with pandas, the CIC-IDS2017 captures and corrected labels, and the ruleset snapshot (see `docs/DATA.md`). The harness expects the layout `/data/pcap`, `/data/labels`, `/data/rules`, `/data/config`; see `harness/README.md` and the protocol for the exact procedure, measurement-control rules and seeds.

## License

Code: MIT (see `LICENSE`). The CIC-IDS2017 data and the Emerging Threats ruleset are not redistributed here and remain under their own terms.
