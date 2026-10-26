import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
plt.rcParams.update({"font.family":"DejaVu Sans","savefig.dpi":300})
W,H=7.5,7.5/3.35
fig,ax=plt.subplots(figsize=(W,H)); ax.set_xlim(0,W); ax.set_ylim(0,H); ax.axis("off")
steps=[("1. Pilot","#dbe8f6",["Setup checks","Rules fixed","Protocol frozen"],"~70 runs\n(excluded)"),
       ("2. Main study","#d9eedb",["Detection: week","CPU: Thursday ×3","Random order"],"150\nconfigs"),
       ("3. Model fitting","#fbefd0",["Protection model","CPU cost model","Held-out test"],"110 fit +\n40 held out"),
       ("4. Optimisation","#fbe0cc",["Exact search","7 budgets","5 methods"],"1.5 M candidates\n(computed only)"),
       ("5. Verification","#e6e0f3",["Run in Suricata","Detection, CPU","vs. predicted"],"25\nconfigs")]
bw,gap,x0=1.355,0.165,0.03
for i,(t,col,bul,foot) in enumerate(steps):
    x=x0+i*(bw+gap)
    ax.add_patch(FancyBboxPatch((x,0.08),bw,H-0.16,boxstyle="round,pad=0.0,rounding_size=0.08",fc="white",ec="#2b4a6b",lw=1.4))
    ax.add_patch(FancyBboxPatch((x,H-0.46),bw,0.38,boxstyle="round,pad=0.0,rounding_size=0.08",fc=col,ec="#2b4a6b",lw=1.4))
    ax.text(x+bw/2,H-0.27,t,ha="center",va="center",fontsize=8.3,weight="bold")
    y=H-0.62
    for b in bul:
        ax.text(x+0.06,y,"•  "+b,ha="left",va="top",fontsize=7.3,linespacing=1.05); y-=0.27+0.15*b.count("\n")
    ax.add_patch(FancyBboxPatch((x+0.07,0.16),bw-0.14,0.5,boxstyle="round,pad=0.0,rounding_size=0.06",fc="#eef2f7",ec="#9fb2c8",lw=0.9))
    ax.text(x+bw/2,0.41,foot,ha="center",va="center",fontsize=7.0,weight="bold",linespacing=1.1)
    if i<4: ax.annotate("",xy=(x+bw+gap-0.03,H/2),xytext=(x+bw+0.03,H/2),arrowprops=dict(arrowstyle="-|>",lw=1.6,color="#2f6ea3",mutation_scale=12))
fig.savefig("fig1_workflow.png",bbox_inches="tight",pad_inches=0.03); fig.savefig("fig1_workflow.pdf",bbox_inches="tight",pad_inches=0.03)
