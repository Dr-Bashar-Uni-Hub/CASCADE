import os as _os
DATA = _os.environ.get("CASCADE_DATA", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "results"))
FIGS = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "figures")

import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import fit as F, pc_fast as PC, costfit as CF
OUT=FIGS+"/"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"axes.spines.top":False,"axes.spines.right":False,"savefig.dpi":300})
def save(fig,name):
    fig.savefig(OUT+name+".png",bbox_inches="tight"); fig.savefig(OUT+name+".pdf",bbox_inches="tight"); plt.close(fig)

# ---------- Fig 1 workflow ----------
fig,ax=plt.subplots(figsize=(7.2,1.9)); ax.axis("off")
steps=[("Pilot","setup checks,\nmeasurement rules,\nprotocol frozen"),
       ("Main study","150 configurations\ndetection: full week\ncost: Thursday ×3"),
       ("Model fitting","protection + cost\nfitted on 110,\nvalidated on 40"),
       ("Exact optimisation","1.5 M configurations\nenumerated,\n7 budgets, 6 methods"),
       ("Verification","25 chosen configs\nrun in Suricata,\npredicted vs measured")]
w,h,gap=1.25,1.25,0.22
for i,(t,s) in enumerate(steps):
    x=i*(w+gap)
    ax.add_patch(FancyBboxPatch((x,0),w,h,boxstyle="round,pad=0.02,rounding_size=0.08",fc="#eef3f8",ec="#2b5c8a",lw=1))
    ax.text(x+w/2,h-0.2,t,ha="center",va="center",weight="bold",fontsize=8.5)
    ax.text(x+w/2,h/2-0.12,s,ha="center",va="center",fontsize=7.2)
    if i<len(steps)-1: ax.annotate("",xy=(x+w+gap-0.02,h/2),xytext=(x+w+0.02,h/2),arrowprops=dict(arrowstyle="->",lw=1.2,color="#2b5c8a"))
ax.set_xlim(-0.05,5*(w+gap)); ax.set_ylim(-0.05,h+0.05)
save(fig,"fig1_workflow")

# ---------- Fig 2 dependencies ----------
def depgraph(ax,title,nodes,edges):
    ax.axis("off"); ax.set_title(title,fontsize=9,loc="left")
    for k,(x,y,lab) in nodes.items():
        ax.add_patch(FancyBboxPatch((x-0.55,y-0.18),1.1,0.36,boxstyle="round,pad=0.02,rounding_size=0.06",fc="#f4f4f4",ec="#555",lw=0.9))
        ax.text(x,y,lab,ha="center",va="center",fontsize=7.3)
    for a,b,d,style in edges:
        (x1,y1,_),(x2,y2,_)=nodes[a],nodes[b]
        ax.annotate("",xy=(x2,y2+(0.2 if y2<y1 else -0.2) if abs(y2-y1)>0.1 else y2),xytext=(x1,y1+(-0.2 if y2<y1 else 0.2) if abs(y2-y1)>0.1 else y1),
                    arrowprops=dict(arrowstyle="->",lw=0.6+2.2*d,color="#b03030" if style=="dep" else "#2b5c8a",linestyle="-" if style=="dep" else "--"))
        ax.text((x1+x2)/2+0.08,(y1+y2)/2,f"{d:.2f}",fontsize=7,color="#b03030" if style=="dep" else "#2b5c8a")
    ax.set_xlim(-0.8,3.8); ax.set_ylim(-0.4,2.4)
fig,axs=plt.subplots(1,2,figsize=(7.2,2.9))
nodes={"K1":(0.2,2.0,"K1 stream\nreassembly"),"K2":(0.2,1.0,"K2 HTTP\nparser"),"K6":(0.2,0.0,"K6 web-attack\nrules"),
       "K3":(1.7,1.0,"K3 TLS\nparser"),"K8":(1.7,0.0,"K8 exploit\nrules"),"K7":(3.1,1.0,"K7 scan\nrules"),"K9":(3.1,0.0,"K9 malware\nrules")}
depgraph(axs[0],"(a) Detection (fitted d, pre-registered model)",nodes,[("K1","K2",0.92,"dep"),("K2","K6",0.94,"dep")])
axs[0].text(1.7,-0.38,"Heartbleed: K3 OR K8 suffices",ha="center",fontsize=7,style="italic")
axs[0].text(3.1,-0.38,"K7, K9: no upstream dependency",ha="center",fontsize=7,style="italic")
nodes2={"K1":(1.6,2.0,"K1 stream\nreassembly"),"K2":(0.0,1.0,"K2 HTTP\nparser"),"K3":(1.1,1.0,"K3 TLS\nparser"),"K5":(2.2,1.0,"K5 SSH/FTP\nparsers"),
        "K7":(3.3,1.0,"K7 scan\nrules"),"K6":(0.0,0.0,"K6 web-attack\nrules"),"K11":(1.1,0.0,"K11 low-conf.\nrules"),"K9":(2.7,0.0,"K9 malware\nrules")}
