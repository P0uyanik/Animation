#!/usr/bin/env python3
"""T-139 evidence: gesture attribution before (input 68da3e8) and after, on e910 s010 (T-117 §3) with the mirrored
boy_reluctant_shrug added at f1 / f126 / f144 (experiment scenes, not production), on e910 s010 as shipped and on e909
s010 (T-114 §3: boy_reluctant_shrug overlapping his right-arm reach).

    python3 pipeline/production/run_shot.py --shot <e909|e910 s010>/shot.scene.json --stages prepare,bake ...
    python3 docs/evaluation/animation/T-139/measure.py --render <plush-render> --old <dir with the 68da3e8 animcheck>

Writes measure_t139.json here: per scene, per clip gesture, the measured side and the threshold failures and acting
warnings of both versions. Scenes and bakes go to a temp dir.
"""
from __future__ import annotations

import argparse
import copy
import importlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
# The resolved scenes of `run_shot --stages prepare` (packages built from the specs; build/ is git-ignored).
E910 = ROOT / "episodes/e910_showcase/shots/s010/build/shot.resolved.scene.json"
E909 = ROOT / "episodes/e909_two_char_acting/shots/s010/build/shot.resolved.scene.json"


def load(tool_dir: Path):
    for m in ("animcheck", "personality", "timing", "acting"):
        sys.modules.pop(m, None)
    sys.path.insert(0, str(tool_dir))
    mods = {m: importlib.import_module(m) for m in ("animcheck", "acting")}
    sys.path.pop(0)
    return mods


def run(mods, scene_path: Path, scene: dict, bake: dict, thr: dict) -> dict:
    rep = mods["animcheck"].analyse(bake, scene, scene_path)
    act = mods["acting"].analyse(scene, scene_path, bake, thr)
    return {"gestures": [{"label": g["label"], "side": g.get("side")} for g in rep["gestures"]],
            "failures": mods["animcheck"].check(rep, thr), "acting_warnings": act.get("warnings", [])}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", required=True)
    ap.add_argument("--old", required=True)
    args = ap.parse_args()
    thr = json.loads((ROOT / "tools/animcheck/thresholds.json").read_text())
    base = json.loads(E910.read_text())
    scenes = {"e910_s010": (E910, base), "e909_s010": (E909, json.loads(E909.read_text()))}
    for f in (1, 126, 144):
        s = copy.deepcopy(base)
        s["actions"].append({"type": "clip", "character": "boy", "clip": "boy_reluctant_shrug", "start": f,
                             "mirror": True})
        scenes[f"e910_s010_shrugL_f{f}"] = (None, s)
    old, new = load(Path(args.old)), load(ROOT / "tools/animcheck")
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, (path, scene) in scenes.items():
            if path is None:  # experiment scene: next to the resolved one (its package paths), removed after the bake
                path = E910.parent / f".t139_{name}.scene.json"
                path.write_text(json.dumps(scene))
            bake_p = Path(tmp) / f"{name}.bake.json"
            try:
                r = subprocess.run([args.render, str(path), "--bake", str(bake_p), "--frames",
                                    f"{scene['frameStart']}-{scene['frameEnd']}"], capture_output=True, text=True,
                                   cwd=ROOT)
            finally:
                if path.name.startswith(".t139_"):
                    path.unlink()
            if r.returncode != 0:
                out[name] = {"error": r.stderr[-300:]}
                continue
            bake = json.loads(bake_p.read_text())
            out[name] = {"before": run(old, path, scene, bake, thr), "after": run(new, path, scene, bake, thr)}
            print(name, json.dumps(out[name], indent=1))
    (HERE / "measure_t139.json").write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
