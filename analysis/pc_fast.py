import os as _os
DATA = _os.environ.get("CASCADE_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results"))
FIGS = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "figures")

import numpy as np, time
from scipy.optimize import least_squares
from fit import TR, TE, EDGES, LEV, IDX, CAPS, CLS, CONST
# level index matrix: for curve lookup
def mats(rows):
    L = np.array([[r["levels"][k] for k in CAPS] for r in rows])
    Y = np.array([[r["rec"][c] for c in CLS] for r in rows])
    M = np.array([r["macro"] for r in rows])
    return L, Y, M
Ltr, Ytr, Mtr = mats(TR); Lte, Yte, Mte = mats(TE)
curve_caps = list(LEV)
nE, nC, nK = len(EDGES), len(CLS), len(CAPS)
ncurve = sum(len(LEV[k]) for k in curve_caps)
def unpack(p):
    o = 0; d = p[o:o+nE]; o += nE
    cur = {}
    for k in curve_caps:
        cur[k] = p[o:o+len(LEV[k])]; o += len(LEV[k])
    m = p[o:o+nC]; o += nC; b = p[o:o+nC]; o += nC
    q = p[o:o+nC*nK].reshape(nC, nK)
    return d, cur, m, b, q
def X_of(L, cur):
    X = L.copy()
    for k in curve_caps:
        j = IDX[k]
        for li, lv in enumerate(LEV[k]):
            X[L[:, j] == lv, j] = cur[k][li]
    return X
def prop(X, d):
    E = np.empty_like(X)
    for k in CAPS:
        i = IDX[k]; v = X[:, i].copy()
        for (pa, c), dv in zip(EDGES, d):
            if c == k: v *= 1 - dv * (1 - E[:, IDX[pa]])
        E[:, i] = v
    return E
def pred(p, L):
    d, cur, m, b, q = unpack(p)
    E = prop(X_of(L, cur), d)                       # n x K
    prodterm = np.prod(1 - E[:, None, :] * q[None, :, :], axis=2)   # n x C
    Yh = m[None, :] * (1 - (1 - b[None, :]) * prodterm)
    return Yh, (Yh.sum(1) + CONST) / 15
n = nE + ncurve + 2 * nC + nC * nK
lo, hi = np.zeros(n), np.ones(n)
def resid(p):
    Yh, _ = pred(p, Ltr)
    return np.concatenate([((Yh - Ytr) / 15).ravel(), 1e-3 * p])
if __name__ == '__main__':
    best = None; rng = np.random.default_rng(3); t = time.time()
    for s in range(6):
        x0 = np.full(n, 0.5) if s == 0 else rng.random(n)
        sol = least_squares(resid, x0, bounds=(lo, hi), max_nfev=4000)
        if best is None or sol.cost < best.cost: best = sol
    p = best.x
    _, Mh_tr = pred(p, Ltr); _, Mh_te = pred(p, Lte)
    te = Mh_te - Mte; boot = [np.mean(np.abs(rng.choice(te, len(te)))) for _ in range(5000)]
    print(f"per-class noisy-OR on CASCADE  params {n}  train RMSE {np.sqrt(np.mean((Mh_tr-Mtr)**2)):.4f}  "
          f"held-out MAE {np.mean(np.abs(te)):.4f} [{np.percentile(boot,2.5):.4f}, {np.percentile(boot,97.5):.4f}]  max {np.max(np.abs(te)):.4f}  ({time.time()-t:.0f}s)")
    d, cur, m, b, q = unpack(p)
    print(" d", {f"{a}->{c}": round(float(v),2) for (a,c),v in zip(EDGES,d)})
    for ci, c in enumerate(CLS):
        print(f"  {c:4s} max {m[ci]:.2f} base {b[ci]:.2f} q", {k: round(float(v),2) for k,v in zip(CAPS,q[ci]) if v>0.05})
    np.save("pc_params.npy", p)
