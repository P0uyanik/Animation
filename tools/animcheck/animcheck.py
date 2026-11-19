#!/usr/bin/env python3
"""animcheck (T-061): animation-principle metrics per gesture, measured on an engine shot bake (plush.shot_bake/1).

    python3 tools/animcheck/animcheck.py --bake bake.json [--scene scene.json] [--json out.json]
                                         [--thresholds tools/animcheck/thresholds.json --check]

Gestures come from the scene's actions (the bake names its scene): clip actions (not base clips) and the IK gestures
`touch` and `reach`. For each gesture the active hand is the side named by the action (`hand`); for a clip, the arm
the clip drives (T-139: the arm sides in its `mask`, else its tracks, swapped when the action mirrors the clip), so a
one-arm gesture is measured on that arm even while the other arm carries or reaches; only when the clip drives both
arms or neither (or the clip file is missing) the wrist that travels furthest in the gesture window. Measured on the wrist pivot (`hand.<side>` bone of the character package, world
space, per integer frame) and on the arm bones' global rotations:

- **segments**: the *entry* (first movement out of the pose the gesture starts from: the lift) and the *exit* (the
  last movement, back to the pose it hands over to). A segment starts where the wrist speed first exceeds `onset`
  (10 %) of the window's peak speed, extended back over its slow tail while the speed still falls and stays above 2 %
  of the peak, and ends at the first local speed minimum below `split` (35 %) of the segment's peak (the exit mirrors
  this from the end of the window).
- **ease ratio** (slow-in / slow-out): mean wrist speed over the first and over the last 20 % of a segment's frames,
  divided by the segment's peak speed. A constant-speed move is close to 1; a good ease is well below 0.5.
- **arc deviation**: the largest distance of the wrist path from the straight chord between the segment's ends,
  divided by the chord length (0 = straight line); in 3D (`arc`) and as the viewer sees it, projected through the
  bake's camera (`arc_screen`).
- **onset / stop step**: the wrist speed of the first moving frame of the entry (`onset_step`) and of the last moving
  frame of the exit (`stop_step`), divided by the segment's peak speed: how abruptly the motion leaves rest and
  arrives at rest (a blend that starts at full spacing is a pop even when the rest of the curve is eased).
- **jerk**: the largest change of wrist speed between consecutive frames inside a segment, divided by the segment's
  peak speed (a velocity pop: a burst at a blend boundary, a hard start or stop).
- **max per-frame step**: the largest wrist displacement between consecutive frames (mm) and the largest per-frame
  rotation of upperArm / forearm / hand (degrees) in the window (strobing).
- **overshoot / settle** (reported): how far the wrist passes the entry segment's end along the chord within the
  next 12 frames (% of the chord), and the frames from the entry's peak speed until the speed stays below 10 %.

Thresholds (`--check`): see thresholds.json and tools/animcheck/README.md. Exit code 1 if any checked value fails.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ONSET = 0.10
TAIL = 0.02
SPLIT = 0.35
EASE_SHARE = 0.20
SETTLE_LOOKAHEAD = 12
ARM_BONES = ("upperArm", "forearm", "hand")


def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vlen(a):
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def vdot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def pivot(m, head):
    """Skinning matrix (column-major 16 floats, = global * translate(-head)) applied to the rest head = the pivot."""
    return tuple(m[r] * head[0] + m[4 + r] * head[1] + m[8 + r] * head[2] + m[12 + r] for r in range(3))


def rot_angle_deg(m0, m1):
    """Angle of the relative rotation between two column-major matrices' 3x3 parts."""
    # trace(R0^T R1)
    tr = 0.0
    for c in range(3):
        for r in range(3):
            tr += m0[4 * c + r] * m1[4 * c + r]
    return math.degrees(math.acos(max(-1.0, min(1.0, (tr - 1.0) / 2.0))))


def load_clip(scene_path: Path, action: dict) -> dict | None:
    """The clip document of a clip action (its `file` next to the scene, else content/clips/<clip>.clip.json)."""
    if "file" in action:
        cand = [scene_path.parent / action["file"]]
    else:
        cand = [d / "content" / "clips" / f"{action.get('clip', '')}.clip.json" for d in scene_path.resolve().parents]
    for c in cand:
        if c.is_file():
            return json.loads(c.read_text())
    return None


def load_clip_frames(scene_path: Path, action: dict) -> float | None:
    """Clip length in clip seconds, for windows of clip actions without `end`."""
    data = load_clip(scene_path, action)
    return None if data is None else (data["frame_count"] - 1) / float(data["fps"])


