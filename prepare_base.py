#!/usr/bin/env python3
"""Create the frozen base suricata.yaml for the study (run once, then hash it).

Changes from the Ubuntu default: HOME_NET is the protected network (CIC-IDS2017 victim
LAN 192.168.10.0/24 by default, so the NAT address 172.16.0.1 that carries the external
attacks counts as external); only alerts + end-of-run stats are logged; rule path is
supplied per run. Everything else stays default.
"""
import argparse, yaml, hashlib

ap = argparse.ArgumentParser()
ap.add_argument("src", nargs="?", default="/etc/suricata/suricata.yaml")
ap.add_argument("dst", nargs="?", default="/data/config/base_suricata.yaml")
ap.add_argument("--home-net", default="[192.168.10.0/24]",
                help="protected network; CIC-IDS2017 victim LAN by default")
ap.add_argument("--external-net", default="!$HOME_NET")
a = ap.parse_args()
src, dst = a.src, a.dst

cfg = yaml.safe_load(open(src).read().split("---", 1)[1])
outs = []
for o in cfg["outputs"]:
    name = next(iter(o))
    if name == "eve-log":
        o[name].update({"enabled": "yes", "filename": "eve.json",
                        "types": [{"alert": {"tagged-packets": "no"}}, {"stats": {"totals": "yes", "threads": "no", "deltas": "no"}}]})
    else:
        if isinstance(o[name], dict):
            o[name]["enabled"] = "no"
    outs.append(o)
cfg["outputs"] = outs
cfg["stats"] = {"enabled": "yes", "interval": 3600}   # final stats are written at shutdown in offline mode
cfg["vars"]["address-groups"]["HOME_NET"] = a.home_net
cfg["vars"]["address-groups"]["EXTERNAL_NET"] = a.external_net
cfg["default-rule-path"] = "/tmp"
cfg["rule-files"] = []

text = "%YAML 1.1\n---\n" + yaml.safe_dump(cfg, sort_keys=False)
open(dst, "w").write(text)
print(dst, hashlib.sha256(text.encode()).hexdigest())
