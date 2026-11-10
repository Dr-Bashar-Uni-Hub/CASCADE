import os as _os
DATA = _os.environ.get("CASCADE_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results"))
FIGS = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "figures")

import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":8.5,"axes.spines.top":False,"axes.spines.right":False,"savefig.dpi":300})
FULL=112.6; s1=(115.5+106.3)/2; s2=120.3; NOISE=3.2
D={"Dependency-aware optimum":[(.9,0.575,98.4,1),(.8,0.575,99.6,2),(.7,0.562,89.6,2),(.6,0.432,67.7,2)],
   "Dependency-unaware optimum":[(.9,0.579,83.8,1),(.8,0.579,83.8,1),(.7,0.579,94.1,2),(.6,0.437,81.0,1),(.5,0.432,61.4,1),(.4,0.432,64.3,1)],
   "CASCADE V2 heuristic":[(.9,0.579,103.9,2),(.8,0.575,92.8,1),(.7,0.558,82.6,1),(.6,0.432,60.1,1)],
   "Most expensive first":[(.9,0.442,98.2,1),(.8,0.442,90.8,1),(.7,0.437,83.2,1),(.6,0.432,61.9,1)],
   "Rules first":[(.9,0.427,102.3,1),(.8,0.295,87.3,1),(.7,0.275,61.4,1),(.6,0.275,61.4,1)]}
C={"Dependency-aware optimum":"#2b5c8a","Dependency-unaware optimum":"#d9a441","CASCADE V2 heuristic":"#5b9b5b","Most expensive first":"#8a5c9b","Rules first":"#b03030"}
MK={"Dependency-aware optimum":"o","Dependency-unaware optimum":"s","CASCADE V2 heuristic":"^","Most expensive first":"v","Rules first":"D"}
fig,axs=plt.subplots(1,2,figsize=(7.4,3.0))
budgets=[.9,.8,.7,.6,.5,.4]; meths=list(D); w=0.15
ax=axs[1]
ax.axhspan(-NOISE,NOISE,color="#dddddd",zorder=0); ax.axhline(0,color="k",lw=0.8)
for j,m in enumerate(meths):
    for b,r,c,s in D[m]:
        i=budgets.index(b); raw=(c/FULL*100)/(b*100)*100-100
        norm=(c*FULL/(s1 if s==1 else s2)/FULL*100)/(b*100)*100-100
        x=i+(j-2)*w
        ax.bar(x,raw,w,color=C[m],edgecolor="k",lw=0.3,label=m if i==0 else None)
        ax.plot(x,norm,"o",ms=2.6,mfc="white",mec="k",mew=0.6)
ax.set_xticks(range(6),[f"{int(b*100)}%" for b in budgets]); ax.set_xlabel("CPU budget")
ax.set_ylabel("Measured CPU vs budget (%)"); ax.set_title("(b) Over (+) or under (−) budget; grey = run-to-run noise",fontsize=8,loc="left")
ax.text(5.45,-19,"○ session-normalised",fontsize=6.5,ha="right")
ax=axs[0]
for m in meths:
    bs=[t[0] for t in D[m]]; rs=[t[1] for t in D[m]]
    ax.plot([b*100 for b in bs],rs,color=C[m],lw=1,zorder=1)
    for b,r,c,s in D[m]:
        over=(c/FULL*100)>b*100*(1+NOISE/100)
        ax.scatter(b*100,r,marker=MK[m],s=26,facecolors="white" if over else C[m],edgecolors=C[m],linewidths=1.1,zorder=2)
ax.set_xlabel("CPU budget (% of full)"); ax.set_ylabel("Measured macro window recall"); ax.invert_xaxis()
ax.set_title("(a) Detection; hollow = measured CPU over budget",fontsize=8,loc="left")
h,l=axs[1].get_legend_handles_labels(); fig.legend(h,l,loc="lower center",ncol=3,fontsize=7,frameon=False,bbox_to_anchor=(0.5,-0.09))
fig.tight_layout(rect=(0,0.06,1,1))
fig.savefig(FIGS+"/fig6_budgets.png",bbox_inches="tight"); fig.savefig(FIGS+"/fig6_budgets.pdf",bbox_inches="tight")
