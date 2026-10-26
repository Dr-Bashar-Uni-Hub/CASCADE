import os as _os
DATA = _os.environ.get("CASCADE_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results"))
FIGS = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "figures")

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"savefig.dpi":300})
def box(ax,x,y,lab,fc="#f4f4f4"):
    ax.add_patch(FancyBboxPatch((x-0.5,y-0.2),1.0,0.4,boxstyle="round,pad=0.02,rounding_size=0.06",fc=fc,ec="#555",lw=0.9))
    ax.text(x,y,lab,ha="center",va="center",fontsize=7)
def arrow(ax,a,b,d,t=0.45,dx=0.06):
    (x1,y1),(x2,y2)=a,b
    ax.annotate("",xy=(x2,y2+0.21),xytext=(x1,y1-0.21),arrowprops=dict(arrowstyle="->",lw=0.6+2.0*d,color="#b03030"))
    mx,my=x1+(x2-x1)*t,(y1-0.21)+((y2+0.21)-(y1-0.21))*t
    ax.text(mx+dx,my,f"{d:.2f}",fontsize=6.8,color="#b03030",ha="left",va="center",bbox=dict(fc="white",ec="none",pad=0.3))
fig,axs=plt.subplots(1,2,figsize=(7.4,3.0),gridspec_kw={"width_ratios":[1,1.55]})
ax=axs[0]; ax.axis("off"); ax.set_title("(a) Detection: fitted d (pre-registered model)",fontsize=8.5,loc="left")
P={"K1":(0,2),"K2":(0,1),"K6":(0,0),"K3":(1.3,1),"K8":(1.3,0),"K7":(2.6,1),"K9":(2.6,0)}
L={"K1":"K1 stream\nreassembly","K2":"K2 HTTP\nparser","K6":"K6 web-attack\nrules","K3":"K3 TLS\nparser","K8":"K8 exploit\nrules","K7":"K7 scan\nrules","K9":"K9 malware\nrules"}
for k in P: box(ax,*P[k],L[k])
arrow(ax,P["K1"],P["K2"],0.92); arrow(ax,P["K2"],P["K6"],0.94)
ax.text(1.3,-0.45,"Heartbleed: either K3 or K8 suffices",ha="center",fontsize=6.5,style="italic")
ax.text(2.6,1.55,"no upstream\ndependency",ha="center",fontsize=6.5,style="italic")
ax.set_xlim(-0.6,3.2); ax.set_ylim(-0.65,2.35)
ax=axs[1]; ax.axis("off"); ax.set_title("(b) CPU cost: fitted δ ≥ 0.5",fontsize=8.5,loc="left")
Q={"K1":(2.4,2),"K2":(0,1),"K3":(1.2,1),"K5":(2.4,1),"K7":(3.6,1),"K9":(4.8,1),"K6":(0,0),"K11":(1.2,0)}
LQ={"K1":"K1 stream\nreassembly","K2":"K2 HTTP\nparser","K3":"K3 TLS\nparser","K5":"K5 SSH/FTP\nparsers","K7":"K7 scan\nrules","K6":"K6 web-attack\nrules","K11":"K11 low-conf.\nrules","K9":"K9 malware\nrules"}
for k in Q: box(ax,*Q[k],LQ[k])
arrow(ax,Q["K1"],Q["K2"],1.0,0.55,-0.25); arrow(ax,Q["K1"],Q["K3"],0.93,0.55,-0.25); arrow(ax,Q["K1"],Q["K5"],1.0,0.5,0.05)
arrow(ax,Q["K1"],Q["K7"],1.0,0.55,0.05); arrow(ax,Q["K1"],Q["K9"],0.75,0.55,0.08)
arrow(ax,Q["K2"],Q["K6"],1.0,0.45,0.06); arrow(ax,Q["K2"],Q["K11"],1.0,0.45,0.1)
ax.set_xlim(-0.6,5.4); ax.set_ylim(-0.65,2.35)
fig.tight_layout(); fig.savefig(FIGS+"/fig3_dependencies.png",bbox_inches="tight"); fig.savefig(FIGS+"/fig3_dependencies.pdf",bbox_inches="tight")
