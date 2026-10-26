import os as _os
DATA = _os.environ.get("CASCADE_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results"))
FIGS = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "figures")

import numpy as np
CLS=["Bot","SHT","FTP","HB","Inf","IPS","PS","SSH","SQ","X"]
DEN={"Bot":59,"SHT":17,"FTP":62,"HB":11,"Inf":31,"IPS":39,"PS":26,"SSH":64,"SQ":4,"X":18}
BASE={"Bot":13,"SHT":2,"FTP":62,"HB":1,"Inf":10,"IPS":38,"PS":12,"SSH":31,"SQ":4,"X":18}
CONST=1+1+18/19+0+0
CAPS=[f"K{i}" for i in range(1,12)]
def load(path=None):
    path = path or _os.path.join(DATA, "det.txt")
    rows=[]
    for line in open(path):
        if line.startswith("#") or not line.strip(): continue
        cid,ph,seed,lv,ov,mac=line.strip().split("|")
        levels={k:1.0 for k in CAPS}
        for kv in filter(None,lv.split(",")):
            k,v=kv.split("="); levels[k]=float(v)
        cnt=dict(BASE)
        for kv in filter(None,ov.split(",")):
            k,v=kv.split("="); cnt[k]=int(v)
        rec={c:cnt[c]/DEN[c] for c in CLS}
        macro=(sum(rec.values())+CONST)/15
        rows.append(dict(id=cid,phase=int(ph),seed=int(seed),levels=levels,rec=rec,macro=macro,reported=float(mac)))
    return rows
if __name__=="__main__":
    R=load(); bad=[(r["id"],round(r["macro"],6),r["reported"]) for r in R if abs(r["macro"]-r["reported"])>2e-6]
    print(len(R),"rows; mismatches:",bad)