depgraph(axs[1],"(b) CPU cost (fitted δ ≥ 0.5)",nodes2,[("K1","K2",1.0,"dep"),("K1","K3",0.93,"dep"),("K1","K5",1.0,"dep"),("K1","K7",1.0,"dep"),
        ("K1","K9",0.75,"dep"),("K2","K6",1.0,"dep"),("K2","K11",1.0,"dep")])
save(fig,"fig2_dependencies")

# ---------- Fig 3 reassembly curve ----------
depth=["1 B","512 B","2 KB","8 KB","32 KB","1 MB"]; cpu=[68.0,87.4,91.9,100.9,102.3,114.4]; rec=[0.243,0.259,0.598,0.659,0.659,0.659]
fig,ax=plt.subplots(figsize=(3.5,2.5)); x=np.arange(6)
ax.bar(x,cpu,color="#c9d8e8",edgecolor="#2b5c8a",lw=0.7,label="Processing CPU (s)"); ax.set_ylabel("Processing CPU, Thursday (s)"); ax.set_xticks(x,depth); ax.set_xlabel("Stream reassembly depth (K1)")
ax2=ax.twinx(); ax2.plot(x,rec,"o-",color="#b03030",lw=1.5,label="Macro window recall"); ax2.set_ylim(0,0.75); ax2.set_ylabel("Macro window recall (Thursday)",color="#b03030")
ax2.spines["top"].set_visible(False)
for xi,c in zip(x,cpu): ax.text(xi,c+1.5,f"{c:.0f}",ha="center",fontsize=7)
save(fig,"fig3_reassembly")

# ---------- Fig 4 per-class ----------
cls=["FTP brute force","DoS GoldenEye","DDoS","Web SQL injection","Web XSS","Infiltration–Portscan","DoS Hulk","SSH brute force","Portscan","Infiltration","Botnet","DoS Slowhttptest","Heartbleed","DoS Slowloris","Web brute force"]
win=[1.0,1.0,1.0,1.0,1.0,0.974,0.947,0.484,0.462,0.323,0.220,0.118,0.091,0.0,0.0]
flow=[0.391,0.013,0.008,0.692,1.0,0.006,0.015,0.010,0.001,0.417,0.042,0.001,0.091,0.0,0.0]
fig,ax=plt.subplots(figsize=(7.2,2.8)); y=np.arange(len(cls))
ax.barh(y-0.2,win,0.4,color="#2b5c8a",label="Window recall (primary)"); ax.barh(y+0.2,flow,0.4,color="#d9a441",label="Flow recall")
ax.set_yticks(y,cls,fontsize=7.5); ax.invert_yaxis(); ax.set_xlim(0,1.05); ax.set_xlabel("Recall, full configuration, full week"); ax.legend(loc="lower right",fontsize=7.5,frameon=False)
save(fig,"fig4_per_class")

# ---------- Fig 5 predicted vs measured ----------
res_p,pk_p,p_p,pred_p=F.fit("pre",lambda:F.model_cascade(False),seeds=5)
res_a,pk_a,p_a,pred_a=F.fit("add",F.model_additive,seeds=1)
res_c,pk_c,p_c,pred_c=F.fit("cur",lambda:F.model_cascade(True),seeds=5)
meas=np.array([r["macro"] for r in F.TE])
pa=np.array([pred_a(p_a,r) for r in F.TE]); pp=np.array([pred_p(p_p,r) for r in F.TE])
rows=[l.strip().split("|") for l in open(_os.path.join(DATA, "verify.txt"))]
LV=np.array([[{**{k:1.0 for k in F.CAPS},**json.loads(r[1])}[k] for k in F.CAPS] for r in rows])
vm=np.array([float(r[3]) for r in rows]); vc=np.array([float(r[2]) for r in rows])
def Pcur(L):
    cur=F.curves_from(pk_c,p_c); E=PC.prop(PC.X_of(L,cur),pk_c.get(p_c,"d")); return pk_c.get(p_c,"b0")[0]+E@pk_c.get(p_c,"w")
