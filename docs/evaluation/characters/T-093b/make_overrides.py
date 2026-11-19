"""T-093b: candidate overrides on top of the T-093 garment/2 candidates (read-only), written to
candidates/T-093b/. The spec merger replaces arrays, so each override carries the whole clothing list of the T-093
candidate with only the fields below changed.

    python3 docs/evaluation/characters/T-093b/make_overrides.py

boy  <id>.T-093b-T090b.override.json   T-093 + the T-090b boy trousers/shoes proposal (5 numeric paths from
                                        docs/evaluation/characters/T-090b/boy-garments/bounds.json, values from its
                                        proposal.json). A candidate only: kept or dropped on the strict sheet.
girl <id>.T-093b.override.json         T-093 + the opt-in crotch arch of `leg_split` (garment/2) and the
                                        sleeve/shorts values from the T-093b fit (FIT below).
Combined looks (T-092 presets/3 on top) are written by make_combined.py next to this file."""
import copy
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
CH = os.path.join(ROOT, "assets", "characters")
T090B = os.path.join(ROOT, "docs", "evaluation", "characters", "T-090b")

# T-093b fit (tools/fit + garment_score.py, fit/girl/): winning values, see README.md
FIT = {"clothing.garments.0.sleeve_puff_m": 0.0321,   # round 3 trial 3 (sleeve length stays 1.0: rounds 1-2)
       "clothing.garments.2.puff_m": 0.038}            # round 3 trial 3: fuller legs (sheet30 front/3/4)
# crotch arch: round 3 trial 3 had lift 0.168 (still one band on the sheet); 0.3 with the smoothstep falloff is the
# visual choice and scores higher (fit/girl5, garment 51.66 vs trial 3 51.54 and T-093 50.15)
GIRL_ARCH = {"crotch_lift": 0.3, "arch_width": 0.7, "arch_power": 1.0}


def t093(cid):
    path = os.path.join(CH, cid, "spec", "candidates", "T-093", f"{cid}.T-093.override.json")
    return json.load(open(path))["override"]


def get(doc, dotted):
    for k in dotted.split("."):
        doc = doc[int(k)] if isinstance(doc, list) else doc[k]
    return doc


def put(doc, dotted, value):
    keys = dotted.split(".")
    for k in keys[:-1]:
        doc = doc[int(k)] if isinstance(doc, list) else doc[k]
    doc[int(keys[-1]) if isinstance(doc, list) else keys[-1]] = value


def write(cid, name, override, note):
    out = os.path.join(CH, cid, "spec", "candidates", "T-093b")
    os.makedirs(out, exist_ok=True)
    override = copy.deepcopy(override)
    override.setdefault("metadata", {})["notes"] = note
    path = os.path.join(out, name)
    with open(path, "w") as f:
        json.dump({"override": override}, f, indent=1)
        f.write("\n")
    print(path)


def boy():
    cid = "boy_yellow_hoodie"
    o = t093(cid)
    bounds = json.load(open(os.path.join(T090B, "boy-garments", "bounds.json")))
    prop = json.load(open(os.path.join(T090B, "boy-garments", "proposal.json")))
    names = [g["name"] for g in o["clothing"]["garments"]]
    pnames = [g["name"] for g in prop["clothing"]["garments"]]
    changed = []
    for path in bounds:  # indices are the garment/1 list; map by garment name
        parts = path.split(".")
        name = pnames[int(parts[2])]
        mine = ".".join(parts[:2] + [str(names.index(name))] + parts[3:])
        put(o, mine, get(prop, path))
        changed.append(f"{name}.{'.'.join(parts[3:])}={get(prop, path):.4g}")
    write(cid, f"{cid}.T-093b-T090b.override.json", o,
          "T-093b candidate (unpublished): T-093 garment/2 candidate with the T-090b trousers/shoes fit values ("
          + ", ".join(changed) + "). Never publish or approve without an owner decision.")


def girl():
    cid = "girl_auburn_bun_glasses"
    o = t093(cid)
    sh = next(g for g in o["clothing"]["garments"] if g["name"] == "shorts")
    # the crotch arch (T-093b): the hem rises into an inverted V at the front/back centre, so the bloomers read as
    # two legs (sheet30 front, G08); without it the shell's crotch bridge spans the gap as one band
    sh["leg_split"] = dict(sh["leg_split"], **GIRL_ARCH)
    for path, value in FIT.items():
        if value is not None:
            put(o, path, value)
    write(cid, f"{cid}.T-093b.override.json", o,
          "T-093b candidate (unpublished): T-093 garment/2 candidate with the leg_split crotch arch and the T-093b "
          "sleeve/shorts fit. Never publish or approve without an owner decision.")


if __name__ == "__main__":
    boy()
    girl()
