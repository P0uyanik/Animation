"""T-185 (B): e909 variants for the girl's left-hand pick-up (set b = site side_b), from run_shot's resolved scene.
Each variant gets its own folder under <repo>/build/t185/<tag>/<variant>/ with a copy of content/assets (the engine and
shot_render.py take the nearest content/assets above the scene), so the cup can differ per variant.
    python3 docs/evaluation/interaction/T-185/e909_variants.py <shot.resolved.scene.json> <tag> [variant ...]
  base     the shot as it is (fingerClose removed if present; released cup)
  r3keys   fingerClose = T-171 R3 (rest, wrap, grip natural, clear 0.006) on pick_up / pass / place; released cup
  r3site   r3keys + T-171's proposed cup site (side_a: socket grip y 0.05, band 0-0.1): the boy's receiving side
  r3siteb  r3site + the same centring for side_b (socket grip_b y 0.05, band 0-0.1): the girl's side (new, unmeasured
           by T-171: the mirror of its proposal)"""
import importlib.util, json, os, shutil, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
spec = importlib.util.spec_from_file_location("e910_make_shot", os.path.join(ROOT, "episodes", "e910_showcase", "make_shot.py"))
e910 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e910)  # R3 only (main() runs under __main__ only)
R3 = e910.R3
VERBS = ("pick_up", "pass", "place")
SITES = {"base": {}, "r3keys": {}, "r3site": {"grip": ("side_a", 0.05)},
         "r3siteb": {"grip": ("side_a", 0.05), "grip_b": ("side_b", 0.05)}}


def make(src, tag, name):
    s = json.load(open(src))
    for a in s["actions"]:
        a.pop("fingerClose", None)
        if name != "base" and a.get("type") in VERBS:
            a["fingerClose"] = json.loads(json.dumps(R3))
    s.pop("x_t185", None)
    for c in s["characters"]:
        if not os.path.isabs(c["asset"]):
            c["asset"] = os.path.abspath(os.path.join(os.path.dirname(src), c["asset"]))
    d = os.path.join(ROOT, "build", "t185", tag, name)
    shutil.rmtree(os.path.join(d, "content"), ignore_errors=True)
    shutil.copytree(os.path.join(ROOT, "content", "assets"), os.path.join(d, "content", "assets"))
    cup = os.path.join(d, "content", "assets", "felt_cup.asset.json")
    a = json.load(open(cup))
    for sock, (site, y) in SITES[name].items():
        a["sockets"][sock]["translation"][1] = y
        next(g for g in a["affordances"]["grasp_sites"] if g["id"] == site)["fingers"]["band"] = [0.0, 0.1]
    json.dump(a, open(cup, "w"), indent=1)
    out = os.path.join(d, "scene.json")
    json.dump(s, open(out, "w"), indent=1)
    return out


if __name__ == "__main__":
    for n in sys.argv[3:] or list(SITES):
        print(make(sys.argv[1], sys.argv[2], n))
