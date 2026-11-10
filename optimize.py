"""Protocol section 8 on the fitted models: exact optimum by full enumeration (1.5 M configurations),
baseline methods, and gradual erosion. Prints the configurations to verify in Suricata."""
import os as _os
DATA = _os.environ.get("CASCADE_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results"))
FIGS = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "figures")

import itertools, json, numpy as np
import fit as F, pc_fast as PC, costfit as CF

CAPS = F.CAPS
GRID = {"K1": [0, .2, .4, .6, .8, 1], "K2": [0, 1], "K3": [0, 1], "K4": [0, 1], "K5": [0, 1]}
for k in ["K6", "K7", "K8", "K9", "K10", "K11"]:
    GRID[k] = [0, .25, .5, .75, 1]
ALL = np.array(list(itertools.product(*[GRID[k] for k in CAPS])), dtype=float)
FULL_COST = 112.6                      # median of the 15 reference runs

# ---- fitted models ----
res, pk, p_cur, pred_cur = F.fit("curves", lambda: F.model_cascade(True), seeds=5)
resA, pkA, p_add, pred_add = F.fit("additive", F.model_additive, seeds=1)
p_pc = np.load("pc_params.npy"); pC = np.load("costC.npy"); pA = np.load("costA.npy")

def P_cur(L):
    cur = F.curves_from(pk, p_cur)
    X = PC.X_of(L, cur); E = PC.prop(X, pk.get(p_cur, "d"))
    return pk.get(p_cur, "b0")[0] + E @ pk.get(p_cur, "w")
def P_pc(L):
    return PC.pred(p_pc, L)[1]
def P_add(L):
    P = np.full(len(L), pkA.get(p_add, "full")[0])
    for j, k in enumerate(CAPS):
        Lk = pkA.get(p_add, "L_" + k)
        P -= np.where(L[:, j] == 0, Lk[0], 0.0)
        for li, lv in enumerate(F.LEV.get(k, [])):
            P -= np.where(L[:, j] == lv, Lk[1 + li], 0.0)
    return np.clip(P, 0, 1)
C_dep = lambda L: CF.predC(pC, np.asarray(L, dtype=float))
C_add = lambda L: CF.predA(pA, np.asarray(L, dtype=float))

def chunks(fn):
    return np.concatenate([fn(ALL[i:i + 200000]) for i in range(0, len(ALL), 200000)])
Pc, Pp, Pa = chunks(P_cur), chunks(P_pc), chunks(P_add)
Cd, Ca = chunks(C_dep), chunks(C_add)
print(f"enumerated {len(ALL)} configurations; predicted cost range {Cd.min():.1f}-{Cd.max():.1f} s "
      f"({Cd.min()/FULL_COST:.0%}-{Cd.max()/FULL_COST:.0%} of full)")

def best(P, C, B, tiebreak=None):
    ok = C <= B
    if not ok.any(): return None
    cand = np.where(ok)[0]
    top = P[cand].max()
    near = cand[P[cand] >= top - 1e-9]
    return near[np.argmin(C[near])]               # among equal protection, the cheapest

def lv(row): return {k: float(v) for k, v in zip(CAPS, ALL[row]) if v != 1}

def idx_of(levels):
    target = np.array([levels.get(k, 1.0) for k in CAPS])
    return int(np.where((ALL == target).all(1))[0][0])

STEPS = {k: [float(v) for v in GRID[k][::-1]] for k in CAPS}          # from full down to 0
def greedy(order_fn, B):
    """Generic step-down heuristic: lower one capability one level at a time until predicted cost <= B."""
    cur = {k: 1.0 for k in CAPS}
    while C_dep(np.array([[cur[k] for k in CAPS]]))[0] > B:
        k = order_fn(cur)
        if k is None: return None
        cur[k] = STEPS[k][STEPS[k].index(cur[k]) + 1]
    return idx_of({k: v for k, v in cur.items() if v != 1})

def most_expensive_first(cur):
    base = C_dep(np.array([[cur[k] for k in CAPS]]))[0]; bestk, bests = None, -1
    for k in CAPS:
        if cur[k] == 0: continue
        nxt = dict(cur); nxt[k] = STEPS[k][STEPS[k].index(cur[k]) + 1]
        s = base - C_dep(np.array([[nxt[c] for c in CAPS]]))[0]
        if s > bests: bestk, bests = k, s
    return bestk

