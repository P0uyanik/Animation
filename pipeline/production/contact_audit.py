"""Per-shot contact audit (T-218): penetrations between the REAL evaluated meshes of a shot, per frame and per pair
class. An audit only: it opens or builds a shot.blend, evaluates it and writes a report; it changes no shot, asset,
bake or engine file.

    python3 pipeline/production/contact_audit.py audit (--blend <shot.blend> | --run-dir <run dir> | --package <dir>)
        --out <audit.json> [--md <audit.md>] [--bake <bake.json>] [--frames A-B] [--step N] [--jobs N]
        [--limit-mm 1] [--pop-mm 5] [--staging-mm 4] [--known <known.json>] [--classes a,b,...]
        [--hair-pushout on|<spec>] [--work <dir>] [--blender <blender>] [--profile <rig profile>]
    python3 pipeline/production/contact_audit.py compare <A.json> <B.json> [--md <out.md>] [--json <out.json>]

Inputs. --blend: a shot.blend written by pipeline/charsys/shot_render.py (--blend-only or a render); its bake is
read from the shot_render.json beside it (or --bake). --run-dir: a run_shot.py run folder (bake.json; its cast.json
is the shot's build/cast.json); --package: a bake package folder (pipeline/production/bake_package.py: bake.json,
cast.json). Without a shot.blend in the run folder the blend is built into --work with shot_render --blend-only
(--hair-pushout forwarded), so the audit sees exactly what the renderer would.

Roles come from object metadata, never from character names (shared-systems rule):
  character  every armature that deforms meshes (library rigs of a shot; the name without "rig_")
  hair       hair_pushout.is_hair (the push-out's own rule)
  garment    a mesh with the `ps_garment_item` property
  solid      the unmasked collision proxies (`ps_collision_proxy`, hidden) plus the body meshes without a MASK modifier;
             the rendered body skin is masked away under the garments, so garment and body tests use these closed
             solids (fallback: the rendered body meshes)
  body       every other rendered mesh deformed by the rig, except the face parts of hair_pushout.SKIP (eyes, brows,
             lashes, lids, mouth, glasses)
  glasses    the glasses* part (not a collider in the push-out; its own apart line)
  hands      solid vertices whose dominant deform bone is the rig profile's hand.L / hand.R bone or below
  set        the bake's box objects (bake["objects"], e.g. floor, walls, stools); props = the bake's props
Hidden helper objects (push-out caps and anchor proxies, widgets) are never surfaces.

Pair classes (query vertices -> surfaces):
  hair_own      hair -> own body + garments (rendered; T-194 measure rules, below)
  hair_other    hair -> the other characters' body + garments; an entry deeper than --staging-mm in another
                character's BODY is listed apart as staging_hair (heads / bodies overlap: staging, T-191)
  hair_prop     hair -> props;  hair_set: hair -> set boxes;  glasses (apart): hair -> any glasses
  garment_body  own garment vertices -> own solid body (body through the cloth; the input of L1)
  body_body     solid body of A -> solid body of B (staging; per ordered pair)
  hand_prop     hand vertices -> props
  body_set      rendered body and garment vertices -> set boxes (exact box test)
Hair tests use one tree over all characters' figures, props and boxes (the nearest face names the class), as the
T-194 measure did; the other classes use one tree per surface set.

Depth, hair and hand_prop (surfaces may be open shells: garments, paper props): T-183 tools/measure_body.py rules, as
in T-194 tools/measure_eval.py: exit distance towards / away from the nearest surface, else the second shortest of 26
fixed directions; "under the face" and "enclosed" rules. Depth, garment_body and body_body (closed solids): behind the
nearest face = inside, depth = the distance to it (the "enclosed" rule would count a sleeve between a folded forearm
and the chest, outside both, as 60 mm deep: e912 s020 f29). For hair_own
and garment_body, vertices embedded at REST (rest pose, actions off, face controls at 0) count only by what they are
deeper than at rest, and not at all where they sit at their rest distance from the same part. A vertex counts when
deeper than --limit-mm.

Per class the report gives frame x character entries over the limit (all / calm / snap frames), distinct frames, max
depth and worst frame, and depth pops (a (character, query object > surface) depth that changes by more than --pop-mm
between two measured frames). Calm = not a body-snap frame +-1 (a bone of head / chest / arms / hands turns > 45 deg
or moves > 100 mm in one frame in the bake, as T-183 tools/snaps.py). Per character and query role the largest
frame-to-frame vertex move is kept for `compare` (T-194 pops: frames where run B adds > --pop-mm to it).
--known lists accepted cases moved apart with a label: {"apart": [{"label": ..., "class": glob, "character": glob,
"query": glob, "surface": glob}]} (data, per production; this file names no character).

Deterministic: fixed object, frame and vertex order; a SHA-256 per frame over every evaluated query position
(float32), and one over the frame hashes in frame order (independent of --jobs). Seconds are reported apart."""
import argparse
import fnmatch
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import hair_pushout as HP  # noqa: E402  (read-only reuse: is_hair, SKIP, object_triangles, bvh_of, enclosed, DIRS, CAP)

