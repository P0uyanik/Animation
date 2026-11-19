"""T-126c: renders of the baked skirt simulation next to the build's skinned skirt, same pose, camera and light.

    blender -b --factory-startup -P docs/evaluation/characters/T-126/dress/sim_evidence.py -- <master.blend>
        <dir with <motion>.pc2 from pipeline/charsys/cloth_sim/run.py> <out dir> [--samples 16] [--px 360] [--seed 126]

Per motion (walk, sit, kneel) the master is opened, the simulation proxy is rebuilt with the same seed, the PC2 bake
is replayed (no simulation here) and each evidence frame is rendered twice: ``<frame>.simulated.png`` and
``<frame>.skinned.png``. The seat of the sit motion is a collision prop and is not rendered."""
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys", "cloth_sim"))
sys.path.insert(0, HERE)
import run as R  # noqa: E402
import shots as SH  # noqa: E402
import skirt as S  # noqa: E402

CAMS = {"walk": ((0.0, 0.0, 0.30), 0.62, 55.0, 6.0), "sit": ((0.0, -0.05, 0.30), 0.62, 60.0, 8.0),
        "kneel": ((0.0, 0.05, 0.30), 0.62, 70.0, 6.0)}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    blend, bakes, out = argv[0], os.path.abspath(argv[1]), os.path.abspath(argv[2])
    opt = {k: argv[argv.index(k) + 1] for k in ("--samples", "--px", "--seed") if k in argv}
    spp, px, seed = int(opt.get("--samples", 16)), int(opt.get("--px", 360)), int(opt.get("--seed", 126))
    record = {"samples": spp, "px": px, "seed": seed, "light": "character_neutral/1", "tiles": []}
    for name in ("walk", "sit", "kneel"):
        ctx = R.prepare(blend, name, seed, {}, lean=False)
        S.replay(ctx["proxy"], os.path.join(bakes, name + ".pc2"))
        sc = bpy.context.scene
        cam, lrig, fov = SH.setup(sc, spp)
        SH.aim(cam, lrig, fov, CAMS[name])
        sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = px, px, 100
        sc.render.image_settings.file_format = "PNG"
        for shot, frame in sorted(ctx["motion"]["evidence"].items(), key=lambda kv: kv[1]):
            S._apply_pose(ctx["rig"], ctx["motion"]["pose"](frame))
            sc.frame_set(frame)
            for label, sim in (("simulated", True), ("skinned", False)):
                S.show(ctx["followers"], sim)
                sc.render.filepath = os.path.join(out, f"{shot}.{label}.png")
                bpy.ops.render.render(write_still=True)
                record["tiles"].append({"motion": name, "shot": shot, "frame": frame, "skirt": label,
                                        "camera": CAMS[name]})
    json.dump(record, open(os.path.join(out, "sim_shots.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
