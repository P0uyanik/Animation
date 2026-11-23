"""T-194 measure: the hair as Blender renders it (after the push-out, if the shot.blend has it) against every
collider of the shot, per frame and per surface.

Opens a shot.blend written by pipeline/charsys/shot_render.py (with or without --hair-pushout) and evaluates it frame
by frame. Hair = the mesh objects `hair_*` of every character (the push-out's anchor proxies are not hair).
Surfaces = what hair_pushout.py collides with (own figure, the other characters' figures, props with their caps, the
bake's box objects) plus glasses, measured as their own line (T-183's SKIP list keeps them out of the colliders).
Depth rules = T-183 `tools/measure_body.py` (exit distance: towards / away from the nearest surface, then the second
shortest of 26 fixed directions; "under the face" and "enclosed" rules; vertices embedded at rest count only by what
they are deeper than at rest, and not at all where they sit at their rest distance from the same part). The rest is
the character's own figure in its rest pose. A vertex counts when deeper than --limit-mm (1).

Also per frame: the largest frame-to-frame move of a hair vertex (pops), and a SHA-256 over all evaluated hair
positions (float32) of the measured frames (determinism; with --jobs the hash of the parts' hashes, so compare
runs made with the same --jobs).

    python3 tools/bpy_blender.py -b --factory-startup -P measure_eval.py -- <shot.blend> <out.json>
        [--frames=A-B] [--step=N] [--limit-mm=1] [--characters=a,b] [--jobs=N]"""
import fnmatch
import hashlib
import json
import os
import subprocess
import sys
import time

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SKIP = ["eye*", "brow*", "lash*", "lid*", "mouth*", "glasses*"]
REACH = 0.05
CAP = 0.6
EPS = 2e-5
UNDER = 0.7
REST_MATCH = 0.0005
DIRS = [Vector(d).normalized() for d in
        [(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1) if (x, y, z) != (0, 0, 0)]]

BPY = os.path.join(os.path.dirname(os.path.abspath(__file__)), *[".."] * 5, "tools", "bpy_blender.py")
argv = sys.argv[sys.argv.index("--") + 1:]
BLEND, OUT = argv[0], argv[1]


def opt(name, default=None):
    return next((a.split("=", 1)[1] for a in argv[2:] if a.startswith(f"--{name}=")), default)


LIMIT = float(opt("limit-mm", "1")) / 1000.0


def exit_along(tree, p, d, best):
    t, last = 0.0, 0.0
    while True:
        hit = tree.ray_cast(p + d * (t + EPS), d, CAP - t)
        if hit[0] is None:
            return last
        t += EPS + hit[3]
        last = t
        if last >= best:
            return last


def enclosed(tree, p):
    free = 0
    for d in DIRS:
        if tree.ray_cast(p + d * EPS, d, CAP)[0] is None:
            free += 1
            if free >= 2:
                return False
    return True


def exit_depth(tree, p, loc, nrm, dist):
    off = p - loc
    if dist > 1e-7:
        if off.dot(nrm) >= 0:
            if tree.ray_cast(p, off / dist, CAP)[0] is None:
                return 0.0
        elif -off.dot(nrm) >= UNDER * dist:
            d = -off / dist
            if tree.ray_cast(loc + d * EPS, d, CAP)[0] is None:
                return dist if enclosed(tree, p) else 0.0
    if not enclosed(tree, p):  # the loop below returns 0 exactly when two directions are free (same first rays)
        return 0.0
    best, second = CAP, CAP
    for d in DIRS:
        e = exit_along(tree, p, d, second)
        if e < best:
            best, second = e, best
        elif e < second:
            second = e
        if second <= 0.0:
            return 0.0
    return second


def is_figure(o, rig, glasses=False):
    if o.type != "MESH" or o.name.startswith(("hair_", "garment.collider", "WGT-", "ps_pushout")):
        return False
    if glasses and fnmatch.fnmatchcase(o.name, "glasses*"):
        return any(m.type == "ARMATURE" and m.object == rig for m in o.modifiers) or o.parent == rig
    if any(fnmatch.fnmatchcase(o.name, p) for p in SKIP):
        return False
    return any(m.type == "ARMATURE" and m.object == rig for m in o.modifiers)


