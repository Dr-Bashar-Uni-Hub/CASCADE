import json, statistics as st, os
DATA=os.environ.get("CASCADE_DATA", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results"))
rows=[l.strip().split("|") for l in open(os.path.join(DATA,"verify3.txt")) if not l.startswith("#")]
fz=json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schedules", "frozen_models_v1_3.json")))
ref=st.mean(float(r[3]) for r in rows if r[1]=="reference")
print(f"phase 6 reference mean {ref:.1f} s ({ref/112.6-1:+.1%} vs main study)")
m={}
for r in rows:
    if r[1]=="reference": continue
    for u in r[1].split(";"):
        if "@" in u: rule,b=[s.strip() for s in u.split("@")]; m[(int(b[:-1]),rule)]=(float(r[3])/ref*100,float(r[4]))
out=[]
for b in [90,80,70,60]:
    for rule in ["plain","tie","chance","chance+tie"]:
        cpu,rec=m[(b,rule)]; pl=fz["plan"][f"{b}%/{rule}"]
        out.append((b,rule,rec,cpu,cpu<=b))
        print(f"{b}% {rule:11s} recall {rec:.3f} (pred {pl['pred_recall']:.3f})  CPU {cpu:5.1f}% (pred {pl['pred_cpu_s']/112.6*100:5.1f}%)  {'within' if cpu<=b else 'OVER %+.1f%%'%(cpu/b*100-100)}")
for rule in ["plain","tie","chance","chance+tie"]:
    print(rule,"strictly within:",sum(o[4] for o in out if o[1]==rule),"/4")
print("H4 chance rules within at all budgets:",all(o[4] for o in out if o[1] in("chance","chance+tie")))
print("H5:",[(b, round(m[(b,'plain')][1]-m[(b,'chance+tie')][1],4)) for b in (90,80)])
print("H6:",[(b, round(m[(b,'plain')][0]-m[(b,'tie')][0],1), round(m[(b,'plain')][1]-m[(b,'tie')][1],4)) for b in (90,80)])
