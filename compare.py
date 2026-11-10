"""Stage 3: CASCADE vs standard predictive baselines (detection and cost), same data, same splits."""
import os as _os
DATA = _os.environ.get("CASCADE_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results"))

import json, itertools, numpy as np, warnings
warnings.filterwarnings("ignore")
from sklearn.linear_model import RidgeCV, LassoCV, LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import fit as F, costfit as CF
CAPS=F.CAPS
GRID={"K1":[0,.2,.4,.6,.8,1],"K2":[0,1],"K3":[0,1],"K4":[0,1],"K5":[0,1]}
for k in ["K6","K7","K8","K9","K10","K11"]: GRID[k]=[0,.25,.5,.75,1]
def onehot(L):
    cols=[]
    for j,k in enumerate(CAPS):
        for lv in GRID[k][:-1]: cols.append((L[:,j]==lv).astype(float))
    return np.column_stack(cols)
def pairs(L):
    D=1-L                                  # reduction amount
    return np.column_stack([D[:,a]*D[:,b] for a,b in itertools.combinations(range(len(CAPS)),2)])
def feats(L,kind):
    if kind=="onehot": return onehot(L)
    if kind=="pair": return np.hstack([onehot(L),pairs(L)])
    return L
# ---------------- data
Ltr=np.array([[r["levels"][k] for k in CAPS] for r in F.TR]); ytr=np.array([r["macro"] for r in F.TR])
Lte=np.array([[r["levels"][k] for k in CAPS] for r in F.TE]); yte=np.array([r["macro"] for r in F.TE])
rows=[l.strip().split("|") for l in open(_os.path.join(DATA, "verify.txt"))]
v2=[l.strip().split("|") for l in open(_os.path.join(DATA, "verify2.txt")) if not l.startswith("#")]
def lv(js): d={k:1.0 for k in CAPS}; d.update({k:float(v) for k,v in json.loads(js).items()}); return [d[k] for k in CAPS]
Lv=np.array([lv(r[1]) for r in rows]); yv=np.array([float(r[3]) for r in rows])
new=[r for r in v2 if r[1]=="new"]
Lv=np.vstack([Lv,np.array([lv(r[6]) for r in new])]); yv=np.concatenate([yv,[float(r[4]) for r in new]])
# cost external test: phase-5b re-measurement (all 29 in one host state), rescaled to main-study reference
ref=np.mean([float(r[3]) for r in v2 if r[1]=="ref"]); scale=112.6/ref
cv=[(lv(r[6]),float(r[3])*scale) for r in v2 if r[1]!="ref"]
Lcv=np.array([c[0] for c in cv]); ycv=np.array([c[1] for c in cv])
LtrC=CF.Ltr; ytrC=CF.ytr; LteC=CF.Lte; yteC=CF.yte
rng=np.random.default_rng(3)
def ci(e): b=[np.mean(np.abs(rng.choice(e,len(e)))) for _ in range(4000)]; return np.percentile(b,[2.5,97.5])
def report(name,pte,pv,yte_,yv_,unit=""):
    e1=pte-yte_; e2=pv-yv_; c=ci(e1)
    print(f"  {name:34s} held-out MAE {np.mean(abs(e1)):.4f}{unit} [{c[0]:.4f},{c[1]:.4f}]  max {np.max(abs(e1)):.3f}   verified MAE {np.mean(abs(e2)):.4f}{unit} bias {np.mean(e2):+.4f}")
    return np.abs(e1)
print("=== DETECTION (macro window recall); train 110, held-out 40, verified 29")
res={}
base=[("Linear, one-hot levels (additive)",lambda:LinearRegression(),"onehot"),
      ("Ridge, one-hot + pairwise",lambda:make_pipeline(StandardScaler(),RidgeCV(alphas=np.logspace(-4,3,30))),"pair"),
      ("Lasso, one-hot + pairwise",lambda:make_pipeline(StandardScaler(),LassoCV(cv=5,max_iter=50000,random_state=0)),"pair"),
      ("Random forest",lambda:RandomForestRegressor(500,random_state=0,min_samples_leaf=1),"raw"),
      ("Gradient boosting",lambda:GradientBoostingRegressor(n_estimators=400,max_depth=3,learning_rate=0.05,random_state=0),"raw")]
