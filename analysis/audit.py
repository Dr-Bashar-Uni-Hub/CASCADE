import os as _os
DATA = _os.environ.get("CASCADE_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results"))
FIGS = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "figures")

import json, numpy as np, fit as F, costfit as CF
FULL=112.6; NOISE=0.032
sess1=(115.5+106.3)/2; sess2=120.3
# (method, budget, recall, raw cost s, session)
V={"V012":1,"V008":1,"V019":1,"V001":1,"V022":2,"V011":1,"V016":1,"V023":2,"V003":1,"V017":1,"V005":1,"V002":1,
   "V024":2,"V025":2,"V020":2,"V004":1,"V014":1,"V006":1,"V021":2,"V007":1,"V013":1,"V009":1,"V010":1,"V015":1,"V018":1}
rows=[l.strip().split("|") for l in open(_os.path.join(DATA, "verify.txt"))]
cost={r[0]:float(r[2]) for r in rows}; rec={r[0]:float(r[3]) for r in rows}
plan=[("Dependency-aware optimum",[(0.9,"V019"),(0.8,"V023"),(0.7,"V024"),(0.6,"V021")]),
      ("Dep-aware optimum (per-class)",[(0.9,"V001"),(0.8,"V003"),(0.7,"V025"),(0.6,"V007")]),
      ("Dependency-unaware optimum",[(0.9,"V008"),(0.8,"V008"),(0.7,"V020"),(0.6,"V013"),(0.5,"V015"),(0.4,"V018")]),
      ("CASCADE V2 heuristic",[(0.9,"V022"),(0.8,"V017"),(0.7,"V004"),(0.6,"V010")]),
      ("Most expensive first",[(0.9,"V011"),(0.8,"V005"),(0.7,"V014"),(0.6,"V009")]),
      ("Rules first",[(0.9,"V016"),(0.8,"V002"),(0.7,"V006"),(0.6,"V006")])]
print(f"{'method':30s} bud  cfg   recall  raw%   norm%  raw_over%  norm_over%  ok_raw ok_raw_tol ok_norm_tol")
tally={}
for m,lst in plan:
    for b,c in lst:
        raw=cost[c]/FULL*100; ref=sess1 if V[c]==1 else sess2; norm=cost[c]*FULL/ref/FULL*100
        ro=(raw/(b*100)-1)*100; no=(norm/(b*100)-1)*100
        okr=raw<=b*100; okrt=raw<=b*100*(1+NOISE); oknt=norm<=b*100*(1+NOISE)
        tally.setdefault(m,[0,0,0,0]); t=tally[m]; t[0]+=1; t[1]+=okr; t[2]+=okrt; t[3]+=oknt
        print(f"{m:30s} {b:.0%} {c} {rec[c]:.3f} {raw:6.1f} {norm:6.1f} {ro:+7.1f} {no:+7.1f}   {okr!s:5} {okrt!s:5} {oknt!s:5}")
print("\nwithin budget counts (n, raw strict, raw+3.2% noise, normalized+3.2%):")
for m,t in tally.items(): print(f"  {m:30s} {t}")