FORMAT = "plush.contact_audit/1"
CLASSES = ["hair_own", "hair_other", "hair_prop", "hair_set", "garment_body", "body_body", "hand_prop", "body_set"]
APART = ["staging_hair", "glasses"]
HAIR_CLASSES = ["hair_own", "hair_other", "hair_prop", "hair_set"]
GROUPS = {"hair vs own body / garments": ["hair_own"], "hair vs other characters": ["hair_other"],
          "body vs body (staging)": ["body_body"], "garment vs body": ["garment_body"],
          "hands vs props": ["hand_prop"], "characters vs set boxes / floor": ["hair_set", "body_set"],
          "hair vs props": ["hair_prop"]}
REACH = 0.05     # m: nearest-surface search radius
EPS = 2e-5       # m: ray restart offset of the exit walk (T-183)
UNDER = 0.7      # "under the face" rule (T-183)
REST_MATCH = 0.0005
PROFILE = os.path.join(ROOT, "pipeline", "charsys", "rig_profiles", "humanoid_rigify.json")
SNAP_BONES = ["head", "chest", "upperArm.L", "upperArm.R", "forearm.L", "forearm.R", "hand.L", "hand.R"]


# ====================================================================================== plain Python (no bpy) ====

def snap_frames(bake_path, deg=45.0, mm=100.0):
    """Frames where a body bone of any character snaps (T-183 tools/snaps.py rule) -> sorted list; [] if unreadable."""
    try:
        sys.path.insert(0, os.path.join(ROOT, "tools", "motion_checks"))
        import shot as S
        sh = S.Shot(bake_path)
    except (Exception, SystemExit):  # noqa: BLE001  (not a full bake, e.g. a synthetic test: no snap list)
        return []
    out = set()
    for c in sh.characters:
        idx = {b: i for i, b in enumerate(c.bones)}
        piv = c.pivots()
        for bn in SNAP_BONES:
            if bn not in idx:
                continue
            R = c.M[:, idx[bn], :3, :3]
            tr = np.einsum("fji,fjk->fik", R[:-1], R[1:]).trace(axis1=1, axis2=2)
            ang = np.degrees(np.arccos(np.clip((tr - 1) / 2, -1, 1)))
            d = np.linalg.norm(np.diff(piv[:, idx[bn]], axis=0), axis=1) * 1000
            out.update(int(sh.frames[i + 1]) for i in np.nonzero((ang > deg) | (d > mm))[0])
    return sorted(out)


def load_known(path):
    if not path:
        return []
    d = json.load(open(path, encoding="utf-8"))
    rules = d.get("apart", [])
    for r in rules:
        bad = sorted(set(r) - {"label", "class", "character", "query", "surface", "note"})
        if bad or "label" not in r:
            raise SystemExit(f"{path}: a known rule needs a label and only class/character/query/surface ({bad})")
    return rules


def known_label(rules, cls, char, key):
    q, _, s = key.partition(" > ")
    for r in rules:
        if all(fnmatch.fnmatchcase(v, r.get(k, "*")) for k, v in
               (("class", cls), ("character", char), ("query", q), ("surface", s))):
            return r["label"]
    return None


def classify_rows(rows, known, staging_mm):
    """Yields (frame, class, character, key, count, mm) with apart classes resolved (staging, known labels)."""
    for r in rows:
        for cls, chars in r["classes"].items():
            for ch, entries in chars.items():
                for key, (cnt, mm) in entries.items():
                    c = cls
                    surf = key.partition(" > ")[2]
                    if cls == "hair_other" and surf.split(":")[1:2] == ["body"] and mm > staging_mm:
                        c = "staging_hair"
                    lab = known_label(known, c, ch, key)
                    if lab:
                        c = f"known:{lab}"
                    yield r["frame"], c, ch, key, cnt, mm