def clip_side(clip: dict | None, mirror: bool = False) -> str | None:
    """The one arm side ('L' / 'R') a clip drives (arm bones in its mask, else its tracks; swapped when the action
    mirrors it), or None when it drives both arms or neither."""
    if not clip:
        return None
    roles = clip.get("mask") or list(clip.get("tracks", {}))
    sfx = (clip.get("mirror") or {}).get("suffix") or [".L", ".R"]
    sides = {s for s, x in zip("LR", sfx) for r in roles if r in {f"{b}{x}" for b in ARM_BONES}}
    if len(sides) != 1:
        return None
    side = sides.pop()
    return {"L": "R", "R": "L"}[side] if mirror else side


class Character:
    def __init__(self, entry: dict):
        self.name = entry["name"]
        self.bones = entry.get("bones", [])
        pkg = Path(entry["package"])
        doc = json.loads(pkg.read_text()) if pkg.is_file() else json.loads((pkg / "character.json").read_text())
        heads = {b["name"]: b["head"] for b in doc["skeleton"]}
        self.index = {n: i for i, n in enumerate(self.bones)}
        self.heads = [heads.get(n, [0, 0, 0]) for n in self.bones]

    def matrix(self, frame_data: dict, bone: str):
        i = self.index.get(bone)
        if i is None:
            return None
        skin = frame_data["characters"][self.name]["skin"]
        return skin[16 * i:16 * i + 16]

    def position(self, frame_data: dict, bone: str):
        m = self.matrix(frame_data, bone)
        return None if m is None else pivot(m, self.heads[self.index[bone]])


LEAD_MARGIN = 12  # frames before a gesture's start that still belong to it
SETTLE_MARGIN = 24  # frames after a gesture's nominal end that still belong to it (longer blends, succession, settle)


def gestures(scene: dict, scene_path: Path) -> list[dict]:
    fps = scene["frameRate"][0] / scene["frameRate"][1]
    out = []
    for a in scene.get("actions", []):
        t = a.get("type")
        if t == "clip" and not a.get("base", False):
            start = float(a.get("start", scene.get("frameStart", 1)))
            clip = load_clip(scene_path, a)
            if "end" in a:
                end = float(a["end"])
            else:
                if clip is None:
                    continue
                end = start + (clip["frame_count"] - 1) / float(clip["fps"]) * fps / float(a.get("speed", 1.0))
            end += float(a.get("blendOut", 6))
            label = f"{a['character']} clip {a.get('clip', Path(a.get('file', '?')).stem)} @{a.get('start')}"
            if a.get("speed", 1) != 1:
                label += f" x{a['speed']}"
            out.append({"label": label, "character": a["character"], "start": start, "end": end,
                        "side": clip_side(clip, bool(a.get("mirror", False))), "kind": "clip"})
        elif t in ("touch", "reach") and "prop" not in a:
            start = float(a["start"])
            contact = float(a.get("contact", start + 14))
            end = float(a.get("end", contact + 20))
            out.append({"label": f"{a['character']} {t} @{a['start']}", "character": a["character"], "start": start,
                        "end": end, "side": a.get("hand", "R")[:1] or "R", "kind": t})
    # The analysis window starts LEAD_MARGIN frames before the gesture (a ramp may start early to reach its contact
    # in time) and runs until it settled, SETTLE_MARGIN frames after its end, never into the character's previous or
    # next gesture.
    for g in out:
        g["nominal_end"] = g["end"]
    for g in out:
        mine = [h for h in out if h["character"] == g["character"] and h is not g]
        nxt = [h["start"] for h in mine if h["start"] > g["start"]]
        prv = [h["nominal_end"] for h in mine if h["start"] < g["start"]]
        g["end"] = min([g["nominal_end"] + SETTLE_MARGIN] + [n - 1 for n in nxt])
        g["from"] = max([g["start"] - LEAD_MARGIN] + [p + 1 for p in prv])
    return out


def segment(speed: list[float], reverse: bool = False) -> tuple[int, int] | None:
    """Entry segment (indices into speed) or, with reverse, the exit segment."""
    s = speed[::-1] if reverse else speed
    peak = max(s) if s else 0.0
    if peak <= 1e-9:
        return None
    i0 = next(i for i, v in enumerate(s) if v > ONSET * peak)
    # include the slow tail of the start (the ease) back to where the motion begins
    while i0 > 0 and s[i0 - 1] < s[i0] and s[i0 - 1] > TAIL * peak:
        i0 -= 1
    run = 0.0
    i1 = len(s) - 1
    for i in range(i0, len(s)):
        run = max(run, s[i])
        if i > i0 and s[i] < SPLIT * run and (i + 1 >= len(s) or s[i] <= s[i + 1]) and s[i] <= s[i - 1]:
            i1 = i
            break
    if reverse:
        n = len(s) - 1
        return n - i1, n - i0
    return i0, i1


