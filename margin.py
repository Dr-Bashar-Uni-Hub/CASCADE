import os as _os
DATA = _os.environ.get("CASCADE_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results"))
FIGS = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "figures")

import itertools, json, numpy as np
import fit as F, pc_fast as PC, costfit as CF
CAPS=F.CAPS
GRID={"K1":[0,.2,.4,.6,.8,1],"K2":[0,1],"K3":[0,1],"K4":[0,1],"K5":[0,1]}
for k in ["K6","K7","K8","K9","K10","K11"]: GRID[k]=[0,.25,.5,.75,1]
ALL=np.array(list(itertools.product(*[GRID[k] for k in CAPS])),dtype=float)
FULL=112.6
res,pk,p,pred=F.fit("curves",lambda:F.model_cascade(True),seeds=5)
pC=np.load("costC.npy")
def Pc(L):
    E=PC.prop(PC.X_of(L,F.curves_from(pk,p)),pk.get(p,"d")); return pk.get(p,"b0")[0]+E@pk.get(p,"w")
P=np.concatenate([Pc(ALL[i:i+200000]) for i in range(0,len(ALL),200000)])
C=np.concatenate([CF.predC(pC,ALL[i:i+200000]) for i in range(0,len(ALL),200000)])
rows=[l.strip().split("|") for l in open(_os.path.join(DATA, "verify.txt"))]
LV=np.array([[{**{k:1.0 for k in CAPS},**json.loads(r[1])}[k] for k in CAPS] for r in rows]); yv=np.array([float(r[2]) for r in rows])
resid=yv-CF.predC(pC,LV)          # measured minus predicted, verified configs
def best(B):
    ok=C<=B; c=np.where(ok)[0]; top=P[c].max(); near=c[P[c]>=top-1e-9]; return near[np.argmin(C[near])]
def lv(i): return {k:float(v) for k,v in zip(CAPS,ALL[i]) if v!=1}
measured={json.dumps({k:float(v) for k,v in json.loads(r[1]).items()},sort_keys=True):(float(r[2]),float(r[3])) for r in rows}
plan={}
print("budget margin  predP  predC  P(meas<=budget+3.2%)  measured_if_known  levels")
for b in [.9,.8,.7,.6]:
    for m in [0,.05,.10]:
        i=best(b*FULL*(1-m)); key=json.dumps(lv(i),sort_keys=True)
        pfeas=np.mean(C[i]+resid<=b*FULL*1.032)
        meas=measured.get(key)
        print(f"{b:.0%}  {m:.0%}   {P[i]:.3f}  {C[i]:6.1f}  {pfeas:5.2f}   {meas}   {lv(i)}")
        plan.setdefault(f"{b:.2f}",{})[f"{m:.2f}"]=lv(i)
json.dump(plan,open("margin_plan.json","w"),indent=1)