def summarise(doc, known=(), staging_mm=4.0, pop_mm=5.0):
    """Per class and the hair aggregate (T-194 headline): entries over the limit, max depth, worst, depth pops."""
    rows = doc["rows"]
    limit = doc["limit_mm"]
    near = {f + d for f in doc.get("snap_frames", []) for d in (-1, 0, 1)}
    frames = [r["frame"] for r in rows]
    chars = doc["characters"]
    per = {}       # (class, frame, char) -> (worst mm, key)
    depth = {}     # (class, char, key) -> {frame: mm}
    for f, c, ch, key, _cnt, mm in classify_rows(rows, known, staging_mm):
        if mm > per.get((c, f, ch), (0.0, None))[0]:
            per[(c, f, ch)] = (mm, key)
        depth.setdefault((c, ch, key), {})[f] = mm
    for (c, f, ch), v in list(per.items()):  # the hair aggregate: worst over the hair classes that are not apart
        if c in HAIR_CLASSES and v[0] > per.get(("hair", f, ch), (0.0, None))[0]:
            per[("hair", f, ch)] = (v[0], f"{c} {v[1]}")
    names = sorted({k[0] for k in per} | set(CLASSES) | {"hair"})
    out = {}
    for c in names:
        s = {"entries": len(frames) * len(chars), "cols": {}, "frames_over": 0, "max_mm": 0.0, "worst": None,
             "pops": {"count": 0, "max_mm": 0.0, "list": []}}
        over_frames = set()
        for col in ("all", "calm", "snap"):
            s["cols"][col] = {"entries": 0, "over": 0, "max_mm": 0.0, "worst": None}
        for f in frames:
            for ch in chars:
                mm, key = per.get((c, f, ch), (0.0, None))
                for col in ("all", "snap" if f in near else "calm"):
                    t = s["cols"][col]
                    t["entries"] += 1
                    if mm > limit:
                        t["over"] += 1
                    if mm > t["max_mm"]:
                        t["max_mm"], t["worst"] = mm, {"frame": f, "character": ch, "key": key}
                if mm > limit:
                    over_frames.add(f)
        s["frames_over"] = len(over_frames)
        s["max_mm"], s["worst"] = s["cols"]["all"]["max_mm"], s["cols"]["all"]["worst"]
        if c != "hair":
            for (cc, ch, key), fm in sorted(depth.items()):
                if cc != c:
                    continue
                prev = None
                for f in frames:
                    d = fm.get(f, 0.0)
                    if prev is not None and abs(d - prev) > pop_mm:
                        s["pops"]["count"] += 1
                        s["pops"]["max_mm"] = max(s["pops"]["max_mm"], round(abs(d - prev), 2))
                        s["pops"]["list"].append({"frame": f, "character": ch, "key": key, "from_mm": prev, "to_mm": d,
                                                  "snap": f in near})
                    prev = d
            s["pops"]["list"] = sorted(s["pops"]["list"], key=lambda p: -abs(p["to_mm"] - p["from_mm"]))[:20]
        out[c] = s
    return out


def jump_pops(a, b, pop_mm=5.0, role="hair"):
    """T-194 pops: frame x character entries where run b adds more than pop_mm to the largest vertex move of `role`."""
    ja = {(r["frame"], ch): v.get(role, 0.0) for r in a["rows"] for ch, v in r["jump_mm"].items()}
    res = {"count": 0, "max_added_mm": 0.0, "list": []}
    for r in b["rows"]:
        for ch, v in r["jump_mm"].items():
            add = v.get(role, 0.0) - ja.get((r["frame"], ch), 0.0)
            if add > pop_mm:
                res["count"] += 1
                res["list"].append({"frame": r["frame"], "character": ch, "added_mm": round(add, 2)})
            res["max_added_mm"] = max(res["max_added_mm"], round(add, 2))
    return res


def markdown(doc):
    s = doc["summary"]
    lines = [f"# Contact audit: {os.path.basename(os.path.dirname(doc['blend']))}/{os.path.basename(doc['blend'])}", "",
             f"Frames {doc['frames'][0]}-{doc['frames'][1]} step {doc['step']} ({len(doc['rows'])} measured, "
             f"{len(doc['characters'])} characters: {', '.join(doc['characters'])}); limit {doc['limit_mm']} mm, "
             f"pops > {doc['pop_mm']} mm; snap frames {doc.get('snap_frames', [])}; {doc['seconds']} s; "
             f"sha256 {doc['sha256'][:16]}.", "",
             "| class | entries > limit (all) | calm | max mm | worst | depth pops |", "|---|---|---|---|---|---|"]
    for c in ["hair"] + CLASSES + sorted(k for k in s if k not in CLASSES and k != "hair"):
        if c not in s:
            continue
        v = s[c]
        w = v["worst"]
        ws = f"f{w['frame']} {w['character']} {w['key']}" if w else ""
        lines.append(f"| {c} | {v['cols']['all']['over']} / {v['cols']['all']['entries']} | "
                     f"{v['cols']['calm']['over']} / {v['cols']['calm']['entries']} | {v['max_mm']} | {ws} | "
                     f"{v['pops']['count']} (max {v['pops']['max_mm']}) |")
    lines += ["", "`hair` = the worst of hair_own / hair_other / hair_prop / hair_set per frame and character (T-194 "
              "headline); staging_hair, glasses and known:* are apart.", ""]
    return "\n".join(lines)


def compare(a, b, pop_mm=5.0):
    """Off / on table of two audits of the same shot and frames (T-194 summarise.py figures)."""
    sa, sb = a["summary"], b["summary"]
    out = {"a": a["blend"], "b": b["blend"], "classes": {}, "pops_b_vs_a": jump_pops(a, b, pop_mm),
           "new_keys_b": {}}
    for c in sorted(set(sa) | set(sb)):
        out["classes"][c] = {k: {"calm_over": s.get(c, {}).get("cols", {}).get("calm", {}).get("over", 0),
                                 "calm_entries": s.get(c, {}).get("cols", {}).get("calm", {}).get("entries", 0),
                                 "all_over": s.get(c, {}).get("cols", {}).get("all", {}).get("over", 0),
                                 "max_calm_mm": s.get(c, {}).get("cols", {}).get("calm", {}).get("max_mm", 0.0),
                                 "max_mm": s.get(c, {}).get("max_mm", 0.0), "frames_over": s.get(c, {}).get(
                                     "frames_over", 0)} for k, s in (("a", sa), ("b", sb))}
    known = load_known(a.get("known"))
    keys = lambda d: {(c, ch, k) for _f, c, ch, k, _n, mm in classify_rows(  # noqa: E731
        d["rows"], known, d["staging_mm"]) if mm > d["limit_mm"] and c in CLASSES}
    ka = keys(a)
    for c, ch, k in sorted(keys(b) - ka):
        out["new_keys_b"].setdefault(c, []).append(f"{ch} {k}")
    return out