def ease_ratios(speed: list[float], a: int, b: int) -> tuple[float, float, float]:
    seg = speed[a:b + 1]
    peak = max(seg)
    k = max(1, round(EASE_SHARE * len(seg)))
    return (sum(seg[:k]) / k / peak, sum(seg[-k:]) / k / peak, peak)


def arc_deviation(points: list[tuple]) -> tuple[float, float]:
    p0, p1 = points[0], points[-1]
    chord = vsub(p1, p0)
    L = vlen(chord)
    if L < 1e-9:
        return 0.0, 0.0
    u = (chord[0] / L, chord[1] / L, chord[2] / L)
    dev = 0.0
    for p in points:
        d = vsub(p, p0)
        t = vdot(d, u)
        perp = vsub(d, (u[0] * t, u[1] * t, u[2] * t))
        dev = max(dev, vlen(perp))
    return dev / L, L


def project(cam: dict, p) -> tuple[float, float]:
    """Pinhole projection of a world point into the bake camera's image plane (normalised by focal length)."""
    pos, tgt, up = cam["position"], cam["target"], cam.get("up", [0, 1, 0])
    f = vsub(tgt, pos)
    fl = vlen(f)
    f = tuple(c / fl for c in f)
    r = (f[1] * up[2] - f[2] * up[1], f[2] * up[0] - f[0] * up[2], f[0] * up[1] - f[1] * up[0])
    rl = vlen(r)
    r = tuple(c / rl for c in r)
    u = (r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0])
    d = vsub(p, pos)
    z = max(1e-6, vdot(d, f))
    return (vdot(d, r) / z, vdot(d, u) / z)


def analyse_gesture(g: dict, ch: Character, frames: dict[int, dict], fps: float) -> dict:
    lo = int(math.floor(g["from"]))
    hi = int(math.ceil(g["end"]))
    fs = [f for f in range(lo, hi + 1) if f in frames]
    sides = [g["side"]] if g["side"] else ["L", "R"]
    best = None
    for side in sides:
        pts = [ch.position(frames[f], f"hand.{side}") for f in fs]
        if any(p is None for p in pts):
            continue
        travel = sum(vlen(vsub(pts[i + 1], pts[i])) for i in range(len(pts) - 1))
        if best is None or travel > best[1]:
            best = (side, travel, pts)
    if best is None:
        return {"label": g["label"], "error": "no hand bone"}
    side, _, pts = best
    speed = [vlen(vsub(pts[i + 1], pts[i])) for i in range(len(pts) - 1)]  # m per frame, between fs[i] and fs[i+1]
    res = {"label": g["label"], "character": ch.name, "kind": g["kind"], "side": side,
           "window": [fs[0], fs[-1]], "speed_mm_per_frame": [round(v * 1000, 3) for v in speed],
           "wrist": [[round(c, 5) for c in p] for p in pts]}
    max_rot = 0.0
    for bone in ARM_BONES:
        ms = [ch.matrix(frames[f], f"{bone}.{side}") for f in fs]
        if any(m is None for m in ms):
            continue
        for i in range(len(ms) - 1):
            max_rot = max(max_rot, rot_angle_deg(ms[i], ms[i + 1]))
    res["max_step_mm"] = round(max(speed) * 1000, 2)
    res["max_rot_step_deg"] = round(max_rot, 2)
    for name, rev in (("entry", False), ("exit", True)):
        seg = segment(speed, rev)
        if not seg:
            continue
        a, b = seg
        ein, eout, peak = ease_ratios(speed, a, b)
        arc, chord = arc_deviation(pts[a:b + 2])
        scr = [project(frames[fs[i]]["camera"], pts[i]) + (0.0,) for i in range(a, min(b + 2, len(pts)))]
        arc_screen, _ = arc_deviation(scr)
        seg = speed[a:b + 1]
        jerk = max(abs(seg[i + 1] - seg[i]) for i in range(len(seg) - 1)) / peak if len(seg) > 1 else 0.0
        res[name] = {"frames": [fs[a], fs[b + 1]], "ease_in": round(ein, 3), "ease_out": round(eout, 3),
                     "jerk": round(jerk, 3), "onset_step": round(seg[0] / peak, 3), "stop_step": round(seg[-1] / peak, 3),
                     "peak_mm_per_frame": round(peak * 1000, 2), "arc": round(arc, 4), "arc_screen": round(arc_screen, 4), "chord_mm": round(chord * 1000, 1)}
    if "entry" in res:
        a, b = (fs.index(res["entry"]["frames"][0]), fs.index(res["entry"]["frames"][1]))
        p0, p1 = pts[a], pts[b]
        chord = vsub(p1, p0)
        L = vlen(chord)
        over = 0.0
        if L > 1e-9:
            u = tuple(c / L for c in chord)
            for i in range(b, min(len(pts), b + SETTLE_LOOKAHEAD + 1)):
                over = max(over, vdot(vsub(pts[i], p1), u))
        ipk = max(range(a, b), key=lambda i: speed[i]) if b > a else a
        pk = speed[ipk]
        settle = 0
        for i in range(ipk, len(speed)):
            if all(v < ONSET * pk for v in speed[i:i + 3]):
                settle = i - ipk
                break
        res["entry"]["overshoot_pct"] = round(100 * over / L, 1) if L > 1e-9 else 0.0
        res["entry"]["settle_frames"] = settle
    return res


