# Result summaries

Compact per-configuration summaries used by `analysis/`. Full per-run records are available from the author on reasonable request.

- `det.txt`: detection of the 150 main-study configurations. Fields: id | phase | rule seed (19 = 20261019, 119 = 20261119, 219 = 20261219) | levels lowered (others at 1) | window counts that differ from the full configuration | macro window recall as reported by the harness. Baseline window counts and the classes that never change are listed in the file header; `load.py` reconstructs per-class window recall and checks it against the reported value.
- `cost.txt`: median processing CPU (s, Thursday capture), median startup CPU (s) and median peak memory (MB) for the 150 configurations (C) and 15 full-configuration reference runs (R).
- `verify.txt`: the 25 verification configurations: id | levels | median processing CPU (s) | macro window recall | cost session (1 or 2).

Exact numbers in the paper are produced from these files by the scripts in `analysis/`.
- `window_sensitivity.csv`: macro and per-class window recall of all 175 configurations for 30, 60, 120 and 300 s windows (from `harness/window_sensitivity.py`; `analysis/winfit.py` refits the models per window, Table 8).
- `verify2.txt`: exploratory phase 5b: four safety-margin configurations (new) and a cost re-measurement of the 25 phase 5 configurations, with three full-configuration reference runs (ref).
- `stage2_3/`: outputs of `analysis/compare.py` (predictive baselines) and `analysis/audit2.py` (optimisation audit), computed from the files above without new measurements.
- `verify3.txt`: phase 6 (pre-registered, amendment v1.3): uncertainty-aware selection rules; `analysis/phase6.py` evaluates H4–H6.
- `snort_results.csv`: Snort 3 replication (amendment v1.4), 110 configurations and 11 reference runs, with the 16 configurations affected by the Lua bug replaced by their re-run (re-run costs scaled by 1.050 to the main reference mean); `snort_results_v1_4_before_fix.csv` keeps the original values, `snort_rerun_results.csv` the re-run; `snort_analysis_output.txt` is the output of `analysis/snort_analysis.py` (H7-H9).
- `verify4.txt`: phase 7 (pre-registered, amendment v1.5): the tie and chance rules applied with the additive model and gradient boosting, plus the structural model's phase-6 choices re-measured for cost (H10-H12).