def compare_markdown(cmp):
    lines = ["| class | A calm > limit | A max calm | B calm > limit | B max calm |", "|---|---|---|---|---|"]
    for c, v in cmp["classes"].items():
        lines.append(f"| {c} | {v['a']['calm_over']} / {v['a']['calm_entries']} | {v['a']['max_calm_mm']} | "
                     f"{v['b']['calm_over']} / {v['b']['calm_entries']} | {v['b']['max_calm_mm']} |")
    p = cmp["pops_b_vs_a"]
    lines += ["", f"Pops (B adds > 5 mm to the largest hair vertex move): {p['count']}, "
              f"largest +{p['max_added_mm']} mm.",
              f"New keys in B: {json.dumps(cmp['new_keys_b'])}", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------- the front end ----

def resolve_inputs(a):
    """-> (blend path or None, bake path, cast path or None, cwd for shot_render)."""
    if a.blend:
        bake = a.bake
        sr = os.path.join(os.path.dirname(os.path.abspath(a.blend)), "shot_render.json")
        if not bake and os.path.isfile(sr):
            bake = json.load(open(sr)).get("bake")
        return os.path.abspath(a.blend), bake, None, None
    if a.run_dir:
        rd = os.path.abspath(a.run_dir)
        blend = os.path.join(rd, "shot.blend")
        cast = os.path.join(rd, "..", "..", "cast.json")
        return (blend if os.path.isfile(blend) else None), os.path.join(rd, "bake.json"), os.path.abspath(cast), None
    pk = os.path.abspath(a.package)
    return None, os.path.join(pk, "bake.json"), os.path.join(pk, "cast.json"), pk


def build_blend(a, bake, cast, cwd, work):
    os.makedirs(work, exist_ok=True)
    cmd = shlex.split(a.blender) + ["-b", "--factory-startup", "-P",
                                    os.path.join(ROOT, "pipeline", "charsys", "shot_render.py"), "--", "--bake", bake,
                                    "--cast", cast, "--out", work, "--blend-only"]
    if a.hair_pushout:
        cmd += ["--hair-pushout", a.hair_pushout]
    with open(os.path.join(work, "shot_render.log"), "w") as log:
        if subprocess.call(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=cwd) != 0:
            raise SystemExit(f"shot_render --blend-only failed (log: {work}/shot_render.log)")
    return os.path.join(work, "shot.blend")


def run_audit(a):
    t0 = time.time()
    blend, bake, cast, cwd = resolve_inputs(a)
    if blend is None:
        blend = build_blend(a, bake, cast, cwd, a.work or tempfile.mkdtemp(prefix="contact_audit_"))
    known = load_known(a.known)
    with tempfile.TemporaryDirectory(prefix="contact_audit_parts_") as tmp:
        info = os.path.join(tmp, "info.json")
        _blender_part(a, blend, bake, info, frames=None)
        meta = json.load(open(info))
        lo, hi = (int(x) for x in a.frames.split("-")) if a.frames else meta["scene_frames"]
        frames = list(range(lo, hi + 1, a.step))
        jobs = max(1, min(a.jobs, len(frames)))
        chunks = [frames[k * len(frames) // jobs:(k + 1) * len(frames) // jobs] for k in range(jobs)]
        procs = []
        for k, ch in enumerate(chunks):
            o = os.path.join(tmp, f"part{k}.json")
            warm = ch[0] - a.step if k > 0 else None  # the previous measured frame: vertex moves across chunks
            procs.append((o, _blender_part(a, blend, bake, o, frames=ch, warm=warm, wait=False)))
        rows, cost = [], {}
        for o, p in procs:
            if p.wait() != 0:
                raise SystemExit(f"audit part failed: {o}.log")
            part = json.load(open(o))
            rows += part["rows"]
            for k, v in part["seconds"].items():
                cost[k] = round(cost.get(k, 0.0) + v, 1)
    rows.sort(key=lambda r: r["frame"])
    h = hashlib.sha256("".join(r["sha256"] for r in rows).encode()).hexdigest()
    doc = {"format": FORMAT, "blend": blend, "bake": bake, "frames": [lo, hi], "step": a.step, "limit_mm": a.limit_mm,
           "pop_mm": a.pop_mm, "staging_mm": a.staging_mm, "known": os.path.abspath(a.known) if a.known else None,
           "characters": meta["characters"], "roles": meta["roles"],
           "snap_frames": ([int(x) for x in a.snap_frames.split(",") if x] if a.snap_frames is not None
                           else snap_frames(bake) if bake and os.path.isfile(bake) else []),
           "snap_frames_from": "--snap-frames" if a.snap_frames is not None else "bake", "sha256": h}
    doc["summary"] = summarise({**doc, "rows": rows}, known, a.staging_mm, a.pop_mm)
    doc["seconds"] = round(time.time() - t0, 1)
    doc["seconds_by_step"] = cost  # summed over the parts (CPU-side wall time per step, all frames)
    doc["rows"] = rows
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(doc, open(a.out, "w"), indent=1, sort_keys=False)
    if a.md:
        open(a.md, "w").write(markdown(doc))
    print(markdown(doc))
    return doc


def _blender_part(a, blend, bake, out, frames, warm=None, wait=True):
    cmd = shlex.split(a.blender) + ["-b", "--factory-startup", "-P", os.path.abspath(__file__), "--", "part",
                                    "--blend", blend, "--out", out, "--limit-mm", str(a.limit_mm), "--classes", a.classes,
                                    "--profile", a.profile]
    if bake:
        cmd += ["--bake", bake]
    if frames is None:
        cmd += ["--info"]
    else:
        cmd += ["--frame-list", ",".join(map(str, frames))] + (["--warm", str(warm)] if warm is not None else [])
    log = open(out + ".log", "w")
    p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
    if wait and p.wait() != 0:
        raise SystemExit(f"audit part failed: {out}.log")
    return p


# ============================================================================================ inside Blender ====

def _exit_along(tree, p, d, best):
    from mathutils import Vector
    t, last = 0.0, 0.0
    while True:
        hit = tree.ray_cast(Vector(p + d * (t + EPS)), Vector(d), HP.CAP - t)
        if hit[0] is None:
            return last
        t += EPS + hit[3]
        last = t
        if last >= best:
            return last


def exit_depth(tree, p, loc, nrm, dist):
    """T-183 depth of point p (numpy) given its nearest surface point loc / normal nrm at distance dist."""
    from mathutils import Vector
    off = p - loc
    if dist > 1e-7:
        if off.dot(nrm) >= 0:
            if tree.ray_cast(Vector(p), Vector(off / dist), HP.CAP)[0] is None:
                return 0.0
        elif -off.dot(nrm) >= UNDER * dist:
            d = -off / dist
            if tree.ray_cast(Vector(loc + d * EPS), Vector(d), HP.CAP)[0] is None:
                return dist if HP.enclosed(tree, p) else 0.0
    if not HP.enclosed(tree, p):
        return 0.0
    best, second = HP.CAP, HP.CAP
    for d in HP.DIRS:
        e = _exit_along(tree, p, d, second)
        if e < best:
            best, second = e, best
        elif e < second:
            second = e
        if second <= 0.0:
            return 0.0
    return second


class Surfaces:
    """One BVH over labelled objects (hair_pushout.object_triangles), with the label of every triangle."""

    def __init__(self, labelled, deps, closed=False):
        self.closed = closed
        pieces = HP.object_triangles([o for _l, o in labelled], deps)
        lab = {id(o): l for l, o in labelled}
        self.labels, ends, n = [], [], 0
        for o, _co, tri in pieces:
            n += len(tri)
            self.labels.append(lab[id(o)])
            ends.append(n)
        self.ends = np.array(ends)
        V, T = HP.concat_pieces([(co, tri) for _o, co, tri in pieces])
        self.tree = HP.bvh_of(V, T)
        self.lo, self.hi = (V.min(0) - REACH, V.max(0) + REACH) if len(V) else (None, None)

    def near(self, P):
        if self.tree is None or not len(P):
            return np.zeros(0, dtype=np.int64)
        return np.nonzero(np.all((P > self.lo) & (P < self.hi), axis=1))[0]

    def depth(self, p):
        """(depth m, label of the nearest face, signed distance to it)."""
        from mathutils import Vector
        loc, nrm, idx, dist = self.tree.find_nearest(Vector(p), REACH)
        if loc is None:
            return 0.0, None, REACH
        loc, nrm = np.array(loc), np.array(nrm)
        sd = dist if (p - loc).dot(nrm) >= 0 else -dist
        lab = self.labels[int(np.searchsorted(self.ends, idx, side="right"))]
        if self.closed:  # closed solid: inside = behind the nearest face, depth = the distance to it
            return (dist if sd < 0 else 0.0), lab, sd
        return exit_depth(self.tree, p, loc, nrm, dist), lab, sd


def points(objs, deps):
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


def scene_objects(bpy):
    """The objects of the shot: in the scene and not linked library data (a shot links each master and works on
    library overrides; the linked originals keep the master's rest state and must not be measured)."""
    return [o for o in bpy.context.scene.objects if o.library is None]


def characters(bpy, profile):
    """{name: roles} from object metadata (see the module doc)."""
    prof = json.load(open(profile)).get("roles", {})
    hand_roots = [prof[k] for k in ("hand.L", "hand.R") if k in prof]
    out = {}
    objs = scene_objects(bpy)
    rigs = [o for o in objs if o.type == "ARMATURE"]
    for rig in sorted(rigs, key=lambda o: o.name):
        kids = sorted((o for o in objs if o.type == "MESH" and any(
            m.type == "ARMATURE" and m.object == rig for m in o.modifiers)), key=lambda o: o.name)
        if not kids:
            continue
        name = rig.name[4:] if rig.name.startswith("rig_") else rig.name
        if name in out:
            raise SystemExit(f"two rigs named {rig.name} in the scene")
        proxy = [o for o in kids if o.get("ps_collision_proxy")]
        rendered = [o for o in kids if not o.hide_render and not o.name.startswith(("WGT-", HP.PREFIX))]
        hair = [o for o in rendered if HP.is_hair(o)]
        garment = [o for o in rendered if o not in hair and "ps_garment_item" in o.keys()]
        glasses = sorted((o for o in objs if o.type == "MESH" and fnmatch.fnmatchcase(o.name, "glasses*")
                          and (o.parent == rig or o in kids) and not o.hide_render), key=lambda o: o.name)
        body = [o for o in rendered if o not in hair and o not in garment
                and not any(fnmatch.fnmatchcase(o.name, p) for p in HP.SKIP)]
        solid = proxy + [o for o in body if not any(m.type == "MASK" for m in o.modifiers)] if proxy else list(body)
        hand_bones = set()
        for hb in hand_roots:
            if hb in rig.data.bones:
                b = rig.data.bones[hb]
                hand_bones |= {b.name} | {c.name for c in b.children_recursive}
        hands = {}
        for o in solid:
            gi = {g.index: g.name for g in o.vertex_groups}
            m = np.zeros(len(o.data.vertices), dtype=bool)
            for v in o.data.vertices:
                best = max(((g.weight, gi.get(g.group)) for g in v.groups), default=(0.0, None))
                m[v.index] = best[1] in hand_bones and best[0] > 0
            if m.any():
                hands[o.name] = m
        out[name] = {"rig": rig, "hair": hair, "garment": garment, "body": body, "solid": solid, "glasses": glasses,
                     "figure": sorted(body + garment, key=lambda o: o.name), "hands": hands}
    return out


def rest_depths(bpy, C, names, queries, surfaces_of):
    """Rest depths of the query vertices of every character against its own surfaces (rest pose)."""
    rest = {}
    for n in names:
        c = C[n]
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
        for k in faces:
            rig[k] = 0.0
        rig.update_tag()
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        rest[n] = {}
        for role in queries:
            S = Surfaces([(f"own:{r}:{o.name}", o) for r, o in surfaces_of(c, role)], deps, closed=role == "garment")
            R = []
            for P in points(c[role], deps):
                r, lab, sd = np.zeros(len(P)), [None] * len(P), np.full(len(P), REACH)
                for i in S.near(P):
                    r[i], lab[i], sd[i] = S.depth(P[i])
                R.append((r, lab, sd))
            rest[n][role] = R
        for pb, loc, q, e, s in saved:
            pb.location, pb.rotation_quaternion, pb.rotation_euler, pb.scale = loc, q, e, s
        for k, v in faces.items():
            rig[k] = v
        if ad:
            ad.action = act
    bpy.context.view_layer.update()
    return rest


def _role_of(c, o):
    return "garment" if o in c["garment"] else "body"


def blender_part(args):
    import bpy
    bpy.ops.wm.open_mainfile(filepath=args.blend)
    sc = bpy.context.scene
    C = characters(bpy, args.profile)
    names = sorted(C)
    bake = json.load(open(args.bake)) if args.bake and os.path.isfile(args.bake) else {"objects": []}
    box_names = {f"prop.{o['name']}" for o in bake.get("objects", [])}
    rigged = {o.name for c in C.values() for k in ("hair", "figure", "solid", "glasses") for o in c[k]}
    meshes = sorted((o for o in scene_objects(bpy) if o.type == "MESH" and not o.hide_render and o.name not in rigged
                     and not any(m.type == "ARMATURE" for m in o.modifiers)), key=lambda o: o.name)
    boxes = [o for o in meshes if o.name in box_names]
    props = [o for o in meshes if o.name.startswith("prop.") and o.name not in box_names]
    if args.info:
        roles = {n: {k: [o.name for o in c[k]] for k in ("hair", "garment", "body", "solid", "glasses")}
                 for n, c in C.items()}
        for n, c in C.items():
            roles[n]["hands"] = {k: int(v.sum()) for k, v in c["hands"].items()}
        roles["props"], roles["set"] = [o.name for o in props], [o.name for o in boxes]
        json.dump({"scene_frames": [sc.frame_start, sc.frame_end], "characters": names, "roles": roles},
                  open(args.out, "w"), indent=1)
        return
    want = set(args.classes.split(",")) if args.classes != "all" else set(CLASSES)
    limit = args.limit_mm / 1000.0
    own_surf = {"hair": lambda c: [(_role_of(c, o), o) for o in c["figure"]],
                "garment": lambda c: [("body", o) for o in c["solid"]]}
    queries = [q for q, cl in (("hair", "hair_own"), ("garment", "garment_body")) if cl in want or q == "hair"]
    cost = {}
    t = time.time()
    rest = rest_depths(bpy, C, names, queries, lambda c, role: own_surf[role](c))
    cost["rest"] = time.time() - t

    def tick(k, t0):
        cost[k] = cost.get(k, 0.0) + time.time() - t0
        return time.time()
    frames = [int(x) for x in args.frame_list.split(",")]
    todo = ([args.warm] if args.warm is not None else []) + frames
    rows, prev = [], {}
    for f in todo:
        t = time.time()
        sc.frame_set(f)
        deps = bpy.context.evaluated_depsgraph_get()
        pts = {n: {role: points(C[n][role], deps) for role in ("hair", "garment", "solid", "body")} for n in names}
        jump = {}
        for n in names:
            jump[n] = {}
            for role, P in pts[n].items():
                if (n, role) in prev:
                    jump[n][role] = round(max((float(np.linalg.norm(x - y, axis=1).max()) for x, y in
                                               zip(P, prev[(n, role)]) if len(x) and len(x) == len(y)),
                                              default=0.0) * 1e3, 2)
                prev[(n, role)] = P
        t = tick("evaluate", t)
        if f == args.warm:
            continue
        h = hashlib.sha256()
        for n in names:
            for role in ("hair", "garment", "solid", "body"):
                for P in pts[n][role]:
                    h.update(P.astype(np.float32).tobytes())
        res = {c: {} for c in CLASSES + ["glasses"]}

        def add(cls, n, key, d):
            e = res[cls].setdefault(n, {}).setdefault(key, [0, 0.0])
            e[0] += 1
            e[1] = max(e[1], d)

        # hair: one tree over every figure, the props and the boxes; the nearest face names the class
        lab = [(f"{n}:{_role_of(C[n], o)}:{o.name}", o) for n in names for o in C[n]["figure"]]
        lab += [(f"prop::{o.name}", o) for o in props] + [(f"set::{o.name}", o) for o in boxes]
        S = Surfaces(lab, deps)
        G = Surfaces([(f"{n}:glasses:{o.name}", o) for n in names for o in C[n]["glasses"]], deps)
        for n in (names if want & set(HAIR_CLASSES) else []):
            for oi, (o, P) in enumerate(zip(C[n]["hair"], pts[n]["hair"])):
                rr, rl, rsd = rest[n]["hair"][oi]
                for i in S.near(P):
                    d, lb, sd = S.depth(P[i])
                    if d <= limit or lb is None:
                        continue
                    own = lb.startswith(f"{n}:")
                    if rr[i] > 0:  # embedded at rest: only beyond the rest depth, not where it sits as modelled
                        if own and rl[i] == "own:" + lb.split(":", 1)[1] and abs(sd - rsd[i]) < REST_MATCH:
                            continue
                        d -= rr[i]
                        if d <= limit:
                            continue
                    kind = lb.split(":", 1)[0]
                    cls = ("hair_own" if own else "hair_prop" if kind == "prop" else "hair_set" if kind == "set"
                           else "hair_other")
                    if cls in want:
                        add(cls, n, f"{o.name} > {'own:' + lb.split(':', 1)[1] if own else lb}", d * 1e3)
                for i in G.near(P):
                    d, lb, _sd = G.depth(P[i])
                    if d > limit:
                        add("glasses", n, f"{o.name} > {lb.replace(n + ':', 'own:', 1)}", d * 1e3)
        t = tick("hair", t)
        solid = {n: Surfaces([(f"{n}:body:{o.name}", o) for o in C[n]["solid"]], deps, closed=True) for n in names}
        if "garment_body" in want:
            for n in names:
                for oi, (o, P) in enumerate(zip(C[n]["garment"], pts[n]["garment"])):
                    rr, rl, rsd = rest[n]["garment"][oi]
                    T = solid[n]
                    for i in T.near(P):
                        d, lb, sd = T.depth(P[i])
                        if d <= limit or lb is None:
                            continue
                        if rr[i] > 0:
                            if rl[i] == "own:" + lb.split(":", 1)[1] and abs(sd - rsd[i]) < REST_MATCH:
                                continue
                            d -= rr[i]
                            if d <= limit:
                                continue
                        add("garment_body", n, f"{o.name} > own:{lb.split(':', 1)[1]}", d * 1e3)
        t = tick("garment_body", t)
        if "body_body" in want:
            for n in names:
                for m in names:
                    if m == n or solid[m].tree is None:
                        continue
                    for o, P in zip(C[n]["solid"], pts[n]["solid"]):
                        for i in solid[m].near(P):
                            d, lb, _sd = solid[m].depth(P[i])
                            if d > limit and lb is not None:
                                add("body_body", n, f"{o.name} > {lb}", d * 1e3)
        t = tick("body_body", t)
        if "hand_prop" in want and props:
            PS = Surfaces([(f"prop::{o.name}", o) for o in props], deps)
            for n in names:
                for o, P in zip(C[n]["solid"], pts[n]["solid"]):
                    m = C[n]["hands"].get(o.name)
                    if m is None or len(m) != len(P):
                        continue
                    for i in PS.near(P):
                        if not m[i]:
                            continue
                        d, lb, _sd = PS.depth(P[i])
                        if d > limit and lb is not None:
                            add("hand_prop", n, f"{o.name} > {lb}", d * 1e3)
        t = tick("hand_prop", t)
        if "body_set" in want and boxes:
            bx = [(o.name, Q.min(0), Q.max(0)) for o, Q in zip(boxes, points(boxes, deps)) if len(Q)]
            for n in names:
                for o, P in zip(C[n]["body"] + C[n]["garment"], pts[n]["body"] + pts[n]["garment"]):
                    for bn, lo, hi in bx:
                        inside = np.all((P > lo) & (P < hi), axis=1)
                        if inside.any():
                            d = np.minimum(P[inside] - lo, hi - P[inside]).min(axis=1)
                            d = d[d > limit]
                            if len(d):
                                e = res["body_set"].setdefault(n, {}).setdefault(f"{o.name} > set::{bn}", [0, 0.0])
                                e[0] += int(len(d))
                                e[1] = max(e[1], float(d.max()) * 1e3)
        t = tick("body_set", t)
        row = {"frame": f, "sha256": h.hexdigest(), "jump_mm": jump,
               "classes": {c: {n: {k: [v[0], round(v[1], 2)] for k, v in sorted(e.items())}
                               for n, e in sorted(res[c].items())} for c in res if res[c]}}
        rows.append(row)
        counts = {c: sum(len(e) for e in v.values()) for c, v in row["classes"].items()}
        print(f"[contact_audit] f{f}", json.dumps(counts), flush=True)
    json.dump({"rows": rows, "seconds": {k: round(v, 1) for k, v in cost.items()}}, open(args.out, "w"))


# ===================================================================================================== CLI ====

def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    au = sub.add_parser("audit")
    src = au.add_mutually_exclusive_group(required=True)
    src.add_argument("--blend")
    src.add_argument("--run-dir")
    src.add_argument("--package")
    au.add_argument("--out", required=True)
    au.add_argument("--md")
    au.add_argument("--bake")
    au.add_argument("--frames", default="")
    au.add_argument("--step", type=int, default=1)
    au.add_argument("--jobs", type=int, default=1)
    au.add_argument("--limit-mm", type=float, default=1.0)
    au.add_argument("--pop-mm", type=float, default=5.0)
    au.add_argument("--staging-mm", type=float, default=4.0)
    au.add_argument("--known")
    au.add_argument("--classes", default="all")
    au.add_argument("--hair-pushout")
    au.add_argument("--work")
    au.add_argument("--blender", default=os.environ.get("BLENDER", "blender"),
                    help="Blender executable or command, e.g. 'python3 tools/bpy_blender.py' (the bpy module)")
    au.add_argument("--profile", default=PROFILE)
    au.add_argument("--snap-frames", help="comma list replacing the bake's snap frames (e.g. an earlier bake's)")
    cp = sub.add_parser("compare")
    cp.add_argument("a")
    cp.add_argument("b")
    cp.add_argument("--md")
    cp.add_argument("--json")
    cp.add_argument("--pop-mm", type=float, default=5.0)
    cp.add_argument("--snap-frames", help="comma list: re-summarise both audits with these snap frames")
    pt = sub.add_parser("part")  # internal: one Blender process
    pt.add_argument("--blend", required=True)
    pt.add_argument("--out", required=True)
    pt.add_argument("--bake")
    pt.add_argument("--limit-mm", type=float, default=1.0)
    pt.add_argument("--classes", default="all")
    pt.add_argument("--profile", default=PROFILE)
    pt.add_argument("--info", action="store_true")
    pt.add_argument("--frame-list", default="")
    pt.add_argument("--warm", type=int)
    a = ap.parse_args(argv)
    if a.cmd == "audit":
        if a.classes != "all" and not set(a.classes.split(",")) <= set(CLASSES):
            ap.error(f"--classes: one or more of {CLASSES}")
        run_audit(a)
    elif a.cmd == "compare":
        A, B = json.load(open(a.a)), json.load(open(a.b))
        if a.snap_frames is not None:
            for d in (A, B):
                d["snap_frames"] = [int(x) for x in a.snap_frames.split(",") if x]
                d["summary"] = summarise(d, load_known(d.get("known")), d["staging_mm"], d["pop_mm"])
        res = compare(A, B, a.pop_mm)
        if a.json:
            json.dump(res, open(a.json, "w"), indent=1)
        md = compare_markdown(res)
        if a.md:
            open(a.md, "w").write(md)
        print(md)
    else:
        blender_part(a)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
