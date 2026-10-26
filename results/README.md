# Result summaries

Compact per-configuration summaries used by `analysis/`. Full per-run records are in the Zenodo archive.

- `det.txt`: detection of the 150 main-study configurations. Fields: id | phase | rule seed (19 = 20261019, 119 = 20261119, 219 = 20261219) | levels lowered (others at 1) | window counts that differ from the full configuration | macro window recall as reported by the harness. Baseline window counts and the classes that never change are listed in the file header; `load.py` reconstructs per-class window recall and checks it against the reported value.
- `cost.txt`: median processing CPU (s, Thursday capture), median startup CPU (s) and median peak memory (MB) for the 150 configurations (C) and 15 full-configuration reference runs (R).
- `verify.txt`: the 25 verification configurations: id | levels | median processing CPU (s) | macro window recall | cost session (1 or 2).

Exact numbers in the paper are produced from these files by the scripts in `analysis/`.
- `window_sensitivity.csv`: macro and per-class window recall of all 175 configurations for 30, 60, 120 and 300 s windows (from `harness/window_sensitivity.py`; `analysis/winfit.py` refits the models per window, Table 8).
