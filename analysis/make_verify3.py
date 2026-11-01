import os as _os
DATA = _os.environ.get("CASCADE_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results"))
import itertools, json, random, hashlib, numpy as np
import fit as F, pc_fast as PC, costfit as CF
CAPS=F.CAPS
GRID={"K1":[0,.2,.4,.6,.8,1],"K2":[0,1],"K3":[0,1],"K4":[0,1],"K5":[0,1]}
for k in ["K6","K7","K8","K9","K10","K11"]: GRID[k]=[0,.25,.5,.75,1]
ALL=np.array(list(itertools.product(*[GRID[k] for k in CAPS])),dtype=float); FULL=112.6
_,pk,p,pred=F.fit("cur",lambda:F.model_cascade(True),seeds=5)
def Pc(L): E=PC.prop(PC.X_of(L,F.curves_from(pk,p)),pk.get(p,"d")); return pk.get(p,"b0")[0]+E@pk.get(p,"w")
P=np.concatenate([Pc(ALL[i:i+200000]) for i in range(0,len(ALL),200000)])
pC=np.load("costC.npy"); C=np.concatenate([CF.predC(pC,ALL[i:i+200000]) for i in range(0,len(ALL),200000)])
res=CF.yte-CF.predC(pC,CF.Lte); bias,sd=float(res.mean()),float(res.std(ddof=1))
EPS=0.005; Z=1.645; EXTRA=bias+Z*sd
def choose(B,eps,extra):
    ok=np.where(C+extra<=B)[0]; top=P[ok].max(); near=ok[P[ok]>=top-eps-1e-12]; return int(near[np.argmin(C[near])])
lvd=lambda i:{k:float(v) for k,v in zip(CAPS,ALL[i]) if v!=1}
measured={json.dumps(json.loads(r.split("|")[1]),sort_keys=True):r.split("|")[0] for r in open(_os.path.join(DATA, "verify.txt"))}
for r in open(_os.path.join(DATA, "verify2.txt")):
    if r.startswith("#"): continue
    f=r.strip().split("|")
    if f[1]=="new": measured[json.dumps({k:float(v) for k,v in json.loads(f[6]).items()},sort_keys=True)]=f[0]
rules={"plain":(0,0),"tie":(EPS,0),"chance":(0,EXTRA),"chance+tie":(EPS,EXTRA)}
plan={}; new={}; anchors={}
for b in [.9,.8,.7,.6]:
    for nm,(e,x) in rules.items():
        i=choose(b*FULL,e,x); key=json.dumps(lvd(i),sort_keys=True)
        plan[f"{int(b*100)}%/{nm}"]={"levels":lvd(i),"pred_recall":round(float(P[i]),4),"pred_cpu_s":round(float(C[i]),2),"already_measured_as":measured.get(key)}
        (anchors if key in measured else new).setdefault(key,[]).append(f"{nm} @ {int(b*100)}%")
cfg=[{"levels":json.loads(k),"used_by":u,"cost_only":False} for k,u in new.items()]
cfg+=[{"levels":json.loads(k),"used_by":u+["anchor re-measure of "+measured[k]],"cost_only":True} for k,u in anchors.items()]
random.Random(20261028).shuffle(cfg)
items=[];nr=0
for n,c in enumerate(cfg,1):
    if (n-1)%5==0: nr+=1; items.append({"id":f"UR{nr:02d}","type":"reference","levels":{},"rule_seed":20261019})
    items.append({"id":f"U{n:03d}","type":"config","phase":"6","held_out":False,"levels":c["levels"],"rule_seed":20261019,"extra_cost_reps":2,"cost_only":c["cost_only"],"used_by":c["used_by"]})
json.dump({"protocol":"CASCADE-IDS protocol v1.3: phase 6, uncertainty-aware optimiser (pre-registered)","order_seed":20261028,"items":items},open("verify3_schedule.json","w"),indent=1)
frozen={"protection_model":"CASCADE with level curves","protection_params":[float(v) for v in p],"cost_params":[float(v) for v in pC],
        "cost_residual_bias_s":bias,"cost_residual_sd_s":sd,"z":Z,"tie_tolerance":EPS,"chance_margin_s":EXTRA,"full_reference_s":FULL,"plan":plan}
s=json.dumps(frozen,indent=1); open("frozen_models_v1_3.json","w").write(s)
print("new",len(new),"anchors",len(anchors),"refs",nr,"items",len(items))
print("frozen sha256",hashlib.sha256(s.encode()).hexdigest())
for k,v in plan.items(): print(k,v["pred_recall"],round(v["pred_cpu_s"]/FULL*100,1),v["already_measured_as"])