def analyse(bake: dict, scene: dict, scene_path: Path) -> dict:
    fps = bake["fps"][0] / bake["fps"][1]
    frames = {fd["frame"]: fd for fd in bake["frame_data"]}
    chars = {c["name"]: Character(c) for c in bake["characters"] if c.get("supported")}
    results = []
    for g in gestures(scene, scene_path):
        ch = chars.get(g["character"])
        if ch:
            results.append(analyse_gesture(g, ch, frames, fps))
    return {"format": "plush.animcheck", "version": 1, "scene": scene.get("name", ""), "fps": fps, "gestures": results}


def check(report: dict, thresholds: dict) -> list[str]:
    """Threshold failures (empty = pass). Segments shorter than min_chord_mm are not checked for ease, jerk and arc."""
    fails = []
    t = thresholds
    for g in report["gestures"]:
        if "error" in g:
            fails.append(f"{g['label']}: {g['error']}")
            continue
        if g["max_step_mm"] > t["max_step_mm"]:
            fails.append(f"{g['label']}: wrist step {g['max_step_mm']} mm/frame > {t['max_step_mm']}")
        if g["max_rot_step_deg"] > t["max_rot_step_deg"]:
            fails.append(f"{g['label']}: arm rotation step {g['max_rot_step_deg']} deg/frame > {t['max_rot_step_deg']}")
        for name in ("entry", "exit"):
            s = g.get(name)
            if not s or s["chord_mm"] < t["min_chord_mm"]:
                continue
            for k in ("ease_in", "ease_out"):
                if s[k] > t["max_ease_ratio"]:
                    fails.append(f"{g['label']} {name}: {k} {s[k]} > {t['max_ease_ratio']}")
            if s["jerk"] > t["max_jerk"]:
                fails.append(f"{g['label']} {name}: jerk {s['jerk']} > {t['max_jerk']}")
            k = "onset_step" if name == "entry" else "stop_step"
            if s[k] > t["max_first_step"]:
                fails.append(f"{g['label']} {name}: {k} {s[k]} > {t['max_first_step']}")
            if s["arc_screen"] < t["min_arc_screen"]:
                fails.append(f"{g['label']} {name}: screen arc {s['arc_screen']} < {t['min_arc_screen']}")
            if s["arc"] < t["min_arc"]:
                fails.append(f"{g['label']} {name}: arc {s['arc']} < {t['min_arc']}")
    return fails


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bake", required=True)
    ap.add_argument("--scene", default="", help="scene file (default: the bake's scene_path)")
    ap.add_argument("--json", default="", help="write the full report here")
    ap.add_argument("--thresholds", default=str(Path(__file__).with_name("thresholds.json")))
    ap.add_argument("--check", action="store_true", help="apply the thresholds; exit 1 on a failure")
    args = ap.parse_args(argv)
    bake = json.loads(Path(args.bake).read_text())
    scene_path = Path(args.scene or bake["scene_path"])
    scene = json.loads(scene_path.read_text())
    report = analyse(bake, scene, scene_path)
    fails = []
    if args.check:
        fails = check(report, json.loads(Path(args.thresholds).read_text()))
        report["failures"] = fails
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=1) + "\n")
    for g in report["gestures"]:
        if "error" in g:
            print(f"{g['label']}: {g['error']}")
            continue
        parts = [f"{g['label']} ({g['side']})", f"step {g['max_step_mm']} mm/f, rot {g['max_rot_step_deg']} deg/f"]
        for name in ("entry", "exit"):
            s = g.get(name)
            if s:
                parts.append(f"{name} f{s['frames'][0]}-{s['frames'][1]} ease {s['ease_in']}/{s['ease_out']} "
                             f"step {s['onset_step']}/{s['stop_step']} jerk {s['jerk']} "
                             f"arc {s['arc']} (screen {s['arc_screen']}) chord {s['chord_mm']} mm")
        if "entry" in g:
            parts.append(f"overshoot {g['entry']['overshoot_pct']} % settle {g['entry']['settle_frames']} f")
        print(" | ".join(parts))
    for f in fails:
        print("FAIL", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
