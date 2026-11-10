"""Stage 2 audit + uncertainty-aware optimisation (model-based, checked against every measured configuration)."""
import os as _os
DATA = _os.environ.get("CASCADE_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results"))

import itertools, json, numpy as np
import fit as F, pc_fast as PC, costfit as CF
CAPS=F.CAPS
GRID={"K1":[0,.2,.4,.6,.8,1],"K2":[0,1],"K3":[0,1],"K4":[0,1],"K5":[0,1]}
for k in ["K6","K7","K8","K9","K10","K11"]: GRID[k]=[0,.25,.5,.75,1]
ALL=np.array(list(itertools.product(*[GRID[k] for k in CAPS])),dtype=float); FULL=112.6
_,pk,p,pred=F.fit("cur",lambda:F.model_cascade(True),seeds=5)
def Pc(L): E=PC.prop(PC.X_of(L,F.curves_from(pk,p)),pk.get(p,"d")); return pk.get(p,"b0")[0]+E@pk.get(p,"w")
P=np.concatenate([Pc(ALL[i:i+200000]) for i in range(0,len(ALL),200000)])
pC=np.load("costC.npy"); C=np.concatenate([CF.predC(pC,ALL[i:i+200000]) for i in range(0,len(ALL),200000)])
# measured configurations: key -> (recall, cpu on 112.6 scale)
key=lambda l: tuple(np.round(l,2))
meas={}
for r in F.R: meas[key([r["levels"][k] for k in CAPS])]=[r["macro"],None]
for r in CF.R:
    if r["id"].startswith("C"): meas.setdefault(key(r["L"]),[None,None])[1]=r["cost"]
def lv(js): d={k:1.0 for k in CAPS}; d.update({k:float(v) for k,v in json.loads(js).items()}); return [d[k] for k in CAPS]
for r in [l.strip().split("|") for l in open(_os.path.join(DATA, "verify.txt"))]: meas[key(lv(r[1]))]=[float(r[3]),None]
v2=[l.strip().split("|") for l in open(_os.path.join(DATA, "verify2.txt")) if not l.startswith("#")]
ref=np.mean([float(r[3]) for r in v2 if r[1]=="ref"])
for r in v2:
    if r[1]=="ref": continue
    k=key(lv(r[6])); m=meas.setdefault(k,[None,None]); m[1]=float(r[3])*FULL/ref
    if r[1]=="new": m[0]=float(r[4])
# residuals of the cost model on held-out (random) configurations
res=CF.yte-CF.predC(pC,CF.Lte); bias,sd=res.mean(),res.std(ddof=1)
print(f"held-out cost residual (measured-predicted): mean {bias:+.2f} s, sd {sd:.2f} s")
def choose(B,eps=0.0,extra=0.0):
    ok=np.where(C+extra<=B)[0]
    if len(ok)==0: return None
    top=P[ok].max(); near=ok[P[ok]>=top-eps-1e-12]; return near[np.argmin(C[near])]
rules={"plain (paper)":(0,0),"tie tolerance 0.005":(0.005,0),
       "chance-constrained 95%":(0,bias+1.645*sd),"chance-constr. + tie tol.":(0.005,bias+1.645*sd)}
print(f"chance-constrained adds {bias+1.645*sd:.1f} s = {(bias+1.645*sd)/FULL:.1%} of full CPU")
for b in [.9,.8,.7,.6]:
    print(f"\nbudget {b:.0%} ({b*FULL:.1f} s)")
    for nm,(eps,ex) in rules.items():
        i=choose(b*FULL,eps,ex); k=key(ALL[i]); m=meas.get(k)
        ms="not measured" if not m else (f"MEASURED recall {m[0]:.3f}" if m[0] is not None else "recall n/a")+ (f", CPU {m[1]/FULL:.1%} ({'within' if m[1]<=b*FULL else 'OVER'})" if m and m[1] else "")
        print(f"  {nm:28s} pred {P[i]:.3f} @ {C[i]/FULL:5.1%}   {ms}   {{{', '.join(f'{c}:{v:g}' for c,v in zip(CAPS,ALL[i]) if v!=1)}}}")
# near-tie audit: how much cheaper within eps of the optimum
print("\nNear-tie audit (plain optimum vs cheapest config within 0.005 predicted recall):")
for b in [.9,.8,.7,.6]:
    i0=choose(b*FULL); i1=choose(b*FULL,0.005)
    print(f"  {b:.0%}: optimum {P[i0]:.3f}@{C[i0]:.1f}s  vs  {P[i1]:.3f}@{C[i1]:.1f}s  -> saves {C[i0]-C[i1]:.1f} s for {P[i0]-P[i1]:.3f} predicted recall")
