"""Figures for manuscript v1.0 (Computers & Security)."""
import os, json, io, contextlib, numpy as np, pandas as pd, matplotlib
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures", "generated"), exist_ok=True)
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","figures","generated"); RES=os.path.join(HERE,"..","results")
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":8.5,"axes.spines.top":False,"axes.spines.right":False,"savefig.dpi":300})
SUR,SNO="#2b5c8a","#d9a441"
def save(f,n): f.savefig(os.path.join(OUT,n+".png"),bbox_inches="tight"); f.savefig(os.path.join(OUT,n+".pdf"),bbox_inches="tight"); plt.close(f)
def box(ax,x,y,w,h,t,fc="#f4f6f9",ec="#2b4a6b",fs=7.4,bold=False,lw=1.0):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0,rounding_size=0.05",fc=fc,ec=ec,lw=lw))
    ax.text(x+w/2,y+h/2,t,ha="center",va="center",fontsize=fs,weight="bold" if bold else "normal",linespacing=1.15)
def arr(ax,x1,y1,x2,y2,c="#2b4a6b",lw=1.2,ls="-"):
    ax.annotate("",xy=(x2,y2),xytext=(x1,y1),arrowprops=dict(arrowstyle="-|>",lw=lw,color=c,linestyle=ls,mutation_scale=9))
# ---------------- Fig 1 workflow
f,ax=plt.subplots(figsize=(7.3,1.75)); ax.axis("off"); ax.set_xlim(0,7.3); ax.set_ylim(0,1.75)
st=[("1. Pilot","Rules fixed;\nprotocol frozen","#dbe8f6"),
    ("2. Suricata","150 configs:\n110 fit, 40 held out","#d9eedb"),
    ("3. Models","Structural vs.\nadditive and\nstatistical models","#fbefd0"),
    ("4. Configuration","1.5 M candidates;\naudit;\nrobust rules","#fbe0cc"),
    ("5. Verification","56 configs run\nin Suricata\n(phases 5 to 7)","#e6e0f3"),
    ("6. Snort 3","110 configs:\nreplication\n(H7-H9)","#f6dcdc")]
w,g=1.06,0.17
for i,(t,s_,c) in enumerate(st):
    x=0.03+i*(w+g); box(ax,x,0.08,w,1.6,"",fc="white"); box(ax,x,1.3,w,0.38,t,fc=c,bold=True,fs=7.0)
    ax.text(x+w/2,0.7,s_,ha="center",va="center",fontsize=6.6,linespacing=1.25)
    if i<5: arr(ax,x+w+0.01,0.88,x+w+g-0.01,0.88)
save(f,"fig1_workflow")
# ---------------- Fig 2 architecture
f,ax=plt.subplots(figsize=(7.3,3.0)); ax.axis("off"); ax.set_xlim(0,7.3); ax.set_ylim(-0.25,2.95)
for row,(eng,y,items,col) in enumerate([("Suricata 7",1.75,["Packet\ndecoding","Flow\ntracking","Stream\nreassembly\n(depth)","App-layer\nparsers\n(HTTP, TLS, ...)","Sticky buffers\n(http.uri, ...)","Prefilter +\nrule evaluation"],SUR),
                                        ("Snort 3",0.25,["Packet\ndecoding","Flow\ntracking","stream_tcp\n(on / off)","Service\ninspectors\n(http_inspect, ...)","PDU buffers\n(http_uri, ...)","Hyperscan +\nIPS rules"],SNO)]):
    ax.text(0.02,y+0.98,eng,fontsize=8.5,weight="bold",color=col)
    for i,t in enumerate(items):
        x=0.05+i*1.2; hl=i in (2,3,4)
        box(ax,x,y,1.0,0.85,t,fc="#fff4dd" if hl else "#f4f6f9",ec=col,lw=1.4 if hl else 0.9,fs=7.0)
        if i<5: arr(ax,x+1.0,y+0.425,x+1.2,y+0.425,c=col)
