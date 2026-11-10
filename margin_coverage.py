"""Section 6.5: how far the chance-constraint margin can be trusted (held-out vs selected configurations)."""
import os, json, io, contextlib, numpy as np
from scipy import stats
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(HERE, "..", "results")
with contextlib.redirect_stdout(io.StringIO()):
    import costfit as CF
pC = np.load(os.path.join(HERE, "costC.npy")) if os.path.exists(os.path.join(HERE, "costC.npy")) else np.load("costC.npy")
CAPS = CF.CAPS
res = CF.yte - CF.predC(pC, CF.Lte); M = res.mean() + 1.645 * res.std(ddof=1)
print(f"held-out: mean {res.mean():.2f} s, sd {res.std(ddof=1):.2f} s, skew {stats.skew(res):.2f}, Shapiro p {stats.shapiro(res).pvalue:.2f}, exceeding margin {np.mean(res > M):.0%}")
def lv(js): d = {k: 1.0 for k in CAPS}; d.update({k: float(v) for k, v in json.loads(js).items()}); return [d[k] for k in CAPS]
rows = []
for fn, refkey in [("verify3.txt", "reference"), ("verify2.txt", "ref")]:
    L = [l.strip().split("|") for l in open(os.path.join(RES, fn)) if not l.startswith("#")]
    ref = np.mean([float(r[3]) for r in L if r[1] == refkey])
    rows += [(lv(r[6]), float(r[3]) * 112.6 / ref) for r in L if r[1] != refkey]
Lm = np.array([r[0] for r in rows]); y = np.array([r[1] for r in rows]); e = y - CF.predC(pC, Lm)
print(f"selected (phases 5b and 6, {len(e)} measurements): mean {e.mean():.2f} s, sd {e.std(ddof=1):.2f} s, within margin {np.mean(e <= M):.0%}")

# duplicates (configurations measured in both phases) and a bootstrap over configurations
from collections import defaultdict
keys = [json.dumps(list(l)) for l in Lm]; g = defaultdict(list)
for k, ee in zip(keys, e): g[k].append(ee)
dk = list(g); ed = np.array([np.mean(g[k]) for k in dk])
print(f"distinct configurations {len(dk)}: within margin {np.mean(ed <= M):.0%}")
rng = np.random.default_rng(1)
cov = [np.mean(np.concatenate([g[k] for k in rng.choice(dk, len(dk))]) <= M) for _ in range(4000)]
print(f"bootstrap over configurations, 95% interval: {np.percentile(cov, 2.5):.0%}-{np.percentile(cov, 97.5):.0%}")
