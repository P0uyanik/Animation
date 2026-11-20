"""T-157: e910 s010 grasp variants from run_shot's resolved scene (written next to it, so package paths resolve).
python3 docs/evaluation/animation/T-157/make_variants.py episodes/e910_showcase/shots/s010/build/shot.resolved.scene.json
t138 = s010 + interaction.graspFit (T-138); a/b/c add boy hand.R.bandFitOptions = (widen lo, off bits, widen hi), metres."""
import json, os, sys

VARIANTS = {
    "t138": None,
    "a": [0.005, 0, 0.005],   # wider band: 45-90 -> 40-95 mm (cup 0-100 mm, open top)
    "b": [0.0, 8, 0.0],       # little finger off the band (bit 3: bone f3 = little in the e910 packages, f0 = index)
    "c": [0.0, 8, 0.005],     # little off + band 45-95 mm
}
src = sys.argv[1]
base = json.load(open(src))
for name, opt in VARIANTS.items():
    s = json.loads(json.dumps(base))
    s["interaction"] = dict(s.get("interaction") or {}, graspFit=True)
    if opt is not None:
        s.setdefault("animation", {})["boy/hand.R.bandFitOptions"] = [[1, opt, "step"]]
    out = os.path.join(os.path.dirname(src), f"t157_{name}.scene.json")
    json.dump(s, open(out, "w"), indent=1)
    print(out)
