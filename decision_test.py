"""Step 2: does the structural model matter for decisions? Same selection rules, three protection models."""
import itertools, json, io, contextlib, os, numpy as np
from sklearn.ensemble import GradientBoostingRegressor
with contextlib.redirect_stdout(io.StringIO()):
    import fit as F, pc_fast as PC, costfit as CF
CAPS=F.CAPS; FULL=112.6; RES="../results"
GRID={"K1":[0,.2,.4,.6,.8,1],"K2":[0,1],"K3":[0,1],"K4":[0,1],"K5":[0,1]}
for k in ["K6","K7","K8","K9","K10","K11"]: GRID[k]=[0,.25,.5,.75,1]
ALL=np.array(list(itertools.product(*[GRID[k] for k in CAPS])),dtype=float)
fz=json.load(open("frozen_models_v1_3.json"))
with contextlib.redirect_stdout(io.StringIO()):
    _,pkS,_,_=F.fit("s",lambda:F.model_cascade(True),seeds=1)
    _,pkA,pA,predA=F.fit("a",F.model_additive,seeds=1)
pS=np.array(fz["protection_params"]); pC=np.array(fz["cost_params"])
def PS(L): E=PC.prop(PC.X_of(L,F.curves_from(pkS,pS)),pkS.get(pS,"d")); return pkS.get(pS,"b0")[0]+E@pkS.get(pS,"w")
def PA(L): return np.array([predA(pA,{"levels":dict(zip(CAPS,l))}) for l in L])
Ltr=np.array([[r["levels"][k] for k in CAPS] for r in F.TR]); ytr=np.array([r["macro"] for r in F.TR])
G=GradientBoostingRegressor(n_estimators=400,max_depth=3,learning_rate=0.05,random_state=0).fit(Ltr,ytr)
chunk=lambda f: np.concatenate([f(ALL[i:i+100000]) for i in range(0,len(ALL),100000)])
# additive is slow per-row; vectorise via dummy regression equivalent: fit linear model on one-hot of TR (same as additive model)
from sklearn.linear_model import LinearRegression
oh=lambda L: np.column_stack([(L[:,j]==lv).astype(float) for j,k in enumerate(CAPS) for lv in GRID[k][:-1]])
A=LinearRegression().fit(oh(Ltr),ytr)
P={"structural":chunk(PS),"additive":chunk(lambda L:A.predict(oh(L))),"gradient boosting":chunk(G.predict)}
C=chunk(lambda L:CF.predC(pC,L))
mae={"structural":0.0105,"additive":0.069,"gradient boosting":0.021}
M=fz["chance_margin_s"]
key=lambda l: json.dumps({k:float(v) for k,v in zip(CAPS,l) if v!=1},sort_keys=True)
meas={}
for r in F.R: meas[key([r["levels"][k] for k in CAPS])]="main"
def lv(js): d={k:1.0 for k in CAPS}; d.update({k:float(v) for k,v in json.loads(js).items()}); return [d[k] for k in CAPS]
for r in open(f"{RES}/verify.txt"): meas[key(lv(r.split("|")[1]))]=r.split("|")[0]
for fn,li in [("verify2.txt",6),("verify3.txt",6)]:
    for l in open(f"{RES}/{fn}"):
        if l.startswith("#"): continue
        f=l.strip().split("|")
        if f[1] not in ("ref","reference"): meas.setdefault(key(lv(f[li])),f[0])
def choose(Pm,B,eps,extra):
    ok=np.where(C+extra<=B)[0]; top=Pm[ok].max(); near=ok[Pm[ok]>=top-eps-1e-12]; return near[np.argmin(C[near])]
plan={}; new={}
for m in P:
    for b in [.9,.8,.7,.6]:
        for rule,(eps,ex) in {"tie":(mae[m]/2,0),"tie@0.005":(0.005,0),"chance+tie":(mae[m]/2,M)}.items():
            i=choose(P[m],b*FULL,eps,ex); k=key(ALL[i]); tag=meas.get(k)
            plan[f"{m}|{int(b*100)}|{rule}"]={"levels":json.loads(k),"pred_struct":round(float(P['structural'][i]),3),"pred_self":round(float(P[m][i]),3),"pred_cpu":round(float(C[i]/FULL*100),1),"measured_as":tag}
            if not tag: new.setdefault(k,[]).append(f"{m} {rule} @ {int(b*100)}%")
for k,v in plan.items(): print(f"{k:34s} self {v['pred_self']:.3f} struct {v['pred_struct']:.3f} cpu {v['pred_cpu']:5.1f}%  {v['measured_as'] or 'NEW'}")
print("distinct new configurations:",len(new))
json.dump({"plan":plan,"new":new},open("decision_plan.json","w"),indent=1)
