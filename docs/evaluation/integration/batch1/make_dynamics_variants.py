"""Integration batch 1: e905 / e906 variants whose girl is built with the T-021 dynamics override (python3).

    python3 docs/evaluation/integration/batch1/make_dynamics_variants.py

The canonical e905 (T-022/T-030) and e906 (T-027) shots cast the girl from her plain spec, so her hair has no spring
chains (T-021 dynamics are opt-in through the girl's dynamics override, used by e904 s010). To check that secondary
motion, the eye/hand fix and the acting clips work together, this writes each shot unchanged apart from that cast
override to <shot dir>/build/batch1_dynamics/shot.scene.json (gitignored), the same way as
episodes/e906_acting_test/make_old_variant.py. The canonical shots stay untouched, so they still compare with the task evidence."""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
OVERRIDE = "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.dynamics.override.json"
SHOTS = ["episodes/e905_props_test/shots/s010", "episodes/e906_acting_test/shots/s010"]

for rel in SHOTS:
    shot = json.load(open(os.path.join(ROOT, rel, "shot.scene.json")))
    cast = shot["production"]["cast"]["girl"]
    cast["overrides"] = list(cast.get("overrides", [])) + [OVERRIDE]
    shot["name"] = shot.get("name", rel) + " [batch1: girl with T-021 dynamics override]"
    out = os.path.join(ROOT, rel, "build", "batch1_dynamics")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "shot.scene.json"), "w") as f:
        json.dump(shot, f, indent=2)
    print(os.path.relpath(os.path.join(out, "shot.scene.json"), ROOT))
