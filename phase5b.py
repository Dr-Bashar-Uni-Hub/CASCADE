"""Phase 5b (exploratory): re-measurement against matched references and safety-margin verification."""
import os, json, statistics as st
DATA = os.environ.get("CASCADE_DATA", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results"))
rows = [l.strip().split("|") for l in open(os.path.join(DATA, "verify2.txt")) if not l.startswith("#")]
v1 = {l.split("|")[0]: float(l.split("|")[2]) for l in open(os.path.join(DATA, "verify.txt"))}
ref = st.mean(float(r[3]) for r in rows if r[1] == "ref")
print(f"re-measurement reference mean {ref:.1f} s ({ref/112.6-1:+.1%} vs main study)")
for r in rows:
    if r[1] == "ref": continue
    pct = float(r[3]) / ref * 100
    extra = f"  phase 5: {v1[r[1]]:.1f} s -> {float(r[3]):.1f} s ({float(r[3])/v1[r[1]]-1:+.1%})" if r[1] in v1 else f"  recall {float(r[4]):.3f}"
    print(f"{r[0]} {r[1]:>4}  {pct:5.1f}% of full{extra}")