RULE_ORDER = ["K9", "K11", "K8", "K6", "K10", "K7"]     # by measured single-factor saving
PARSER_ORDER = ["K1", "K2", "K3", "K4", "K5"]
def rules_first(cur):
    for k in RULE_ORDER + PARSER_ORDER:
        if cur[k] > 0: return k
    return None

def v2_heuristic(B):
    """CASCADE V2 idea on the fitted models: greedy by lost protection per saved cost, then 1-swap repair."""
    cur = np.ones(len(CAPS))
    def P1(x): return P_cur(x[None])[0]
    def C1(x): return C_dep(x[None])[0]
    while C1(cur) > B:
        bestj, bestr = None, None
        for j, k in enumerate(CAPS):
            if cur[j] == 0: continue
            nx = cur.copy(); nx[j] = STEPS[k][STEPS[k].index(cur[j]) + 1]
            dc = C1(cur) - C1(nx); dp = P1(cur) - P1(nx)
            r = dp / max(dc, 1e-6)
            if bestr is None or r < bestr: bestj, bestr, bestx = j, r, nx
        if bestj is None: return None
        cur = bestx
    improved = True
    while improved:
        improved = False
        for j, k in enumerate(CAPS):
            for i, k2 in enumerate(CAPS):
                if i == j or cur[j] == 1 or cur[i] == 0: continue
                nx = cur.copy(); nx[j] = STEPS[k][STEPS[k].index(cur[j]) - 1]
                nx[i] = STEPS[k2][STEPS[k2].index(cur[i]) + 1]
                if C1(nx) <= B and P1(nx) > P1(cur) + 1e-9:
                    cur, improved = nx, True
    return idx_of({k: v for k, v in zip(CAPS, cur) if v != 1})

BUDGETS = [1.0, .9, .8, .7, .6, .5, .4]
plan = {}
print(f"\n{'budget':>6} {'method':28s} {'pred P':>7} {'pred cost':>9}  levels")
for b in BUDGETS:
    B = b * FULL_COST
    methods = {
        "dependency-aware optimum": best(Pc, Cd, B),
        "dep-aware optimum (per-class)": best(Pp, Cd, B),
        "dependency-unaware optimum": best(Pa, Ca, B),
        "rules first": greedy(rules_first, B),
        "most expensive first": greedy(most_expensive_first, B),
        "CASCADE V2 heuristic": v2_heuristic(B),
    }
    for m, r in methods.items():
        if r is None:
            print(f"{b:6.0%} {m:28s} infeasible (minimum predicted cost {Cd.min():.1f} s)"); continue
        plan.setdefault(b, {})[m] = lv(r)
        print(f"{b:6.0%} {m:28s} {Pc[r]:7.3f} {Cd[r]:9.1f}  {lv(r)}")

# gradual erosion: re-solve vs never re-enable
print("\nGradual erosion 100% -> 60% in 5% steps (dependency-aware model)")
prev = None; mono_prev = np.ones(len(CAPS)); flips = 0; mono_total = 0.0; resolve_total = 0.0
for b in np.arange(1.0, 0.599, -0.05):
    B = b * FULL_COST
    r = best(Pc, Cd, B)
    ok = (Cd <= B) & (ALL <= mono_prev + 1e-12).all(1)
    rm = np.where(ok)[0][np.argmax(Pc[ok])]
    if prev is not None:
        flips += int(((ALL[r] > ALL[prev]) ).sum())
    print(f"  {b:4.0%}  re-solve P {Pc[r]:.3f}   monotone P {Pc[rm]:.3f}")
    resolve_total += Pc[r]; mono_total += Pc[rm]; prev = r; mono_prev = ALL[rm]
print(f"  capability levels raised again by re-solving: {flips}; mean P loss of monotone path {(resolve_total-mono_total)/9:.4f}")
json.dump({f"{k:.2f}": v for k, v in plan.items()}, open("verification_plan.json", "w"), indent=1)
