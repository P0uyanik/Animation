"""T-198 motion continuity: the per-frame speed-limit check of the engine (engine/anim/animation.h MotionLimits,
scene/interaction.h continuityReport) on a bake JSON, for any shot.

    python3 continuity.py <bake.json> [--scene=<resolved scene.json>] [--json]

A body bone (hips, spine, chest, neck, head, thigh, shin, foot, upperArm, forearm, hand) snaps on frame f when it
turns more than 1080 deg/s or its pivot travels more than 2.4 m/s from f-1 to f (45 deg / 100 mm per frame at 24 fps);
a finger (f<k>a..c, thumbA..C) when it turns more than 600 deg/s relative to its parent. Eyes (saccades), DEF and chain
bones are not measured. With --scene, frames intended by data are classified, never smoothed: "cut" (a camera.* or the
character's own position / yaw animation key that steps at f) and "fast" (an action with "fast": true covering f,
start .. end + 1). Exit status 1 when a snap is left (not cut, not fast)."""
import json
import math
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shot as S  # noqa: E402

DEG_PER_SEC, MM_PER_SEC, FINGER_DEG_PER_SEC = 1080.0, 2400.0, 600.0
BODY = {"hips", "spine", "chest", "neck", "head", "thigh", "shin", "foot", "upperArm", "forearm", "hand"}


def bone_class(name):
    base = name.split(".")[0]
    if base in BODY:
        return "body"
    if re.fullmatch(r"f[0-9][a-c]", base) or re.fullmatch(r"thumb[A-C]", base):
        return "finger"
    return None


def _axes(M):
    R = M[..., :3, :3]
    return R / np.linalg.norm(R, axis=-2, keepdims=True)


def _turn(Ra, Rb):
    tr = np.einsum("...ji,...jk->...ik", Ra, Rb).trace(axis1=-2, axis2=-1)
    return np.degrees(np.arccos(np.clip((tr - 1) / 2, -1, 1)))


def exemptions(scene, who):
    """frame -> "cut" | "fast" (scene JSON, as continuityExemptions in the engine; hand-authored tracks only)."""
    out = {}
    for name, keys in (scene.get("animation") or {}).items():
        if not (name.startswith("camera.") or name in (who + ".position", who + ".yaw")):
            continue
        for a, b in zip(keys, keys[1:]):
            step = len(a) > 2 and a[2] == "step"
            if step and a[1] != b[1]:
                out[int(math.ceil(b[0] - 1e-9))] = "cut"
    for a in scene.get("actions") or []:
        if a.get("fast") is True and a.get("character", who) == who and isinstance(a.get("start"), (int, float)):
            s = int(math.floor(a["start"]))
            e = int(math.ceil(a.get("end", s)))
            for f in range(s, e + 2):
                out.setdefault(f, "fast")
    return out


def report(bake, scene=None):
    sh = S.Shot(bake) if isinstance(bake, str) else bake
    fps = float(getattr(sh, "fps", 24.0) or 24.0)
    rows = []
    for c in sh.characters:
        ex = exemptions(scene, c.name) if scene else {}
        R, piv = _axes(c.M), c.pivots()
        for i, b in enumerate(c.bones):
            k = bone_class(b)
            if not k:
                continue
            if k == "finger":
                p = c.parent[i]
                if p < 0:
                    continue
                L = np.einsum("fji,fjk->fik", R[:, p], R[:, i])
                deg, mm = _turn(L[:-1], L[1:]), np.zeros(len(L) - 1)
                ratio = deg / (FINGER_DEG_PER_SEC / fps)
            else:
                deg = _turn(R[:-1, i], R[1:, i])
                mm = np.linalg.norm(np.diff(piv[:, i], axis=0), axis=1) * 1000
                ratio = np.maximum(deg / (DEG_PER_SEC / fps), mm / (MM_PER_SEC / fps))
            for j in np.nonzero(ratio > 1)[0]:
                f = int(sh.frames[j + 1])
                rows.append({"character": c.name, "frame": f, "bone": b, "deg": round(float(deg[j]), 1),
                             "mm": round(float(mm[j]), 1), "class": ex.get(f, "snap")})
    return rows


if __name__ == "__main__":
    opts = {a.split("=", 1)[0][2:]: a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--") and "=" in a}
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    scene = json.load(open(opts["scene"])) if "scene" in opts else None
    rows = report(paths[0], scene)
    if "--json" in sys.argv:
        print(json.dumps(rows))
    else:
        by = {}
        for r in rows:
            by.setdefault((r["character"], r["frame"], r["class"]), []).append(f'{r["bone"]} {r["deg"]:.0f}/{r["mm"]:.0f}')
        for (c, f, k), bs in sorted(by.items()):
            print(f"{c} f{f} {k}: " + ", ".join(bs))
        print("# snap frames:", len({(c, f) for (c, f, k) in by if k == "snap"}))
    sys.exit(1 if any(r["class"] == "snap" for r in rows) else 0)