class Surfaces:
    """One tree over several objects, with the label of every triangle."""

    def __init__(self, objs, deps):
        V, T, self.labels, self.ranges, off, toff = [], [], [], [], 0, 0
        for label, o in objs:
            e = o.evaluated_get(deps)
            me = e.to_mesh()
            n = len(me.vertices)
            me.calc_loop_triangles()
            m = len(me.loop_triangles)
            if n and m:
                co = np.empty(n * 3)
                me.vertices.foreach_get("co", co)
                M = np.array(e.matrix_world)
                V.append(co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3])
                t = np.empty(m * 3, dtype=np.int64)
                me.loop_triangles.foreach_get("vertices", t)
                T.append(t.reshape(-1, 3) + off)
                self.labels.append(label)
                self.ranges.append(toff + m)
                off += n
                toff += m
            e.to_mesh_clear()
        self.ranges = np.array(self.ranges)
        if V:
            V, T = np.concatenate(V), np.concatenate(T)
            self.tree = BVHTree.FromPolygons(V.tolist(), T.tolist(), all_triangles=True)
            self.lo, self.hi = V.min(0) - REACH, V.max(0) + REACH
        else:
            self.tree = None

    def label(self, tri):
        return self.labels[int(np.searchsorted(self.ranges, tri, side="right"))]

    def depth(self, p):
        """(depth m, label of the nearest face, signed distance to it)."""
        loc, nrm, idx, dist = self.tree.find_nearest(p, REACH)
        if loc is None:
            return 0.0, None, REACH
        sd = dist if (p - loc).dot(nrm) >= 0 else -dist
        return exit_depth(self.tree, p, loc, nrm, dist), self.label(idx), sd


def chars():
    out = {}
    for rig in sorted((o for o in bpy.data.objects if o.type == "ARMATURE" and o.library is None
                       and o.override_library is not None), key=lambda o: o.name):
        kids = [o for o in bpy.data.objects if o.type == "MESH" and (o.parent == rig or any(
            m.type == "ARMATURE" and m.object == rig for m in o.modifiers))]
        name = rig.name[4:] if rig.name.startswith("rig_") else rig.name
        out[name] = {"rig": rig, "hair": sorted((o for o in kids if o.name.startswith("hair_")), key=lambda o: o.name),
                     "figure": sorted((o for o in kids if is_figure(o, rig)), key=lambda o: o.name),
                     "glasses": sorted((o for o in kids if o.name.startswith("glasses")), key=lambda o: o.name)}
    return out


def hair_points(objs, deps):
    out = []
    for o in objs:
        e = o.evaluated_get(deps)
        me = e.to_mesh()
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        M = np.array(e.matrix_world)
        out.append(co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3])
        e.to_mesh_clear()
    return out


def rest_state(C):
    """Rest depths of every hair vertex against its own figure (rest pose: actions off, pose bones identity)."""
    rest = {}
    for n, c in C.items():
        rig = c["rig"]
        ad = rig.animation_data
        act = ad.action if ad else None
        if ad:
            ad.action = None
        saved = [(pb, pb.location.copy(), pb.rotation_quaternion.copy(), pb.rotation_euler.copy(), pb.scale.copy())
                 for pb in rig.pose.bones]
        for pb in rig.pose.bones:
            pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
            pb.rotation_euler = (0, 0, 0)
        faces = {k: rig[k] for k in rig.keys() if k.startswith("face_")}
        for k in faces:  # facial controls at rest (they keep the last evaluated frame's value with the action off)
            rig[k] = 0.0
        rig.update_tag()
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        S = Surfaces([(f"own:{o.name}", o) for o in c["figure"]], deps)
        R = []
        for P in hair_points(c["hair"], deps):
            r = np.zeros(len(P))
            lab = [None] * len(P)
            sd = np.full(len(P), REACH)
            inb = np.all((P > S.lo) & (P < S.hi), axis=1) if S.tree else np.zeros(len(P), bool)
            for i in np.nonzero(inb)[0]:
                r[i], lab[i], sd[i] = S.depth(Vector(P[i]))
            R.append((r, lab, sd))
        rest[n] = R
        for pb, l, q, e, s in saved:
            pb.location, pb.rotation_quaternion, pb.rotation_euler, pb.scale = l, q, e, s
        for k, v in faces.items():
            rig[k] = v
        if ad:
            ad.action = act
    bpy.context.view_layer.update()
    return rest


