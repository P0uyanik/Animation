#!/usr/bin/env python3
"""animcheck timing rule (T-104): beat lengths and holds of a shot against the reference timing table
(content/timing/reference_timing.json, measured in docs/references/video_paperboat.mp4 and video_watertable.mp4).

    python3 tools/animcheck/timing.py --scene shot.scene.json [--bake bake.json] [--json report.json]

It only warns: the result never fails a check (exit 0 unless the inputs cannot be read). Two kinds of warning:

- **short beat**: an interaction beat of the scene's actions shorter than the low end of its reference range
  (`beats.<beat>.frames[0]`). Beats (scene frames; frames an action leaves out take the engine's shared defaults,
  scene/interaction.h):
    grasp / reach with a prop   reach        = contact - start
    reach / grasp:false         hold         = end - contact (the touch)
    hold (carry: at / by moves) reach        = end - start;  hold (still) hold = end - start
    place                       place        = contact - start;  release = end - contact
    handover                    reach        = contact - receiverStart;  shared_hold = release - contact;
                                release      = end - release
- **no hold**: with a bake, the longest run of frames in which every hand (wrist pivot) and head of every character
  moves less than `timing_still_mm_per_frame` (thresholds.json) is shorter than `beats.hold.frames[0]`: the shot
  never comes to rest. Without a bake, the frames after the last interaction beat ends (the end hold) are measured
  instead.

Frame values at 24 fps (scenes at another rate are scaled)."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import animcheck  # noqa: E402

REFERENCE = ROOT / "content" / "timing" / "reference_timing.json"
# engine defaults (scene/interaction.h) for frames an action leaves out
DEFAULTS = {"reach_contact": 14, "touch_end": 12, "hold_end": 16, "place_contact": 16, "place_end": 14,
            "handover_contact": 18, "handover_receiver": 4, "handover_release": 4, "handover_end": 12}


def load_reference(path: Path = REFERENCE) -> dict:
    ref = json.loads(Path(path).read_text())
    return {k: v["frames"] for k, v in ref["beats"].items()}


def scene_beats(scene: dict) -> list[dict]:
    """Interaction beats of the scene's actions: {beat, character, action, frames: [a, b], length}."""
    out = []

    def add(beat, who, typ, a, b):
        out.append({"beat": beat, "character": who, "action": typ, "frames": [a, b], "length": b - a})

    for a in scene.get("actions", []):
        t, who = a.get("type"), a.get("character", "")
        s = a.get("start")
        if s is None:
            continue
        if t in ("reach", "grasp") and "prop" in a:
            c = a.get("contact", s + DEFAULTS["reach_contact"])
            add("reach", who, t, s, c)
            if a.get("grasp", True) is False:
                add("hold", who, t, c, a.get("end", c + DEFAULTS["touch_end"]))
        elif t == "hold":
            moves = ("at" in a) or any(abs(x) > 1e-6 for x in a.get("by", [0, 0, 0]))
            add("reach" if moves else "hold", who, t, s, a.get("end", s + DEFAULTS["hold_end"]))
        elif t == "place":
            c = a.get("contact", s + DEFAULTS["place_contact"])
            add("place", who, t, s, c)
            add("release", who, t, c, a.get("end", c + DEFAULTS["place_end"]))
        elif t == "handover":
            rs = a.get("receiverStart", s + DEFAULTS["handover_receiver"])
            c = a.get("contact", s + DEFAULTS["handover_contact"])
            rel = a.get("release", c + DEFAULTS["handover_release"])
            add("reach", a.get("to", ""), t, rs, c)
            add("shared_hold", who, t, c, rel)
            add("release", who, t, rel, a.get("end", rel + DEFAULTS["handover_end"]))
    return out


def still_runs(bake: dict, still_mm: float) -> dict:
    """Longest run of frames in which every wrist and head of every character moves < still_mm per frame."""
    frames = {fd["frame"]: fd for fd in bake["frame_data"]}
    chars = [animcheck.Character(c) for c in bake["characters"] if c.get("supported")]
    bones = ("hand.L", "hand.R", "head")
    order = sorted(frames)
    prev, best, cur, start, best_at = None, 0, 0, None, None
    for f in order:
        pts = [ch.position(frames[f], b) for ch in chars for b in bones if b in ch.index]
        if prev is not None:
            step = max(1000.0 * math.dist(p, q) for p, q in zip(pts, prev)) if pts else 0.0
            if step < still_mm:
                if cur == 0:
                    start = f - 1
                cur += 1
                if cur > best:
                    best, best_at = cur, [start, f]
            else:
                cur = 0
        prev = pts
    return {"longest_still_frames": best, "at": best_at}


def analyse(scene: dict, bake: dict | None = None, thresholds: dict | None = None, reference: dict | None = None) -> dict:
    ref = reference or load_reference()
    thr = thresholds or json.loads((HERE / "thresholds.json").read_text())
    fps = scene.get("frameRate", [24, 1])
    k = 24.0 / (fps[0] / fps[1])  # scene frames -> frames at 24 fps
    warnings = []
    beats = scene_beats(scene)
    for b in beats:
        lo = ref.get(b["beat"], [0])[0]
        b["reference"] = ref.get(b["beat"])
        if b["length"] * k < lo:
            warnings.append(f"short beat: {b['character']} {b['action']} {b['beat']} f{b['frames'][0]}-f{b['frames'][1]} "
                            f"{b['length'] * k:g} f < reference {lo} f")
    hold_lo = ref["hold"][0]
    res = {"format": "plush.animcheck_timing", "version": 1, "scene": scene.get("name", ""),
           "timing_profile": scene.get("timing"), "beats": beats}
    if bake is not None:
        runs = still_runs(bake, thr["timing_still_mm_per_frame"])
        res["holds"] = runs
        if runs["longest_still_frames"] * k < hold_lo:
            warnings.append(f"no hold: longest still run {runs['longest_still_frames'] * k:g} f < reference hold {hold_lo} f")
    else:
        last = max((b["frames"][1] for b in beats), default=scene.get("frameStart", 1))
        end_hold = scene.get("frameEnd", last) - last
        res["holds"] = {"end_hold_frames": end_hold}
        if beats and end_hold * k < hold_lo:
            warnings.append(f"no hold: end hold {end_hold * k:g} f after the last beat < reference hold {hold_lo} f")
    res["warnings"] = warnings
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--bake", default="")
    ap.add_argument("--json", default="")
    ap.add_argument("--reference", default=str(REFERENCE))
    a = ap.parse_args(argv)
    scene = json.loads(Path(a.scene).read_text())
    bake = json.loads(Path(a.bake).read_text()) if a.bake else None
    res = analyse(scene, bake, reference=load_reference(Path(a.reference)))
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1) + "\n")
    for w in res["warnings"]:
        print("WARN", w)
    print(f"timing: {len(res['beats'])} beats, {len(res['warnings'])} warnings (warnings only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
