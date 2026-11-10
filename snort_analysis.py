"""Snort 3 replication (protocol amendment v1.4): H7-H9, model and baseline comparison."""
import os, json, itertools, warnings, numpy as np, pandas as pd
from scipy.optimize import least_squares
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
warnings.filterwarnings("ignore")
DATA = os.environ.get("CASCADE_DATA", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results"))
CAPS = [f"K{i}" for i in range(1, 12)]; IDX = {k: i for i, k in enumerate(CAPS)}
GRID = {"K1": [0, 1], "K2": [0, 1], "K3": [0, 1], "K4": [0, 1], "K5": [0, 1]}
for k in ["K6", "K7", "K8", "K9", "K10", "K11"]: GRID[k] = [0, .25, .5, .75, 1]
LEV = {k: [.25, .5, .75] for k in ["K6", "K7", "K8", "K9", "K10", "K11"]}
EDGES = [("K1", "K2"), ("K1", "K3"), ("K1", "K5"), ("K2", "K6"), ("K1", "K8"), ("K3", "K8"), ("K2", "K9"), ("K3", "K9"), ("K4", "K9")]
d = pd.read_csv(os.path.join(DATA, "snort_results.csv"))
refs = d[d.type == "reference"]; c = d[d.type == "config"].copy()
c["L"] = c.levels.apply(lambda s: [{**{k: 1.0 for k in CAPS}, **{k: float(v) for k, v in json.loads(s).items()}}[k] for k in CAPS])
tr = c[c.phase.isin([1, 2, 3])]; te = c[c.phase == 4]
Ltr, Lte = np.array(tr.L.tolist()), np.array(te.L.tolist())
ytr, yte = tr.macro_window_recall.values, te.macro_window_recall.values
print(f"Snort: {len(tr)} fitting, {len(te)} held-out configurations; reference CPU mean {refs.cpu_median.mean():.1f} s (CV {refs.cpu_median.std()/refs.cpu_median.mean():.1%})")
full = c[c.levels == "{}"].iloc[0]
print(f"full configuration: macro window recall {full.macro_window_recall:.3f}, CPU {full.cpu_median:.1f} s, startup {full.startup_median:.1f} s, memory {full.rss_median:.0f} MB, benign alerts {full.alerts_on_benign:.0f}")
# ---------- H7: interactions on week macro window recall
norm = lambda s: json.dumps({k: float(v) for k, v in json.loads(s).items()}, sort_keys=True)
mac = {norm(s): v for s, v in zip(c.levels, c.macro_window_recall)}
c["key"] = c.levels.apply(norm)
P = lambda **kw: mac[json.dumps({k: float(v) for k, v in kw.items()}, sort_keys=True)]
Pf = full.macro_window_recall
print("\nH7 interactions (pair at 0) - single losses:")
ok7 = True
for a, b in [("K1", "K2"), ("K1", "K6"), ("K2", "K6")]:
    I = P(**{a: 0, b: 0}) - P(**{a: 0}) - P(**{b: 0}) + Pf; ok7 &= I >= 0.02
    print(f"  {a}-{b}: I = {I:+.3f}  (pair {P(**{a:0,b:0}):.3f}, singles {P(**{a:0}):.3f}, {P(**{b:0}):.3f}, full {Pf:.3f})")
others = []
for a, b in itertools.combinations(CAPS, 2):
    try: I = P(**{a: 0, b: 0}) - P(**{a: 0}) - P(**{b: 0}) + Pf
    except KeyError: continue
    if abs(I) > 0.02 and (a, b) not in [("K1", "K2"), ("K1", "K6"), ("K2", "K6")]: others.append(f"{a}-{b} {I:+.3f}")
print("  other pairs with |I| > 0.02:", others or "none"); print("  H7 supported:", ok7)
print("  single-factor losses:", {k: round(Pf - P(**{k: 0}), 3) for k in CAPS})
# ---------- models
def X_of(L, cur):
    X = L.copy()
    if cur is not None:
        for k, vals in cur.items():
            j = IDX[k]
            for li, lv in enumerate(LEV[k]): X[L[:, j] == lv, j] = vals[li]
    return X
def prop(X, dd):
    E = np.empty_like(X)
    for k in CAPS:
        i = IDX[k]; v = X[:, i].copy()
        for (p, ch), dv in zip(EDGES, dd):
            if ch == k: v = v * (1 - dv * (1 - E[:, IDX[p]]))
        E[:, i] = v
    return E
def cascade(curves):
    nE = len(EDGES); nc = sum(len(v) for v in LEV.values()) if curves else 0
    def unpack(p):
        b0, w, dd = p[0], p[1:12], p[12:12 + nE]; cur = None
        if curves:
            cur, o = {}, 12 + nE
            for k in LEV: cur[k] = p[o:o + 3]; o += 3
        return b0, w, dd, cur
    def pred(p, L):
        b0, w, dd, cur = unpack(p); return b0 + prop(X_of(L, cur), dd) @ w
    n = 12 + nE + nc; lo = np.zeros(n); hi = np.ones(n)
    best = None; rng = np.random.default_rng(1)
    for s in range(6):
        x0 = np.r_[0.3, np.full(11, .03), np.full(n - 12, .5)] if s == 0 else lo + rng.random(n) * (hi - lo)
        sol = least_squares(lambda p: np.r_[pred(p, Ltr) - ytr, 1e-4 * p], x0, bounds=(lo, hi), max_nfev=4000)
        if best is None or sol.cost < best.cost: best = sol
    return best.x, pred, unpack
def onehot(L):
    return np.column_stack([(L[:, j] == lv).astype(float) for j, k in enumerate(CAPS) for lv in GRID[k][:-1]])
rng = np.random.default_rng(7)
def ci(e): b = [np.mean(np.abs(rng.choice(e, len(e)))) for _ in range(4000)]; return np.percentile(b, [2.5, 97.5])
res = {}
print("\nH8 held-out mean absolute error (25 configurations):")
add = LinearRegression().fit(onehot(Ltr), ytr); res["additive"] = add.predict(onehot(Lte)) - yte
for nm, cur in [("CASCADE pre-registered form", False), ("CASCADE with level curves", True)]:
    p, pred, unpack = cascade(cur); res[nm] = pred(p, Lte) - yte
    if cur: pc, upc = p, unpack
    else: pp, upp = p, unpack
res["random forest"] = RandomForestRegressor(500, random_state=0).fit(Ltr, ytr).predict(Lte) - yte
res["gradient boosting"] = GradientBoostingRegressor(n_estimators=400, max_depth=3, learning_rate=.05, random_state=0).fit(Ltr, ytr).predict(Lte) - yte
for nm, e in res.items():
    lo_, hi_ = ci(e); print(f"  {nm:30s} {np.mean(abs(e)):.4f} [{lo_:.4f}, {hi_:.4f}]  max {np.max(abs(e)):.3f}")
dlt = np.abs(res["additive"]) - np.abs(res["CASCADE with level curves"]); bb = [dlt[rng.integers(0, 25, 25)].mean() for _ in range(4000)]
print(f"  paired additive - CASCADE(curves): {dlt.mean():+.4f} [{np.percentile(bb,2.5):+.4f}, {np.percentile(bb,97.5):+.4f}]")
dg = np.abs(res["gradient boosting"]) - np.abs(res["CASCADE with level curves"]); bb = [dg[rng.integers(0, 25, 25)].mean() for _ in range(4000)]
print(f"  paired gradient boosting - CASCADE(curves): {dg.mean():+.4f} [{np.percentile(bb,2.5):+.4f}, {np.percentile(bb,97.5):+.4f}]")
m8 = np.mean(abs(res["CASCADE with level curves"])); print("  H8 supported:", m8 <= 0.05 and m8 < np.mean(abs(res["additive"])))
print("\nH9 fitted dependency strengths:")
for nm, (p, up) in [("level curves (H8 model)", (pc, upc)), ("pre-registered form", (pp, upp))]:
    b0, w, dd, cur = up(p)
    print(f"  {nm}: " + ", ".join(f"{a}->{b} {v:.2f}" for (a, b), v in zip(EDGES, dd) if v > 0.05 or (a, b) in [("K1", "K2"), ("K2", "K6")]),
          f"| b0 {b0:.3f} | weights", {k: round(v, 3) for k, v in zip(CAPS, w) if v > 0.003})
b0, w, dd, cur = upc(pc); print("  H9 supported:", dd[0] >= .5 and dd[3] >= .5)
# ---------- cost (exploratory)
ctr, cte = tr.cpu_median.values, te.cpu_median.values
print("\nCost (exploratory) held-out MAE:")
ca = LinearRegression().fit(onehot(Ltr), ctr); print(f"  additive (one-hot)     {np.mean(abs(ca.predict(onehot(Lte)) - cte)):.1f} s")
g = GradientBoostingRegressor(n_estimators=400, max_depth=3, learning_rate=.05, random_state=0).fit(Ltr, ctr); print(f"  gradient boosting      {np.mean(abs(g.predict(Lte) - cte)):.1f} s")
EDC = [("K1", k) for k in CAPS[1:]] + [("K2", "K6"), ("K2", "K9"), ("K2", "K11"), ("K3", "K8"), ("K3", "K9")]
def cpred(p, L):
    C0, cc = p[0], p[1:12]; cur, o = {}, 12
    for k in LEV: cur[k] = p[o:o + 3]; o += 3
    G = X_of(L, cur); U = np.ones_like(G)
    for (a, b), dv in zip(EDC, p[o:]): U[:, IDX[b]] *= 1 - dv * (1 - G[:, IDX[a]])
    return C0 + (G * U) @ cc
n = 12 + 18 + len(EDC); lo = np.zeros(n); hi = np.r_[300, np.full(11, 150), np.ones(n - 12)]
best = None; rr = np.random.default_rng(0)
for s in range(8):
    x0 = np.r_[120, np.full(11, 5), np.full(n - 12, .5)] if s == 0 else lo + rr.random(n) * (hi - lo)
    sol = least_squares(lambda p: np.r_[cpred(p, Ltr) - ctr, 1e-3 * p[12:]], x0, bounds=(lo, hi), max_nfev=5000)
    if best is None or sol.cost < best.cost: best = sol
e = cpred(best.x, Lte) - cte
print(f"  dependency-aware       {np.mean(abs(e)):.1f} s ({np.mean(abs(e)/cte):.1%}); bias {e.mean():+.1f} s")
print("  cost of each capability switched off alone:", {k: round(full.cpu_median - mac_c, 1) for k, mac_c in
      [(k, c[c.key == json.dumps({k: 0.0})].cpu_median.iloc[0]) for k in CAPS if (c.key == json.dumps({k: 0.0})).any()]})