ax.text(3.65,-0.12,"rules that need an application buffer stay loaded but never match if any highlighted stage is missing",ha="center",fontsize=7,style="italic")
save(f,"fig2_architecture")
# ---------------- data for Snort
sn=pd.read_csv(os.path.join(RES,"snort_results.csv")); full_sn=sn[sn.levels=="{}"].iloc[0]
su_full={"Botnet":0.220,"DDoS":1.0,"DoS GoldenEye":1.0,"DoS Hulk":0.947,"DoS Slowhttptest":0.118,"DoS Slowloris":0.0,"FTP-Patator":1.0,"Heartbleed":0.091,
 "Infiltration":0.323,"Infiltration - Portscan":0.974,"Portscan":0.462,"SSH-Patator":0.484,"Web Attack - Brute Force":0.0,"Web Attack - SQL Injection":1.0,"Web Attack - XSS":1.0}
# ---------------- Fig 3 per-class
cls=sorted(su_full,key=lambda c:-(su_full[c]+full_sn["W:"+c]))
f,ax=plt.subplots(figsize=(7.3,3.0)); y=np.arange(len(cls))
ax.barh(y-0.2,[su_full[c] for c in cls],0.4,color=SUR,label=f"Suricata 7 (macro {np.mean(list(su_full.values())):.3f})")
ax.barh(y+0.2,[full_sn["W:"+c] for c in cls],0.4,color=SNO,label=f"Snort 3 (macro {full_sn.macro_window_recall:.3f})")
ax.set_yticks(y,cls,fontsize=7.4); ax.invert_yaxis(); ax.set_xlim(0,1.05); ax.set_xlabel("Window recall, full configuration, full week"); ax.legend(loc="lower right",fontsize=7.5,frameon=False)
save(f,"fig3_per_class")
# ---------------- Fig 4 dependencies
f,axs=plt.subplots(1,2,figsize=(7.3,2.5))
lab=["Reassembly ×\nHTTP","Reassembly ×\nweb rules","HTTP ×\nweb rules","Largest\nother pair"]
su=[0.133,0.137,0.137,0.013]; sn_=[0.089,0.085,0.085,0.044]
x=np.arange(4); axs[0].bar(x-0.2,su,0.4,color=SUR,label="Suricata"); axs[0].bar(x+0.2,sn_,0.4,color=SNO,label="Snort")
axs[0].axhline(0.02,ls=":",c="k",lw=0.8); axs[0].text(3.45,0.026,"H7 threshold",fontsize=6.5,ha="right")
axs[0].set_xticks(x,lab,fontsize=7); axs[0].set_ylabel("Interaction (macro window recall)"); axs[0].set_title("(a) Pairwise interactions",fontsize=8.5,loc="left"); axs[0].legend(fontsize=7,frameon=False)
d_su=[0.92,0.94]; d_sn=[0.96,0.95]; x=np.arange(2)
axs[1].bar(x-0.2,d_su,0.4,color=SUR,label="Suricata"); axs[1].bar(x+0.2,d_sn,0.4,color=SNO,label="Snort")
axs[1].axhline(0.5,ls=":",c="k",lw=0.8); axs[1].text(1.45,0.53,"H1/H9 threshold",fontsize=6.5,ha="right")
axs[1].set_xticks(x,["Reassembly → HTTP","HTTP → web rules"],fontsize=7.5); axs[1].set_ylim(0,1.1); axs[1].set_ylabel("Fitted dependency strength d")
axs[1].set_title("(b) Fitted dependencies (pre-registered form)",fontsize=8.5,loc="left")
f.tight_layout(); save(f,"fig4_dependencies")
# ---------------- Fig 5 predicted vs measured
import fit as F
buf=io.StringIO()
with contextlib.redirect_stdout(buf):
    _,pkc,pc,predc=F.fit("c",lambda:F.model_cascade(True),seeds=5); _,pka,pa,preda=F.fit("a",F.model_additive,seeds=1)
    import importlib.util; sp=importlib.util.spec_from_file_location("sa","snort_analysis.py"); sa=importlib.util.module_from_spec(sp); sp.loader.exec_module(sa)
m=np.array([r["macro"] for r in F.TE]); pcu=np.array([predc(pc,r) for r in F.TE]); pad=np.array([preda(pa,r) for r in F.TE])
CAPS=F.CAPS
def lv(js): d={k:1.0 for k in CAPS}; d.update({k:float(v) for k,v in json.loads(js).items()}); return d
rows=[l.strip().split("|") for l in open(os.path.join(RES,"verify.txt"))]
vm=[float(r[3]) for r in rows]; vp=[predc(pc,{"levels":lv(r[1])}) for r in rows]
for l in open(os.path.join(RES,"verify2.txt")):
    if l.startswith("#"): continue
    r=l.strip().split("|")
    if r[1]=="new": vm.append(float(r[4])); vp.append(predc(pc,{"levels":lv(r[6])}))
