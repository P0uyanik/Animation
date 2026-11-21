"""T-171: e910 s010 variants from run_shot's resolved scene (written next to it, so package paths resolve).
python3 docs/evaluation/interaction/T-171/make_variants.py <shot.resolved.scene.json> [name ...]
Each variant adds the opt-in action key "fingerClose" to the verbs of the shot (pick_up, pass, place) and, where it
names one, authored rest-hand tracks for hands that never grasp."""
import json, os, sys

# The separated rest hand: a curl cascade index -> little and a light fan, so neighbouring fingers do not line up.
SEP = {"rest": {"curl": 0.25, "thumb": 0.12, "spread": 0.6, 
                "fingers": {"index": {"curl": 0.14, "spread": 0.9}, "middle": {"curl": 0.22, "spread": 0.6}, "ring": {"curl": 0.29, "spread": 0.6}, "little": {"curl": 0.35, "spread": 0.9}}}}
VARIANTS = {
    "base": None,                                             # current default (released behaviour)
    "t157a": {"_plain": True, "widen": [0.005, 0.005]},       # T-157 (a) alone: old timing, band 40-95 mm
    "r2": {},                                                 # pre-shape + stagger 2 + soft landing, site band as is
    "r2a": {"widen": [0.005, 0.005]},                         # + T-157 (a)
    "r2s": dict(SEP, widen=[0.005, 0.005]),                   # r2a + the separated rest hand
}


def variant(base, name):
    opt = VARIANTS[name]
    s = json.loads(json.dumps(base))
    if opt is None:
        return s
    opt = dict(opt)
    if opt.pop("_plain", False):  # the T-157 route: graspFit + authored options track, nothing of T-171
        s["interaction"] = dict(s.get("interaction") or {}, graspFit=True)
        w = opt["widen"]
        s.setdefault("animation", {})["boy/hand.R.bandFitOptions"] = [[1, [w[0], 0, w[1]], "step"]]
        return s
    for a in s["actions"]:
        if a.get("type") in ("pick_up", "pass", "place"):
            a["fingerClose"] = opt if opt else True
    return s


# Round 3 (owner review 2026-11-21): the fixed opt-in on the proposed cup site. wrap = joint-by-joint finger wrap with
# the measured skin and the seated palm; grip natural = thumb up (the grasp point turns about the cup's axis).
R3 = dict(SEP, wrap=True, grip="natural", clear=0.006)
# r3site: the same without the turn (the authored grasp point: the planner turns the right hand thumb down there).
SITE_VARIANTS = {"r2site": dict(SEP), "r3": R3, "r3site": dict(SEP, wrap=True, clear=0.006)}


def site_variant(src, base, root, name="r2site"):
    """A variant on a copy of the prop library whose felt_cup site side_a is the PROPOSED one (hand centred on the
    cup: socket grip at 50 mm instead of 66, band 0-100 mm instead of 45-90). The copy lives under the build folder;
    content/assets is not changed. r2site = r2s there; r3 / r3site = the round 3 fixes on top."""
    import shutil
    d = os.path.join(os.path.dirname(src), "t171_site")
    for sub in ("assets", "hand_shapes"):
        shutil.rmtree(os.path.join(d, "content", sub), ignore_errors=True)
        shutil.copytree(os.path.join(root, "content", sub), os.path.join(d, "content", sub))
    cup = os.path.join(d, "content", "assets", "felt_cup.asset.json")
    a = json.load(open(cup))
    a["sockets"]["grip"]["translation"][1] = 0.05
    for g in a["affordances"]["grasp_sites"]:
        if g["id"] == "side_a":
            g["fingers"]["band"] = [0.0, 0.1]
    json.dump(a, open(cup, "w"), indent=1)
    s = variant(base, "r2")
    for act in s["actions"]:
        if "fingerClose" in act:
            act["fingerClose"] = dict(SITE_VARIANTS[name])
    for c in s["characters"]:  # package paths are relative to the scene file
        if not os.path.isabs(c["asset"]):
            c["asset"] = os.path.abspath(os.path.join(os.path.dirname(src), c["asset"]))
    out = os.path.join(d, f"t171_{name}.scene.json")
    json.dump(s, open(out, "w"), indent=1)
    return out


if __name__ == "__main__":
    src = sys.argv[1]
    base = json.load(open(src))
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    for name in sys.argv[2:] or list(VARIANTS) + list(SITE_VARIANTS):
        if name in SITE_VARIANTS:
            print(site_variant(src, base, root, name))
            continue
        out = os.path.join(os.path.dirname(src), f"t171_{name}.scene.json")
        json.dump(variant(base, name), open(out, "w"), indent=1)
        print(out)
