import os as _os
DATA = _os.environ.get("CASCADE_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results"))
FIGS = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "figures")

import json, numpy as np
from scipy.optimize import least_squares
CAPS=[f"K{i}" for i in range(1,12)]; IDX={k:i for i,k in enumerate(CAPS)}
LEV={"K1":[0.2,0.4,0.6,0.8]}; [LEV.__setitem__(k,[0.25,0.5,0.75]) for k in ["K6","K7","K8","K9","K10","K11"]]
def load(path=None):
    path = path or _os.path.join(DATA, "cost.txt")
    rows=[]
    for line in open(path):
        i,lv,c,st,rss=line.strip().split("|")
        L={k:1.0 for k in CAPS}; L.update(json.loads(lv))
        rows.append(dict(id=i,L=np.array([L[k] for k in CAPS]),cost=float(c),startup=float(st),rss=float(rss)))
    return rows
R=load()
refs=[r for r in R if r["id"].startswith("R")]
cfg=[r for r in R if r["id"].startswith("C")]
num=lambda r:int(r["id"][1:])
TR=[r for r in cfg if num(r)<=110]; TE=[r for r in cfg if num(r)>110]
Ltr=np.array([r["L"] for r in TR]); ytr=np.array([r["cost"] for r in TR])
Lte=np.array([r["L"] for r in TE]); yte=np.array([r["cost"] for r in TE])
refc=np.array([r["cost"] for r in refs])
print(f"reference runs: median {np.median(refc):.1f}, CV {refc.std(ddof=1)/refc.mean():.3f}")
def G(L,cur):
    X=L.copy()
    for k in LEV:
        j=IDX[k]
        for li,lv in enumerate(LEV[k]): X[L[:,j]==lv,j]=cur[k][li]
    return X
ncur=sum(len(v) for v in LEV.values())
def unpack_cur(p,o):
    cur={}
    for k in LEV: cur[k]=p[o:o+len(LEV[k])]; o+=len(LEV[k])
    return cur,o
# A: additive with level curves: C = C0 + sum c_i g_i
def predA(p,L):
    C0=p[0]; c=p[1:12]; cur,_=unpack_cur(p,12)
    return C0+G(L,cur)@c
nA=12+ncur
# C: cascade-structured cost
EDG=[("K1",k) for k in CAPS[1:]]+[("K2","K6"),("K2","K9"),("K2","K11"),("K3","K8"),("K3","K9")]
def predC(p,L):
    C0=p[0]; c=p[1:12]; cur,o=unpack_cur(p,12); dl=p[o:o+len(EDG)]
    Gm=G(L,cur); U=np.ones_like(Gm)
    for (a,b),dv in zip(EDG,dl): U[:,IDX[b]]*=1-dv*(1-Gm[:,IDX[a]])
    return C0+(Gm*U)@c
nC=12+ncur+len(EDG)
def fit(pred,n,name,lo=None,hi=None):
    lo=np.zeros(n) if lo is None else lo; hi=np.r_[150,np.full(11,60),np.ones(n-12)] if hi is None else hi
    best=None; rng=np.random.default_rng(0)
    for s in range(8):
        x0=np.r_[60,np.full(11,3),np.full(n-12,0.5)] if s==0 else lo+rng.random(n)*(hi-lo)
        sol=least_squares(lambda p:np.r_[pred(p,Ltr)-ytr,1e-3*p[12:]],x0,bounds=(lo,hi),max_nfev=5000)
        if best is None or sol.cost<best.cost: best=sol
    p=best.x; e=pred(p,Lte)-yte; et=pred(p,Ltr)-ytr
    rng=np.random.default_rng(7); boot=[np.mean(np.abs(rng.choice(e,len(e)))) for _ in range(5000)]
    print(f"{name:28s} train RMSE {np.sqrt(np.mean(et**2)):5.2f} s  held-out MAE {np.mean(np.abs(e)):5.2f} s "
          f"[{np.percentile(boot,2.5):.2f}, {np.percentile(boot,97.5):.2f}] = {np.mean(np.abs(e)/yte)*100:.1f}%  max {np.max(np.abs(e)):.1f} s")
    return p
if __name__ == '__main__':
    pA=fit(predA,nA,"additive cost")
    pC=fit(predC,nC,"dependency-aware cost")
    np.save("costA.npy",pA); np.save("costC.npy",pC)
    print("additive: C0 %.1f"%pA[0], {k:round(v,1) for k,v in zip(CAPS,pA[1:12])})
    cur,o=unpack_cur(pC,12)
    print("dep-aware: C0 %.1f"%pC[0], {k:round(v,1) for k,v in zip(CAPS,pC[1:12])})
    print("  curves",{k:[round(x,2) for x in v] for k,v in cur.items()})
    print("  delta",{f"{a}->{b}":round(d,2) for (a,b),d in zip(EDG,pC[o:]) if d>0.05})
