"""R3 faces bundle: stack the approved overrides onto the T-155 candidate specs (no version, no current change).

Order per character: T-159 temple (girls) -> T-159 ears -> T-159 glasses (auburn) -> T-168 face (boy) -> T-167 hair
-> T-156 eyes/lids (girls, t-156-claude-eye-targets@6b3ddf4). Each layer's `override` block is deep-merged (spec.deep_merge: dicts
recursive, lists replaced whole). The script reports every key path written by more than one layer, and every list
that a layer replaces, so a later layer cannot silently drop an earlier one.
Usage (repo root): python3 docs/evaluation/characters/R3/stack_specs.py [--check]
Writes docs/evaluation/characters/R3/specs/<id>.<ver>.spec.json (not under assets/: the opt-in guards forbid the new
options in asset specs until the release step) and docs/evaluation/characters/R3/stack_report.json.
"""
import copy, json, sys
from pathlib import Path
sys.path.insert(0, "pipeline/charsys")
from spec import deep_merge  # noqa: E402

E, A = "docs/evaluation/characters", "assets/characters"
O159, O167, O156 = f"{E}/T-159/overrides", f"{E}/T-167/overrides", f"{E}/T-156"
JOBS = {
    "boy_yellow_hoodie": ("2.3.0", [f"{O159}/boy_ears.json", f"{E}/T-168/boy_yellow_hoodie.T-168.override.json",
                                    f"{O167}/boy_yellow_hoodie.hair_r6.override.json"]),
    "girl_auburn_bun_glasses": ("0.14.0", [f"{O159}/girl_auburn_bun_glasses.temple.override.json",
                                           f"{O159}/girl_ears.json", f"{O159}/girl_glasses.json",
                                           f"{O167}/girl_auburn_bun_glasses.hair_r7.override.json",
                                           f"{O156}/auburn/girl_auburn_bun_glasses.eyes.override.json"]),
    "girl_white_hair_blue_dress": ("0.1.0", [f"{O159}/girl_white_hair_blue_dress.temple.override.json",
                                             f"{O159}/third_ears.json",
                                             f"{O167}/girl_white_hair_blue_dress.hair_r7.override.json",
                                             f"{O156}/third/girl_white_hair_blue_dress.eyes.override.json"]),
}


def leaves(d, p=()):
    """Key paths a merge of d writes (a list or scalar is one leaf)."""
    if isinstance(d, dict) and d:
        for k, v in d.items():
            yield from leaves(v, p + (k,))
    else:
        yield p


def get(d, p):
    for k in p:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


report = {}
for cid, (ver, layers) in JOBS.items():
    spec = json.loads(Path(f"{A}/{cid}/spec/candidates/T-155/{cid}.{ver}.spec.json").read_text())
    writers, lists, rows = {}, [], []
    for f in layers:
        d = json.loads(Path(f).read_text())
        ov = d.get("override", {k: v for k, v in d.items() if k != "note"})
        before = copy.deepcopy(spec)
        for p in leaves(ov):
            writers.setdefault(p, []).append(Path(f).name)
            new, old = get(ov, p), get(before, p)
            if isinstance(new, list):
                lists.append({"layer": Path(f).name, "path": ".".join(p), "old_len": None if old is None else len(old),
                              "new_len": len(new), "same": old == new})
        spec = deep_merge(spec, ov)
        rows.append({"layer": f, "changed_leaves": sum(get(before, p) != get(ov, p) for p in leaves(ov))})
    clashes = {".".join(p): w for p, w in writers.items() if len(w) > 1}
    # also catch a later layer writing a parent/child of an earlier layer's path
    for p, w in writers.items():
        for q, v in writers.items():
            if p != q and p == q[:len(p)] and set(w) != set(v):
                clashes[".".join(q) + " under " + ".".join(p)] = v + w
    spec.setdefault("metadata", {})
    spec["metadata"] = {**spec["metadata"], "candidate": "R3 faces bundle (integration/r3-faces)",
                        "layers": ["T-155 candidate"] + layers}
    out = Path(f"{E}/R3/specs/{cid}.{ver}.spec.json")  # outside assets/: the opt-in guards stay as they are
    if "--check" not in sys.argv:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(spec, indent=1, sort_keys=False) + "\n")
    report[cid] = {"out": str(out), "layers": rows, "clashes": clashes, "lists_replaced": lists}
Path(f"{E}/R3/stack_report.json").write_text(json.dumps(report, indent=1) + "\n")
print(json.dumps({c: {"clashes": r["clashes"], "lists": [l for l in r["lists_replaced"] if not l["same"]]}
                  for c, r in report.items()}, indent=1))