for name,mk,kind in base:
    m=mk().fit(feats(Ltr,kind),ytr); res[name]=report(name,m.predict(feats(Lte,kind)),m.predict(feats(Lv,kind)),yte,yv)
for nm,mk in [("CASCADE pre-registered (21 par.)",lambda:F.model_cascade(False)),("CASCADE + level curves (43 par.)",lambda:F.model_cascade(True))]:
    _,pk,p,pred=F.fit(nm,mk,seeds=5)
    rr=lambda L:[{"levels":dict(zip(CAPS,l))} for l in L]
    res[nm]=report(nm,np.array([pred(p,r) for r in F.TE]),np.array([pred(p,r) for r in rr(Lv)]),yte,yv)
d=res["Ridge, one-hot + pairwise"]-res["CASCADE pre-registered (21 par.)"]
b=[d[rng.integers(0,40,40)].mean() for _ in range(4000)]
print(f"  paired: Ridge-pairwise minus CASCADE pre-reg  {d.mean():+.4f} [{np.percentile(b,2.5):+.4f},{np.percentile(b,97.5):+.4f}]")
d=res["Lasso, one-hot + pairwise"]-res["CASCADE + level curves (43 par.)"]
b=[d[rng.integers(0,40,40)].mean() for _ in range(4000)]
print(f"  paired: Lasso-pairwise minus CASCADE curves   {d.mean():+.4f} [{np.percentile(b,2.5):+.4f},{np.percentile(b,97.5):+.4f}]")
print("\n=== COST (processing CPU, s, main-study scale); train 110, held-out 40, verified 29 (re-measured, rescaled)")
resC={}
for name,mk,kind in base:
    m=mk().fit(feats(LtrC,kind),ytrC); resC[name]=report(name,m.predict(feats(LteC,kind)),m.predict(feats(Lcv,kind)),yteC,ycv," s")
pA=np.load("costA.npy"); pC=np.load("costC.npy")
resC["add"]=report("Additive cost model (paper)",CF.predA(pA,LteC),CF.predA(pA,Lcv),yteC,ycv," s")
resC["dep"]=report("Dependency-aware cost model (paper)",CF.predC(pC,LteC),CF.predC(pC,Lcv),yteC,ycv," s")
d=resC["Ridge, one-hot + pairwise"]-resC["dep"]; b=[d[rng.integers(0,40,40)].mean() for _ in range(4000)]
print(f"  paired: Ridge-pairwise minus dependency-aware  {d.mean():+.3f} s [{np.percentile(b,2.5):+.3f},{np.percentile(b,97.5):+.3f}]")

# paired comparisons for the structural model vs best black box
_,pk,p,pred=F.fit("cur",lambda:F.model_cascade(True),seeds=5)
pc_te=np.array([pred(p,r) for r in F.TE]); pc_v=np.array([pred(p,{"levels":dict(zip(CAPS,l))}) for l in Lv])
g=GradientBoostingRegressor(n_estimators=400,max_depth=3,learning_rate=0.05,random_state=0).fit(Ltr,ytr)
for nm,a,b_,y_ in [("held-out",g.predict(Lte),pc_te,yte),("verified",g.predict(Lv),pc_v,yv)]:
    d=np.abs(a-y_)-np.abs(b_-y_); n=len(d); bb=[d[rng.integers(0,n,n)].mean() for _ in range(4000)]
    print(f"  paired {nm}: GBR minus CASCADE+curves {d.mean():+.4f} [{np.percentile(bb,2.5):+.4f},{np.percentile(bb,97.5):+.4f}]")
gC=GradientBoostingRegressor(n_estimators=400,max_depth=3,learning_rate=0.05,random_state=0).fit(LtrC,ytrC)
for nm,a,b_,y_ in [("held-out",gC.predict(LteC),CF.predC(pC,LteC),yteC),("verified",gC.predict(Lcv),CF.predC(pC,Lcv),ycv)]:
    d=np.abs(a-y_)-np.abs(b_-y_); n=len(d); bb=[d[rng.integers(0,n,n)].mean() for _ in range(4000)]
    print(f"  paired cost {nm}: GBR minus dependency-aware {d.mean():+.3f} s [{np.percentile(bb,2.5):+.3f},{np.percentile(bb,97.5):+.3f}]")
