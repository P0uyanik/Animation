#!/usr/bin/env python3
"""T-163 gate check (plain python, no engine build): prop JSON is current, structurally valid and follows the cup
conventions. The engine-side verb tests (pick up / carry / place per prop) are tests/props/test_prop_verbs.cpp
(see tests/props/CMakeLists.txt)."""
import json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
NEW = ["bowl", "plate", "spoon", "book", "ball", "box", "box_lid", "toy", "apple", "pencil", "block", "basket"]
fails = []

def check(ok, msg):
    if not ok: fails.append(msg)

r = subprocess.run([sys.executable, str(ROOT / "tests/props/make_props.py"), "--check"], capture_output=True, text=True)
check(r.returncode == 0, f"assets differ from make_props.py: {r.stdout.strip()}")
check(10 <= len(NEW) + 1 <= 15, "library size must be 10-15")
for n in NEW + ["cup"]:
    a = json.loads((ROOT / f"content/assets/felt_{n}.asset.json").read_text())
    af, sk = a["affordances"], a["sockets"]
    check(a["id"] == f"prop.felt_{n}" and a["material_presets"] == ["felt"], f"{n}: id/material")
    check({"place", "contact"} <= set(sk), f"{n}: place/contact sockets")
    sites = {s["id"]: s for s in af["grasp_sites"]}
    check(all(s["socket"] in sk for s in sites.values()), f"{n}: site socket missing")
    check(all(x in sites for st in af["grasp_sets"] for x in st["sites"]), f"{n}: set site missing")
    sets = {s["id"] for s in af["grasp_sets"]}
    ho = af.get("handover", {})
    check(all(x in sets for x in ho.get("give", []) + ho.get("receive", [])), f"{n}: handover set missing")
    check(af["deform"]["mode"] == "rigid", f"{n}: must be rigid (verbs reject others)")
    check(af["place"]["socket"] in sk, f"{n}: place socket")
    if af["hands"] == "two":
        check(any(len(s["sites"]) == 2 for s in af["grasp_sets"]), f"{n}: two-hand set")
lid, box = (json.loads((ROOT / f"content/assets/felt_{n}.asset.json").read_text()) for n in ("box_lid", "box"))
d = box["sockets"]["lid_seat"]["translation"][1] - lid["sockets"]["place"]["translation"][1]
check(abs(d - (box["mesh"]["size"][1] / 2 + lid["mesh"]["size"][1] / 2)) < 1e-6, "lid does not seat on the box")
print("FAIL: " + "; ".join(fails) if fails else f"props ok ({len(NEW)} new + felt_cup)")
sys.exit(1 if fails else 0)
