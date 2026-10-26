import os as _os
DATA = _os.environ.get("CASCADE_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results"))
FIGS = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "figures")

import json, numpy as np, fit as F, costfit as CF
rng=np.random.default_rng(11)
def boot(f, n, B=10000):
    idx=rng.integers(0,n,(B,n)); return np.percentile([f(i) for i in idx],[2.5,97.5])
# protection held-out paired
_,pkp,pp,predp=F.fit("p",lambda:F.model_cascade(False),seeds=5)
_,pka,pa,preda=F.fit("a",F.model_additive,seeds=1)
_,pkc,pc,predc=F.fit("c",lambda:F.model_cascade(True),seeds=5)
m=np.array([r["macro"] for r in F.TE])
ea=np.abs([preda(pa,r) for r in F.TE]-m); ep=np.abs([predp(pp,r) for r in F.TE]-m); ec=np.abs([predc(pc,r) for r in F.TE]-m)
d=ea-ep; print("MAE add %.4f pre %.4f curves %.4f"%(ea.mean(),ep.mean(),ec.mean()))
print("paired diff add-pre %.4f CI"%d.mean(), boot(lambda i:d[i].mean(),40), "frac boot<=0", np.mean([d[rng.integers(0,40,40)].mean()<=0 for _ in range(10000)]))
d2=ep-ec; print("paired diff pre-curves %.4f CI"%d2.mean(), boot(lambda i:d2[i].mean(),40))
print("CASCADE pre MAE CI", boot(lambda i:ep[i].mean(),40), "upper vs 0.05")
# cost held-out paired
pA=np.load("costA.npy"); pC=np.load("costC.npy")
eA=np.abs(CF.predA(pA,CF.Lte)-CF.yte); eC=np.abs(CF.predC(pC,CF.Lte)-CF.yte); dc=eA-eC
print("cost held-out MAE add %.2f dep %.2f diff %.2f CI"%(eA.mean(),eC.mean(),dc.mean()), boot(lambda i:dc[i].mean(),40))
resC=CF.predC(pC,CF.Lte)-CF.yte; print("held-out cost residual mean %.2f sd %.2f"%(resC.mean(),resC.std(ddof=1)))
# verification cost bias
rows=[l.strip().split("|") for l in open(_os.path.join(DATA, "verify.txt"))]
LV=np.array([[{**{k:1.0 for k in CF.CAPS},**json.loads(r[1])}[k] for k in CF.CAPS] for r in rows]); y=np.array([float(r[2]) for r in rows])
rv=CF.predC(pC,LV)-y; ra=CF.predA(pA,LV)-y
print("verif cost bias dep %.2f CI"%rv.mean(), boot(lambda i:rv[i].mean(),25), " sd %.2f"%rv.std(ddof=1))
print("verif cost bias add %.2f CI"%ra.mean(), boot(lambda i:ra[i].mean(),25))
dv=np.abs(ra)-np.abs(rv); print("verif paired |err| add-dep %.2f CI"%dv.mean(), boot(lambda i:dv[i].mean(),25))
# violation probability if predicted exactly at budget, using held-out residuals (meas-pred)
r=-(resC); print("P(meas > pred) held-out %.2f; P(meas > pred*1.0+3.6s) %.2f"%(np.mean(r>0),np.mean(r>3.6)))
print("verif: share of configs measuring above prediction %.2f, above by >5%% %.2f"%(np.mean(-rv>0),np.mean(-rv/ (y)>0.05)))