vp=Pcur(LV); cp=CF.predC(np.load("costC.npy"),LV)
fig,axs=plt.subplots(1,3,figsize=(7.2,2.5))
ax=axs[0]; ax.plot([0.25,0.6],[0.25,0.6],"k:",lw=0.8)
ax.scatter(meas,pa,s=14,marker="x",color="#d9a441",label=f"Additive (MAE {np.mean(abs(pa-meas)):.3f})")
ax.scatter(meas,pp,s=14,color="#2b5c8a",label=f"CASCADE (MAE {np.mean(abs(pp-meas)):.3f})")
ax.set_xlabel("Measured"); ax.set_ylabel("Predicted"); ax.set_title("(a) Held-out detection (40)",fontsize=8.5,loc="left"); ax.legend(fontsize=6.5,frameon=False)
ax=axs[1]; ax.plot([0.25,0.6],[0.25,0.6],"k:",lw=0.8); ax.scatter(vm,vp,s=14,color="#2b5c8a")
ax.set_xlabel("Measured"); ax.set_title(f"(b) Verification detection (25)\nMAE {np.mean(abs(vp-vm)):.3f}",fontsize=8.5,loc="left")
ax=axs[2]; ax.plot([55,115],[55,115],"k:",lw=0.8); ax.scatter(vc,cp,s=14,color="#b03030")
ax.set_xlabel("Measured CPU (s)"); ax.set_ylabel("Predicted CPU (s)"); ax.set_title(f"(c) Verification cost (25)\nMAE {np.mean(abs(cp-vc)):.1f} s, bias {np.mean(cp-vc):+.1f} s",fontsize=8.5,loc="left")
fig.tight_layout(); save(fig,"fig5_predicted_vs_measured")
print("held-out MAE add %.4f pre %.4f; verify det MAE %.4f max %.4f; cost MAE %.2f"%(np.mean(abs(pa-meas)),np.mean(abs(pp-meas)),np.mean(abs(vp-vm)),np.max(abs(vp-vm)),np.mean(abs(cp-vc))))

# ---------- Fig 6 budgets ----------
FULL=112.6
M={"Dependency-aware optimum":{1:(0.579,107.8),.9:(0.575,98.4),.8:(0.575,99.6),.7:(0.562,89.6),.6:(0.432,67.7)},
   "Dependency-unaware optimum":{1:(0.579,83.8),.9:(0.579,83.8),.8:(0.579,83.8),.7:(0.579,94.1),.6:(0.437,81.0),.5:(0.432,61.4),.4:(0.432,64.3)},
   "CASCADE V2 heuristic":{1:(0.575,115.0),.9:(0.579,103.9),.8:(0.575,92.8),.7:(0.558,82.6),.6:(0.432,60.1)},
   "Most expensive first":{1:(0.575,115.0),.9:(0.442,98.2),.8:(0.442,90.8),.7:(0.437,83.2),.6:(0.432,61.9)},
   "Rules first":{1:(0.575,115.0),.9:(0.427,102.3),.8:(0.295,87.3),.7:(0.275,61.4),.6:(0.275,61.4)}}
sty={"Dependency-aware optimum":("o","#2b5c8a"),"Dependency-unaware optimum":("s","#d9a441"),"CASCADE V2 heuristic":("^","#5b9b5b"),"Most expensive first":("v","#8a5c9b"),"Rules first":("D","#b03030")}
fig,axs=plt.subplots(1,2,figsize=(7.2,2.8))
for m,d in M.items():
    b=sorted(d,reverse=True); mk,c=sty[m]
    axs[0].plot([x*100 for x in b],[d[x][0] for x in b],marker=mk,color=c,lw=1.1,ms=4,label=m)
    axs[1].plot([x*100 for x in b],[d[x][1]/FULL*100 for x in b],marker=mk,color=c,lw=1.1,ms=4)
axs[0].set_xlabel("CPU budget (% of full)"); axs[0].set_ylabel("Measured macro window recall"); axs[0].invert_xaxis(); axs[0].set_title("(a) Detection",fontsize=8.5,loc="left")
axs[1].plot([100,40],[100,40],"k:",lw=0.9); axs[1].text(52,45,"budget",fontsize=7,rotation=33)
axs[1].axhline(59.5/FULL*100,color="grey",lw=0.7,ls="--"); axs[1].text(99,54.5,"predicted cost floor (53%)",fontsize=6.5,color="grey")
axs[1].set_xlabel("CPU budget (% of full)"); axs[1].set_ylabel("Measured CPU (% of full)"); axs[1].invert_xaxis(); axs[1].set_title("(b) Cost (above dotted line = over budget)",fontsize=8.5,loc="left")
axs[0].legend(fontsize=6.5,frameon=False,loc="lower left")
fig.tight_layout(); save(fig,"fig6_budgets")
