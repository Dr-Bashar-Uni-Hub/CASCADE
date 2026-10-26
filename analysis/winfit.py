import os, pandas as pd, numpy as np, fit as F
DATA=os.environ.get("CASCADE_DATA", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results"))
d=pd.read_csv(os.path.join(DATA, "window_sensitivity.csv"))
main=d[d.set=="main"].pivot_table(index="config",columns="window_s",values="macro_window_recall")
orig={r["id"]:r["macro"] for r in F.R}
rng=np.random.default_rng(5)
for W in [30,60,120,300]:
    for r in F.R: r["macro"]=float(main.loc[r["id"],W])
    out={}
    for name,mk in [("add",F.model_additive),("pre",lambda:F.model_cascade(False)),("cur",lambda:F.model_cascade(True))]:
        res,pk,p,pred=F.fit(name,mk,seeds=3 if name!="add" else 1)
        e=np.array([pred(p,r)-r["macro"] for r in F.TE]); out[name]=(np.abs(e),pk,p)
    da=out["add"][0]-out["pre"][0]
    boot=[da[rng.integers(0,40,40)].mean() for _ in range(5000)]
    pk,p=out["pre"][1],out["pre"][2]
    dd={f"{a}->{b}":round(float(v),2) for (a,b),v in zip(F.EDGES,pk.get(p,"d")) if v>0.3}
    print(f"W={W:3d}s  MAE add {out['add'][0].mean():.3f}  pre {out['pre'][0].mean():.3f}  curves {out['cur'][0].mean():.3f}  diff add-pre {da.mean():.3f} [{np.percentile(boot,2.5):.3f},{np.percentile(boot,97.5):.3f}]  d>0.3 {dd}  full={main.loc['C001',W]:.3f}")
for r in F.R: r["macro"]=orig[r["id"]]
