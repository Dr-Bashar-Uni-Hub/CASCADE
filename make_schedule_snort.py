"""Frozen Snort 3 main-study schedule (protocol amendment v1.4)."""
import itertools, json, random, sys
LEVELS = {"K1": [0, 1], "K2": [0, 1], "K3": [0, 1], "K4": [0, 1], "K5": [0, 1]}
for k in ["K6", "K7", "K8", "K9", "K10", "K11"]:
    LEVELS[k] = [0, 0.25, 0.5, 0.75, 1]
CAPS = list(LEVELS); SEED = 20261019
key = lambda lv: tuple(sorted(lv.items()))
ph = {1: [{"levels": {}, "extra_cost_reps": 4}], 2: [], 3: [], 4: []}
for k in CAPS:
    for v in LEVELS[k][:-1]:
        ph[2].append({"levels": {k: v}})
for a, b in itertools.combinations(CAPS, 2):
    ph[3].append({"levels": {a: 0, b: 0}})
seen = {key(c["levels"]) for p in (1, 2, 3) for c in ph[p]}
rv = random.Random(20261029)
while len(ph[4]) < 25:
    lv = {k: rv.choice(LEVELS[k]) for k in CAPS}
    lv = {k: v for k, v in lv.items() if v != 1}
    if key(lv) not in seen:
        seen.add(key(lv)); ph[4].append({"levels": lv, "held_out": True})
ro = random.Random(20261030); items = []; n = 0; nr = 0
for p in (1, 2, 3, 4):
    cf = ph[p][:]; ro.shuffle(cf)
    for c in cf:
        if n % 10 == 0:
            nr += 1; items.append({"id": f"SR{nr:02d}", "type": "reference", "levels": {}, "rule_seed": SEED})
        n += 1
        items.append({"id": f"SC{n:03d}", "type": "config", "phase": p, "held_out": c.get("held_out", False),
                      "levels": c["levels"], "rule_seed": SEED, "extra_cost_reps": c.get("extra_cost_reps", 2)})
out = sys.argv[1] if len(sys.argv) > 1 else "snort_schedule.json"
json.dump({"protocol": "CASCADE-IDS protocol v1.4: Snort 3 replication", "engine": "snort", "levels": LEVELS,
           "seeds": {"rule": SEED, "validation": 20261029, "order": 20261030},
           "counts": {f"phase{p}": len(ph[p]) for p in ph} | {"references": nr}, "items": items}, open(out, "w"), indent=1)
print(out, {f"phase{p}": len(ph[p]) for p in ph}, "references", nr, "items", len(items))