for l in open(os.path.join(RES,"verify3.txt")):
    if l.startswith("#"): continue
    r=l.strip().split("|")
    if r[1]!="reference" and "anchor" not in r[1]: vm.append(float(r[4])); vp.append(predc(pc,{"levels":lv(r[6])}))
f,axs=plt.subplots(1,3,figsize=(7.3,2.45))
def sc(ax,meas,preds,title):
    lo=min(min(meas),min(min(p) for _,p,_,_ in preds))-0.02; hi=max(max(meas),max(max(p) for _,p,_,_ in preds))+0.02
    ax.plot([lo,hi],[lo,hi],"k:",lw=0.8)
    for nm,p,c,mk in preds: ax.scatter(meas,p,s=12,color=c,marker=mk,label=f"{nm} (MAE {np.mean(np.abs(np.array(p)-np.array(meas))):.3f})")
    ax.set_title(title,fontsize=8,loc="left"); ax.set_xlabel("Measured"); ax.legend(fontsize=6,frameon=False,loc="upper left")
sc(axs[0],m,[("additive",pad,"#bbbbbb","x"),("structural",pcu,SUR,"o")],"(a) Suricata, 40 held-out")
pe=sa.res; snm=sa.yte; sc(axs[1],snm,[("additive",pe["additive"]+snm,"#bbbbbb","x"),("structural",pe["CASCADE with level curves"]+snm,SNO,"o")],"(b) Snort, 25 held-out")
sc(axs[2],vm,[("structural",vp,SUR,"o")],f"(c) Suricata, {len(vm)} optimised (verified)")
axs[0].set_ylabel("Predicted macro window recall"); f.tight_layout(); save(f,"fig5_predicted_vs_measured")
print("verified n",len(vm),"MAE",round(np.mean(np.abs(np.array(vp)-np.array(vm))),4))
# ---------------- Fig 7 phase 6
p6={(90,"plain"):(0.575,88.9),(90,"tie"):(0.572,77.6),(90,"chance"):(0.575,85.6),(90,"chance+tie"):(0.572,77.6),
    (80,"plain"):(0.575,83.2),(80,"tie"):(0.569,77.6),(80,"chance"):(0.575,77.0),(80,"chance+tie"):(0.569,76.4),
    (70,"plain"):(0.562,74.2),(70,"tie"):(0.558,75.6),(70,"chance"):(0.437,70.8),(70,"chance+tie"):(0.431,70.6),
    (60,"plain"):(0.432,59.3),(60,"tie"):(0.424,55.4),(60,"chance"):(0.426,56.4),(60,"chance+tie"):(0.424,54.9)}
rules=["plain","tie","chance","chance+tie"]; cols=["#888888",SUR,"#5b9b5b","#8a5c9b"]; B=[90,80,70,60]
f,axs=plt.subplots(1,2,figsize=(7.3,2.6)); w=0.2
for j,(r,c) in enumerate(zip(rules,cols)):
    xs=np.arange(4)+(j-1.5)*w
    axs[0].bar(xs,[p6[(b,r)][1]-b for b in B],w,color=c,label=r)
    axs[1].bar(xs,[p6[(b,r)][0] for b in B],w,color=c,label=r)
axs[0].axhline(0,c="k",lw=0.8); axs[0].set_xticks(range(4),[f"{b}%" for b in B]); axs[0].set_ylabel("Measured CPU minus budget (points)")
axs[0].set_title("(a) Budget compliance (above 0 = over budget)",fontsize=8,loc="left"); axs[0].legend(fontsize=6.5,frameon=False,ncol=2)
axs[1].set_xticks(range(4),[f"{b}%" for b in B]); axs[1].set_ylim(0.38,0.6); axs[1].set_ylabel("Measured macro window recall"); axs[1].set_title("(b) Detection",fontsize=8,loc="left")
for a in axs: a.set_xlabel("CPU budget")
f.tight_layout(); save(f,"fig7_robust_selection")
