# CASCADE

**Component dependencies in signature-based intrusion detection: measurement, modelling and robust configuration under CPU budgets, in Suricata and Snort.**

This repository contains everything behind the study: the measurement harness for two engines, the pre-registered protocol with all amendments and deviations, the frozen schedules and models, the per-configuration results, and the analysis and figure scripts.

> Manuscript under review. Please cite the paper once published (see `CITATION.cff`).

## Main findings

| Finding | Evidence | Status |
|---|---|---|
| Suricata 7 and Snort 3 share the dependency chain stream reassembly → HTTP inspection → web-attack rules | Fitted strengths 0.92-0.96; interactions +0.085 to +0.14 (H1, H7, H9) | Supported, pre-registered |
| A structural dependency model has the lowest observed prediction error; clearly ahead of additive and regression baselines, narrowly ahead of gradient boosting (not statistically established on Snort) | Held-out MAE 0.011 (Suricata), 0.010 (Snort); 0.003 on 40 optimised configurations verified in Suricata (H2, H8) | Supported, pre-registered |
| Model-based optima are flat; cheaper near-optimal configurations exist within the model's error | Audit of the fitted models; phase 5 verification | Established |
| Robust selection (cheapest within error; chance constraint) | Tie rule saved 11.3 / 5.6 CPU points at 90% / 80% with <= 0.006 recall loss (H5, H6); chance constraint missed the 70% budget by < 1 point (H4) | Partly supported, pre-registered |
| Dependency awareness gives more detection than a dependency-unaware optimiser at tight budgets | H3 | Not supported |

## Repository layout

| Folder | Contents |
|---|---|
| `protocol/` | Pre-registered measurement protocol (v1.4) with all amendments, deviations, results and hashes |
| `harness/` | Suricata measurement harness, batch runner (`main_batch.py --engine suricata|snort`), label matching, week scoring, window re-analysis |
| `snort/` | Snort 3 harness port, levels, schedules and pilot scripts |
| `schedules/` | Frozen Suricata schedules (main, verification, phases 5b and 6) and the frozen models of phase 6 |
| `analysis/` | Model fitting, baselines, optimisation, audits, phase evaluations, Snort analysis, figures |
| `results/` | Per-configuration results for both engines (see `results/README.md`) |
| `figures/` | Manuscript figures (PNG 300 dpi and PDF) |
| `docs/` | Data sources, hashes, environment, and how each table and figure is reproduced |
| `legacy_synthetic/` | Earlier synthetic-graph notebooks; not used in the results |

The full per-run records (about 1 GB per engine) and the ruleset snapshots are available from the author on reasonable request.

## Reproducing the analysis (no IDS needed)

    pip install -r requirements.txt
    cd analysis
    python3 costfit.py        # Suricata cost models (writes costA.npy, costC.npy)
    python3 pc_fast.py        # per-class protection model
    python3 fit.py            # Suricata protection models
    python3 compare.py        # Suricata: structural model vs baselines
    python3 audit2.py         # optimisation audit (flat optimum)
    python3 phase6.py         # pre-registered robust selection (H4-H6)
    python3 snort_analysis.py # Snort replication (H7-H9) and baselines
    python3 figs_v1.py        # manuscript figures

See `docs/REPRODUCE.md` for the mapping from each table and figure to its script and data.

## Reproducing the measurements

Requires Ubuntu 24.04, Suricata 7.0.3 and/or Snort 3.12.4.0 (DAQ 3.0.28, Hyperscan), Python 3.12 with pandas, the CIC-IDS2017 captures and corrected labels, and the ruleset snapshots (see `docs/DATA.md`). See `harness/README.md` and the protocol for the procedure, measurement-control rules and seeds.

## License

Code: MIT (see `LICENSE`). CIC-IDS2017 and the Emerging Threats rulesets are not redistributed here and remain under their own terms.
