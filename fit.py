"""Protocol section 7: fit protection models on phases 1-3, validate on held-out phase 4."""
import os as _os
DATA = _os.environ.get("CASCADE_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results"))
FIGS = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "figures")

import json, numpy as np
from scipy.optimize import least_squares
from load import load, CAPS, CLS, CONST

R = load()
TR = [r for r in R if r["phase"] in (1, 2, 3)]
TE = [r for r in R if r["phase"] == 4]
EDGES = [("K1", "K2"), ("K1", "K3"), ("K1", "K5"), ("K2", "K6"), ("K1", "K8"),
         ("K3", "K8"), ("K2", "K9"), ("K3", "K9"), ("K4", "K9")]
LEV = {"K1": [0.2, 0.4, 0.6, 0.8]}
for k in ["K6", "K7", "K8", "K9", "K10", "K11"]:
    LEV[k] = [0.25, 0.5, 0.75]
IDX = {k: i for i, k in enumerate(CAPS)}
TOPO = CAPS  # edges all go from lower to higher index


class Packer:
    def __init__(self): self.spec, self.n = [], 0
    def add(self, name, size, lo, hi, init):
        self.spec.append((name, self.n, size, lo, hi, init)); self.n += size
    def bounds(self):
        lo = np.concatenate([np.full(s, l) for _, _, s, l, _, _ in self.spec])
        hi = np.concatenate([np.full(s, h) for _, _, s, _, h, _ in self.spec])
        return lo, hi
    def x0(self): return np.concatenate([np.full(s, i) for _, _, s, _, _, i in self.spec])
    def get(self, p, name):
        for n, o, s, _, _, _ in self.spec:
            if n == name: return p[o:o + s]


def x_of(r, curves=None):
    """Operating-level input per capability: the level itself, or a fitted level curve."""
    out = np.empty(len(CAPS))
    for i, k in enumerate(CAPS):
        lv = r["levels"][k]
        if curves is None or k not in LEV or lv in (0.0, 1.0):
            out[i] = lv
        else:
            out[i] = curves[k][LEV[k].index(lv)]
    return out


def propagate(x, d):
    e = x.copy()
    for (p, c), dv in zip(EDGES, d):
        pass
    e = np.empty_like(x)
    for k in TOPO:
        i = IDX[k]
        v = x[i]
        for (p, c), dv in zip(EDGES, d):
            if c == k:
                v *= 1 - dv * (1 - e[IDX[p]])
        e[i] = v
    return e


def curves_from(pk, p):
    return {k: pk.get(p, "f_" + k) for k in LEV}


# ---------- model definitions ----------
def model_additive():
    pk = Packer(); pk.add("full", 1, 0, 1, 0.57)
    for k in CAPS:
        n = len(LEV.get(k, [])) + 1          # level 0 plus intermediate levels
        pk.add("L_" + k, n, -0.2, 1, 0.0)
    def pred(p, r):
        P = pk.get(p, "full")[0]
        for k in CAPS:
            lv = r["levels"][k]
            if lv == 1.0: continue
            L = pk.get(p, "L_" + k)
            P -= L[0] if lv == 0.0 else L[1 + LEV[k].index(lv)]
        return min(max(P, 0.0), 1.0)
    return pk, pred, False


def model_cascade(curves):
    pk = Packer(); pk.add("b0", 1, 0, 1, 0.3); pk.add("w", len(CAPS), 0, 1, 0.03)
    pk.add("d", len(EDGES), 0, 1, 0.5)
    if curves:
        for k in LEV: pk.add("f_" + k, len(LEV[k]), 0, 1, 0.5)
    def pred(p, r):
        x = x_of(r, curves_from(pk, p) if curves else None)
        e = propagate(x, pk.get(p, "d"))
        return pk.get(p, "b0")[0] + pk.get(p, "w") @ e
    return pk, pred, False


def model_perclass():
    pk = Packer(); pk.add("d", len(EDGES), 0, 1, 0.5)
    for k in LEV: pk.add("f_" + k, len(LEV[k]), 0, 1, 0.5)
    for c in CLS:
        pk.add("m_" + c, 1, 0, 1, 0.5); pk.add("beta_" + c, 1, 0, 1, 0.2)
        pk.add("q_" + c, len(CAPS), 0, 1, 0.1)
    def pred_cls(p, r):
        e = propagate(x_of(r, curves_from(pk, p)), pk.get(p, "d"))
        out = {}
        for c in CLS:
            m, b, q = pk.get(p, "m_" + c)[0], pk.get(p, "beta_" + c)[0], pk.get(p, "q_" + c)
            out[c] = m * (1 - (1 - b) * np.prod(1 - q * e))
        return out
    def pred(p, r):
        return (sum(pred_cls(p, r).values()) + CONST) / 15
    pred.cls = pred_cls
    return pk, pred, True


def fit(name, make, seeds=5):
    pk, pred, per_class = make()
    lo, hi = pk.bounds()
    def resid(p):
        if per_class:
            res = []
            for r in TR:
                pc = pred.cls(p, r)
                res += [(pc[c] - r["rec"][c]) / 15 for c in CLS]
            return np.array(res + list(1e-3 * p))     # tiny ridge keeps unused parameters at rest
        return np.array([pred(p, r) - r["macro"] for r in TR] + list(1e-4 * p))
    best = None
    rng = np.random.default_rng(1)
    for s in range(seeds):
        x0 = pk.x0() if s == 0 else lo + rng.random(pk.n) * (hi - lo)
        sol = least_squares(resid, x0, bounds=(lo, hi), max_nfev=3000)
        if best is None or sol.cost < best.cost: best = sol
    p = best.x
    tr_err = np.array([pred(p, r) - r["macro"] for r in TR])
    te_err = np.array([pred(p, r) - r["macro"] for r in TE])
    rng = np.random.default_rng(7)
    boot = [np.mean(np.abs(rng.choice(te_err, len(te_err)))) for _ in range(5000)]
    res = dict(model=name, params=pk.n, train_rmse=float(np.sqrt(np.mean(tr_err ** 2))),
               test_mae=float(np.mean(np.abs(te_err))), test_mae_ci=[float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
               test_max=float(np.max(np.abs(te_err))))
    return res, pk, p, pred


if __name__ == "__main__":
    out = {}
    for name, make in [("additive (no dependencies)", model_additive),
                       ("CASCADE, protocol form", lambda: model_cascade(False)),
                       ("CASCADE + level curves", lambda: model_cascade(True)),
                       ("per-class noisy-OR on CASCADE", model_perclass)]:
        res, pk, p, pred = fit(name, make)
        out[name] = (res, pk, p, pred)
        print(f"{name:32s} params {res['params']:3d}  train RMSE {res['train_rmse']:.4f}  "
              f"held-out MAE {res['test_mae']:.4f} [{res['test_mae_ci'][0]:.4f}, {res['test_mae_ci'][1]:.4f}]  max {res['test_max']:.4f}")
    import pickle; pickle.dump({k: (v[0], v[2]) for k, v in out.items()}, open("fits.pkl", "wb"))
