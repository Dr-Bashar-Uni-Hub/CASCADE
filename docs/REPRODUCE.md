# Reproducing the manuscript's tables and figures

| Item | Script | Data |
|---|---|---|
| Fig. 1 (architecture), Fig. 2 (workflow) | `analysis/figs_v1.py` | none |
| Fig. 3 (per-class detection, both engines) | `analysis/figs_v1.py` | `results/det.txt`, `results/snort_results.csv` |
| Table 5 (single-factor effects) | `analysis/fit.py`, `analysis/snort_analysis.py` | `results/det.txt`, `results/cost.txt`, `results/snort_results.csv` |
| Fig. 4 (dependencies) | `analysis/figs_v1.py` (values from `fit.py`, `snort_analysis.py`) | as above |
| Table 6, Fig. 5 (model comparison) | `analysis/compare.py`, `analysis/snort_analysis.py`, `analysis/figs_v1.py` | `results/det.txt`, `results/verify*.txt`, `results/snort_results.csv` |
| Section 6.4 (cost models) | `analysis/costfit.py`, `analysis/compare.py`, `analysis/snort_analysis.py` | `results/cost.txt`, `results/verify2.txt`, `results/snort_results.csv` |
| Table 7 (phase 5 verification) | `analysis/audit.py` | `results/verify.txt` |
| Flat-optimum audit (Section 6.5) | `analysis/audit2.py` | `results/det.txt`, `results/cost.txt` |
| Table 8, Fig. 6 (phase 6) | `analysis/phase6.py`, `analysis/figs_v1.py` | `results/verify3.txt`, `schedules/frozen_models_v1_3.json` |
| Section 6.6 (window length, re-measurement, margin) | `analysis/winfit.py`, `analysis/phase5b.py` | `results/window_sensitivity.csv`, `results/verify2.txt` |
| Table 4 (hypotheses) | all of the above | protocol |