def measure(frames, only):
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    sc = bpy.context.scene
    C = chars()
    names = [n for n in C if not only or n in only]
    props = sorted((o for o in bpy.data.objects if o.type == "MESH" and (o.name.startswith("prop.")
                    or o.name.startswith("ps_pushout.cap."))), key=lambda o: o.name)
    rest = rest_state({n: C[n] for n in names})
    rows, prev = [], {}
    h = hashlib.sha256()
    for f in frames:
        sc.frame_set(f)
        deps = bpy.context.evaluated_depsgraph_get()
        objs = [(f"{n}:{o.name}", o) for n in sorted(C) for o in C[n]["figure"]]
        objs += [(f"prop:{o.name}", o) for o in props]
        S = Surfaces(objs, deps)
        G = Surfaces([(f"{n}:glasses", o) for n in sorted(C) for o in C[n]["glasses"]], deps)
        row = {"frame": f, "chars": {}}
        for n in names:
            pts = hair_points(C[n]["hair"], deps)
            for P in pts:
                h.update(P.astype(np.float32).tobytes())
            jump = 0.0
            if n in prev:
                jump = max((float(np.linalg.norm(a - b, axis=1).max()) for a, b in zip(pts, prev[n]) if len(a)), default=0.0)
            prev[n] = pts
            surf = {}
            for oi, (o, P) in enumerate(zip(C[n]["hair"], pts)):
                rr, rl, rsd = rest[n][oi]
                inb = np.all((P > S.lo) & (P < S.hi), axis=1)
                for i in np.nonzero(inb)[0]:
                    p = Vector(P[i])
                    d, lab, sd = S.depth(p)
                    if d <= LIMIT or lab is None:
                        continue
                    own_lab = lab.split(":", 1)[1] if lab.startswith(f"{n}:") else None
                    if rr[i] > 0:  # embedded at rest: only beyond the rest depth, not where it sits as modelled
                        if own_lab is not None and rl[i] == f"own:{own_lab}" and abs(sd - rsd[i]) < REST_MATCH:
                            continue
                        d -= rr[i]
                        if d <= LIMIT:
                            continue
                    key = (lab.replace(f"{n}:", "own:", 1) if own_lab else lab)
                    s = surf.setdefault(f"{o.name} > {key}", [0, 0.0])
                    s[0] += 1
                    s[1] = max(s[1], d)
                if G.tree is not None:
                    ing = np.all((P > G.lo) & (P < G.hi), axis=1)
                    for i in np.nonzero(ing)[0]:
                        d, lab, _sd = G.depth(Vector(P[i]))
                        if d > LIMIT:
                            s = surf.setdefault(f"{o.name} > {lab}", [0, 0.0])
                            s[0] += 1
                            s[1] = max(s[1], d)
            row["chars"][n] = {"jump_mm": round(jump * 1e3, 2),
                               "surfaces": {k: [v[0], round(v[1] * 1e3, 2)] for k, v in sorted(surf.items())}}
        rows.append(row)
        print(f"[measure_eval] f{f}", json.dumps({n: (r["jump_mm"], sum(v[0] for v in r["surfaces"].values()))
                                                for n, r in row["chars"].items()}), flush=True)
    return rows, h.hexdigest()


def summarise(rows):
    out = {}
    for r in rows:
        for n, c in r["chars"].items():
            o = out.setdefault(n, {"frames": 0, "frames_over": 0, "max_mm": 0.0, "surfaces": {}})
            o["frames"] += 1
            o["frames_over"] += bool(c["surfaces"])
            for k, (cnt, mm) in c["surfaces"].items():
                part = k.split(" > ", 1)[1]
                s = o["surfaces"].setdefault(part, {"frames": 0, "max_mm": 0.0, "max_vertices": 0, "worst_frame": None,
                                                     "hair": {}})
                s["frames"] += 1
                if mm > s["max_mm"]:
                    s["max_mm"], s["worst_frame"] = mm, r["frame"]
                s["max_vertices"] = max(s["max_vertices"], cnt)
                hk = k.split(" > ", 1)[0]
                s["hair"][hk] = max(s["hair"].get(hk, 0.0), mm)
                o["max_mm"] = max(o["max_mm"], mm)
    return out


def main():
    t0 = time.time()
    a, b = (int(x) for x in opt("frames", "0-0").split("-"))
    if a == 0 and b == 0:
        bpy.ops.wm.open_mainfile(filepath=BLEND)
        a, b = bpy.context.scene.frame_start, bpy.context.scene.frame_end
    step = int(opt("step", "1"))
    only = [x for x in opt("characters", "").split(",") if x]
    jobs = int(opt("jobs", "1"))
    frames = list(range(a, b + 1, step))
    if jobs > 1 and opt("part") is None:  # split into contiguous chunks, one Blender each
        chunks = [frames[k * len(frames) // jobs:(k + 1) * len(frames) // jobs] for k in range(jobs)]
        procs = []
        for k, ch in enumerate(chunks):
            if not ch:
                continue
            o = f"{OUT}.part{k}"
            cmd = ["python3", BPY, "-b", "--factory-startup", "-P",
                   os.path.abspath(__file__), "--", BLEND, o, f"--frames={ch[0]}-{ch[-1]}", f"--step={step}",
                   f"--limit-mm={LIMIT * 1000}", f"--characters={','.join(only)}", "--part=1"]
            procs.append((o, subprocess.Popen(cmd, stdout=subprocess.DEVNULL)))
        rows, hashes = [], []
        for o, p in procs:
            if p.wait() != 0:
                raise SystemExit(f"part {o} failed")
            d = json.load(open(o))
            rows += d["rows"]
            hashes.append(d["sha256"])
            os.remove(o)
        sha = hashlib.sha256("".join(hashes).encode()).hexdigest()
    else:
        rows, sha = measure(frames, only)
    json.dump({"blend": os.path.abspath(BLEND), "frames": [a, b], "step": step, "limit_mm": LIMIT * 1000,
               "sha256": sha, "seconds": round(time.time() - t0, 1), "summary": summarise(rows), "rows": rows},
              open(OUT, "w"), indent=1)
    print("[measure_eval] done", json.dumps({"sha256": sha, "seconds": round(time.time() - t0, 1)}))


main()
