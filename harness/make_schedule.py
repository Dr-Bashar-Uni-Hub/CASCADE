#!/usr/bin/env python3
"""Generate the frozen main-study schedule (protocol v1.0, phases 1-4).

Phase 1  baseline: full configuration (4 extra cost repeats)
Phase 2  single-factor: each capability at each lower level, others full;
         rule capabilities K6-K11 also at level 0.5 with two extra rule seeds
Phase 3  pairwise: all 55 pairs with both at level 0, plus 9 hypothesized edges at middle levels
Phase 4  validation: 40 random configurations (seed 20261020), held out from model fitting
Order: phases in sequence, random order within each phase (seed 20261021); a full-configuration
reference cost run is inserted before every 10th configuration.

Usage: python3 make_schedule.py [out.json]
"""
import itertools, json, random, sys

LEVELS = {"K1": [0, 0.2, 0.4, 0.6, 0.8, 1], "K2": [0, 1], "K3": [0, 1], "K4": [0, 1], "K5": [0, 1]}
for k in ["K6", "K7", "K8", "K9", "K10", "K11"]:
    LEVELS[k] = [0, 0.25, 0.5, 0.75, 1]
CAPS = list(LEVELS)
RULE_CAPS = ["K6", "K7", "K8", "K9", "K10", "K11"]
SEED_MAIN, EXTRA_SEEDS = 20261019, [20261119, 20261219]
# hypothesized edges (parent, child) from protocol section 4, with middle levels for phase 3b
EDGES_MID = [({"K1": 0.4}, {"K2": 0}), ({"K1": 0.4}, {"K3": 0}), ({"K1": 0.4}, {"K5": 0}),
             ({"K1": 0.4}, {"K8": 0.5}), ({"K2": 0}, {"K6": 0.5}), ({"K3": 0}, {"K8": 0.5}),
             ({"K2": 0}, {"K9": 0.5}), ({"K3": 0}, {"K9": 0.5}), ({"K4": 0}, {"K9": 0.5})]


def key(levels, seed):
    return (tuple(sorted(levels.items())), seed)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "main_schedule.json"
    phases = {1: [], 2: [], 3: [], 4: []}
    phases[1].append({"levels": {}, "rule_seed": SEED_MAIN, "extra_cost_reps": 4})
    for k in CAPS:
        for lv in LEVELS[k][:-1]:
            phases[2].append({"levels": {k: lv}, "rule_seed": SEED_MAIN})
    for k in RULE_CAPS:
        for s in EXTRA_SEEDS:
            phases[2].append({"levels": {k: 0.5}, "rule_seed": s})
    for a, b in itertools.combinations(CAPS, 2):
        phases[3].append({"levels": {a: 0, b: 0}, "rule_seed": SEED_MAIN})
    for p, c in EDGES_MID:
        phases[3].append({"levels": {**p, **c}, "rule_seed": SEED_MAIN})

    seen = {key(c["levels"], c["rule_seed"]) for ph in (1, 2, 3) for c in phases[ph]}
    rv = random.Random(20261020)
    while len(phases[4]) < 40:
        lv = {k: rv.choice(LEVELS[k]) for k in CAPS}
        lv = {k: v for k, v in lv.items() if v != 1}            # level 1 = default, omitted
        if key(lv, SEED_MAIN) not in seen:
            seen.add(key(lv, SEED_MAIN))
            phases[4].append({"levels": lv, "rule_seed": SEED_MAIN, "held_out": True})

    ro = random.Random(20261021)
    items, n_cfg, n_ref = [], 0, 0
    for ph in (1, 2, 3, 4):
        cfgs = phases[ph][:]
        ro.shuffle(cfgs)
        for c in cfgs:
            if n_cfg % 10 == 0:
                n_ref += 1
                items.append({"id": f"R{n_ref:03d}", "type": "reference", "levels": {}, "rule_seed": SEED_MAIN})
            n_cfg += 1
            items.append({"id": f"C{n_cfg:03d}", "type": "config", "phase": ph,
                          "held_out": c.get("held_out", False), "levels": c["levels"],
                          "rule_seed": c["rule_seed"], "extra_cost_reps": c.get("extra_cost_reps", 2)})
    sched = {"protocol": "CASCADE-IDS Measurement Protocol v1.0", "levels": LEVELS,
             "seeds": {"rule_main": SEED_MAIN, "rule_extra": EXTRA_SEEDS, "validation": 20261020, "order": 20261021},
             "counts": {f"phase{p}": len(phases[p]) for p in phases} | {"references": n_ref},
             "items": items}
    json.dump(sched, open(out, "w"), indent=1)
    print(out, sched["counts"], "items:", len(items))


if __name__ == "__main__":
    main()
