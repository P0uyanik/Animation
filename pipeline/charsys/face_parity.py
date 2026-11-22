"""Face export parity, knob-free master check and Blender build pin (T-213; face plan P5a, docs/research/T-212).

Acceptance tooling for the face plan, run BEFORE and AFTER every face fit / bake (P2-P6). For a character master it
checks three things and writes one JSON report:

1. **Export parity.** The engine package (export_engine.py, run in-process on the master, or an existing package via
   --package) is reconstructed the way the engine does it (rest positions + sum of weight x morph delta, in-between
   chains expanded like engine/model/character.cpp expandInbetweens) and compared, vertex by vertex, with what
   Blender evaluates for the same controls (face_* properties on the rig, drivers live, every modifier live, rig in
   REST position as the exporter does it). Also compares every raw key-minus-Basis delta with the exported delta.
   Expressions: neutral, half-blink (Blink 0.5), smile+blink (Smile 1 + Blink 1), plus a sweep (every face control
   alone at 1.0 and every in-between chain at two between-stop weights). Corrective keys (drivers not fed by face_*
   controls only, e.g. corrective.reach.*) are checked to be 0 in Blender at every tested expression (the engine
   never drives them); a combination corrective (fed by two or more face_* controls) is reported and makes parity
   fail, because the engine has no combination logic.
   Pass = every coordinate within the export quantization bound (quant_bound(); docs/evaluation/characters/T-213).
   The verdict ("pass") gates on rest, raw deltas, combination correctives and the three core expressions; the
   sweep has its own verdict ("sweep_pass"), reported always and gating with --strict. "chain_gaps" names objects
   whose base key has no in-between keys (the engine then keeps that block at 0 below the last stop).
2. **Knob-free master.** Objects carrying face keys may have only ARMATURE and (vertex-group) MASK modifiers, with
   identical viewport/render switches; no fit helper (Warp, Hook, Lattice, Surface Deform, Geometry Nodes, ...)
   may be left live (T-211 risk a). Face keys must be relative to Basis, unmuted and without a vertex group (the
   exporter writes raw key-minus-Basis deltas). No Lattice object may remain in the character collection.
3. **Blender build pin.** BLENDER_PIN is the build the parity numbers were measured on. Another build fails loudly
   (exit 3) so parity is re-run on upgrades. Intentional upgrade: run with --accept-blender <version>+<hash> (or
   env PS_FACE_PARITY_ACCEPT_BLENDER) on all masters; when they pass, change BLENDER_PIN in a reviewed commit.

Usage (headless; read-only on the masters, nothing is saved):
    blender -b --factory-startup -P pipeline/charsys/face_parity.py -- \
        (--character <id> [--version X] | --blend <master.blend> | --all) [--package <dir>] [--out report.json]
Exit codes: 0 pass, 1 a check failed, 2 usage / export error, 3 Blender build differs from the pin.
From other Blender scripts (P2-P6): `import face_parity as FP; rep = FP.run_master(path)`; rep["pass"].

The pure helpers (expand_inbetweens, quant_bound, check_pin, classify_modifiers, key_rule_problems) need neither
bpy nor numpy (tests/test_face_parity.py runs them in the plain Python tests step).
"""
import json
import math
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
PROFILE = os.path.join(HERE, "rig_profiles", "humanoid_rigify.json")
SCHEMA = "plush-studio.face-parity/1"

# Blender build the T-213 numbers were measured on (docs/evaluation/characters/T-213/README.md). The owner's
# production Blender (T-212 replay) and the gate's bpy wheel report the same build.
BLENDER_PIN = {"version": "5.3.0", "build_hash": "02f0899d78e3"}
PIN_ENV = "PS_FACE_PARITY_ACCEPT_BLENDER"

# Modifiers allowed on an object that carries face keys. The exporter evaluates the mesh with masks off and the rig in
# REST position, so these two cannot split render and engine. Everything else (Warp, Hook, Lattice, Surface Deform,
# Geometry Nodes, Displace, Smooth, Shrinkwrap, ...) is a live deformer the engine never sees.
ALLOWED_FACE_MODIFIERS = ("ARMATURE", "MASK")
KNOB_TYPES = ("WARP", "HOOK", "LATTICE", "SURFACE_DEFORM", "NODES", "MESH_DEFORM", "CAST", "SIMPLE_DEFORM",
              "DISPLACE", "WAVE", "SMOOTH", "LAPLACIANSMOOTH", "CORRECTIVE_SMOOTH", "SHRINKWRAP")

# The three expressions T-212 (d) names, as morph-channel weights (engine names in the README).
CORE_EXPRESSIONS = (("neutral", {}), ("half_blink", {"Blink": 0.5}), ("smile_blink", {"Smile": 1.0, "Blink": 1.0}))
SWEEP_INBETWEEN_WEIGHTS = (0.375, 0.625, 0.875)  # between the stops of the 25/50/75 chains

# ---- quantization (export_engine.py) ----
GRID_M = 2.0 ** -15        # export/5 position grid (export_engine.GRID_M)
DELTA_GRID_M = 2.0 ** -14  # export/5 delta grid (export_engine.DELTA_GRID_M)
E4_DROP_M = 1e-7           # export/4 drops a delta whose norm is <= 1e-7 m


def ulp32(x):
    """Spacing of float32 numbers at |x| (x >= 0)."""
    x = abs(float(x))
    if x < 2.0 ** -126:
        return 2.0 ** -149
    return 2.0 ** (math.floor(math.log2(x)) - 23)


def quant_bound(exporter, extent_m, delta_extent_m, weight_sum):
    """Per-coordinate bound (m) of |engine reconstruction - Blender evaluation| for one vertex.

    exporter: "4" (float32, unrounded) or "5"/"6" (grids). extent_m: largest |coordinate| of the object (world),
    delta_extent_m: largest |delta coordinate| of its keys, weight_sum: sum of |weight| of the active morph blocks.
      position term  q_p: export/4 float32 rounding ulp(extent)/2;  export/5 GRID/2 (+ float32 ulp/2, exact for grids)
      delta term     q_d: export/4 drop threshold 1e-7 + float32 rounding ulp(delta extent)/2;  export/5 DELTA_GRID/2
      Blender term   q_b: Blender mixes keys and applies the REST armature in float32 on local coordinates:
                         (2 + number of active blocks) ulps at the extent (one per add, plus deform and world matrix)
    bound = q_p + weight_sum * q_d + q_b. The README states the numbers for the current masters."""
    u = ulp32(extent_m)
    if str(exporter) == "4":
        q_p, q_d = u / 2, E4_DROP_M + ulp32(delta_extent_m) / 2
    else:
        q_p, q_d = GRID_M / 2 + u / 2, DELTA_GRID_M / 2 + ulp32(delta_extent_m) / 2
    q_b = (2 + math.ceil(weight_sum)) * u
    return q_p + weight_sum * q_d + q_b


def delta_bound(exporter, delta_extent_m):
    """Per-coordinate bound (m) of |exported delta - Blender key-minus-Basis delta|."""
    if str(exporter) == "4":
        return E4_DROP_M + ulp32(delta_extent_m) / 2
    return DELTA_GRID_M / 2 + ulp32(delta_extent_m) / 2


# ---- engine weight semantics (mirror of engine/model/character.cpp expandInbetweens) ----
def expand_inbetweens(inbetweens, weights):
    """weights: morph name -> weight (base channels). inbetweens: package "morph_inbetweens" (base -> [[f, name]]).
    Returns morph name -> weight after expanding each chain (stops 0, f..., 1). Same arithmetic as the engine
    (float32 there; the difference is far below the bound)."""
    out = dict(weights)
    for base, chain in inbetweens.items():
        stops = [(0.0, None)] + [(float(f), m) for f, m in chain] + [(1.0, base)]
        for _, m in stops:
            if m is not None:
                out[m] = 0.0
        w = float(weights.get(base, 0.0))
        if w <= 0:
            continue
        if w >= 1:
            out[base] = w
            continue
        for (f0, m0), (f1, m1) in zip(stops, stops[1:]):
            if w > f1:
                continue
            t = (w - f0) / max(1e-6, f1 - f0)
            if m0 is not None:
                out[m0] += 1.0 - t
            out[m1] += t
            break
    return {k: v for k, v in out.items() if v != 0.0}


# ---- build pin ----
class PinError(RuntimeError):
    pass


def check_pin(version, build_hash, accept=None, pin=None):
    """Returns the pin record. Raises PinError when (version, build_hash) is not the pin and `accept`
    ("<version>+<hash>", from --accept-blender or PS_FACE_PARITY_ACCEPT_BLENDER) does not name exactly this build."""
    pin = pin or BLENDER_PIN
    running = {"version": version, "build_hash": build_hash}
    rec = {"pinned": dict(pin), "running": running, "override": None}
    if version == pin["version"] and build_hash == pin["build_hash"]:
        return rec
    if accept:
        v, _, h = accept.partition("+")
        if v == version and h == build_hash:
            rec["override"] = accept
            return rec
        raise PinError(f"--accept-blender {accept!r} does not name the running build {version}+{build_hash}")
    raise PinError(
        f"Blender build {version}+{build_hash} is not the face-parity pin {pin['version']}+{pin['build_hash']}. "
        f"Parity must be re-run on a Blender upgrade: run with --accept-blender {version}+{build_hash} (or "
        f"{PIN_ENV}={version}+{build_hash}) on every master; when all pass, update BLENDER_PIN in "
        f"pipeline/charsys/face_parity.py in a reviewed commit.")


# ---- knob-free master (pure part, on plain descriptors) ----
def classify_modifiers(mods):
    """mods: [{"name", "type", "show_viewport", "show_render", "mode"?}] of one face object. Returns problems."""
    out = []
    for m in mods:
        t = m["type"]
        if t not in ALLOWED_FACE_MODIFIERS:
            kind = "fit helper / knob" if t in KNOB_TYPES else "unexpected"
            out.append(f"live {kind} modifier {m['name']!r} ({t})")
        elif t == "MASK" and m.get("mode", "VERTEX_GROUP") != "VERTEX_GROUP":
            out.append(f"mask modifier {m['name']!r} in {m.get('mode')} mode (the exporter handles vertex-group masks only)")
        if bool(m.get("show_viewport", True)) != bool(m.get("show_render", True)):
            out.append(f"modifier {m['name']!r} ({t}) differs between viewport and render")
    return out


def key_rule_problems(keys, basis_name):
    """keys: [{"name", "relative_key", "vertex_group", "mute"}] (Basis excluded). The exporter writes key - Basis."""
    out = []
    for k in keys:
        if k["relative_key"] != basis_name:
            out.append(f"key {k['name']!r} is relative to {k['relative_key']!r}, not {basis_name!r}")
        if k.get("vertex_group"):
            out.append(f"key {k['name']!r} is limited by vertex group {k['vertex_group']!r}")
        if k.get("mute"):
            out.append(f"key {k['name']!r} is muted")
    return out


def master_path(character, version=None):
    d = os.path.join(ROOT, "assets", "characters", character, "versions")
    if version is None:
        version = json.load(open(os.path.join(d, "index.json")))["pointers"]["approved"]
    return os.path.join(d, version, f"{character}_master.blend"), version


def current_characters(first=None):
    """Character ids with a version store, sorted; `first` (e.g. the face-plan pilot) moves to the front."""
    base = os.path.join(ROOT, "assets", "characters")
    ids = sorted(c for c in os.listdir(base) if os.path.isfile(os.path.join(base, c, "versions", "index.json")))
    if first is not None and first not in ids:
        raise ValueError(f"--first {first!r}: no such character (have {ids})")
    return sorted(ids, key=lambda c: (c != first, c))


# =====================================================================================================================
# Blender part
# =====================================================================================================================
def _bpy():
    import bpy  # noqa: F401
    return bpy


def running_build():
    bpy = _bpy()
    h = bpy.app.build_hash
    return bpy.app.version_string, h.decode() if isinstance(h, bytes) else str(h)


def _root(bpy):
    return next((c for c in bpy.data.collections if c.get("ps_character_id")), None)


def face_controls(bpy, root):
    """face_* control -> list of (ID, data_path) the shape-key drivers read; key name -> set of controls it reads
    (None for a variable that is not a face_* property, e.g. a bone swing)."""
    controls, key_inputs, face_objects = {}, {}, []
    for o in root.all_objects:
        if o.type != "MESH" or not o.data.shape_keys:
            continue
        sk = o.data.shape_keys
        ad = sk.animation_data
        reads_face = False
        for d in (ad.drivers if ad else []):
            if not d.data_path.startswith('key_blocks["'):
                continue
            kname = d.data_path[len('key_blocks["'):].split('"]')[0]
            ins = key_inputs.setdefault((o.name, kname), set())
            for v in d.driver.variables:
                for t in v.targets:
                    p = t.data_path or ""
                    if v.type == "SINGLE_PROP" and p.startswith('["face_') and t.id is not None:
                        c = p[2:-2]
                        controls.setdefault(c, set()).add((t.id.name, t.id_type, p))
                        ins.add(c)
                        reads_face = True
                    else:
                        ins.add(None)
        if reads_face:
            face_objects.append(o)
    return controls, key_inputs, face_objects


def knob_check(bpy, root, face_objects):
    problems = {}
    for o in face_objects:
        mods = [{"name": m.name, "type": m.type, "show_viewport": m.show_viewport, "show_render": m.show_render,
                 **({"mode": m.mode} if m.type == "MASK" else {})} for m in o.modifiers]
        kb = o.data.shape_keys.key_blocks
        keys = [{"name": k.name, "relative_key": k.relative_key.name, "vertex_group": k.vertex_group, "mute": k.mute}
                for k in kb[1:]]
        p = classify_modifiers(mods) + key_rule_problems(keys, kb[0].name)
        if not o.data.shape_keys.use_relative:
            p.append("shape keys are absolute (use_relative off)")
        if p:
            problems[o.name] = p
    lattices = sorted(o.name for o in root.all_objects if o.type == "LATTICE")
    if lattices:
        problems["<collection>"] = [f"lattice object(s) left in the character: {lattices}"]
    return {"pass": not problems, "face_objects": sorted(o.name for o in face_objects),
            "allowed_modifiers": list(ALLOWED_FACE_MODIFIERS), "problems": problems}


def _set_controls(bpy, controls, values):
    for c, owners in controls.items():
        v = float(values.get(c, 0.0))
        for name, id_type, path in owners:
            coll = {"OBJECT": bpy.data.objects, "MESH": bpy.data.meshes, "ARMATURE": bpy.data.armatures,
                    "KEY": bpy.data.shape_keys}.get(id_type, bpy.data.objects)
            idb = coll[name]
            idb[c] = v
            idb.update_tag()  # a custom-property write does not tag the depsgraph; drivers would keep old values


def _evaluated_world(bpy, np, o, deps):
    ev = o.evaluated_get(deps)
    me = ev.to_mesh()
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("co", co)
    ev.to_mesh_clear()
    mw = np.array(o.matrix_world, dtype=np.float64)
    co = co.reshape(n, 3).astype(np.float64)
    return co @ mw[:3, :3].T + mw[:3, 3]


def _raw_deltas(np, o):
    kb = o.data.shape_keys.key_blocks
    n = len(o.data.vertices)

    def get(k):
        a = np.empty(n * 3, np.float32)
        k.data.foreach_get("co", a)
        return a.reshape(n, 3).astype(np.float64)
    basis = get(kb[0])
    m3 = np.array(o.matrix_world.to_3x3(), dtype=np.float64)
    return {k.name: (get(k) - basis) @ m3.T for k in kb[1:]}


def _to_engine(np, v):
    return np.stack([v[..., 0], v[..., 2], -v[..., 1]], axis=-1)


def load_package(np, pkg):
    man = json.load(open(os.path.join(pkg, "character.json")))
    blob = open(os.path.join(pkg, "geometry.bin"), "rb").read()

    def arr(d, shape_last=None):
        a = np.frombuffer(blob, dtype=np.dtype(d["dtype"]), count=d["count"], offset=d["offset"])
        return a.reshape(-1, shape_last) if shape_last else a
    by_obj = {}
    for mi, m in enumerate(man["meshes"]):
        by_obj.setdefault(m["source_object"], []).append(mi)
    meshes = [{"pos": arr(m["positions"], 3).astype(np.float64), "source": m["source_object"]} for m in man["meshes"]]
    for m in meshes:
        m["morphs"] = {}
    for mo in man["morphs"]:
        meshes[mo["mesh"]]["morphs"][mo["name"]] = (arr(mo["vertices"]).astype(np.int64),
                                                    arr(mo["dpos"], 3).astype(np.float64))
    return man, meshes, by_obj


def _match(bpy, np, eng_pos, bl_pos, eng_rec, bl_rec, radius):
    """Engine vertex -> Blender vertex (engine axes for both). Nearest position within `radius`; ties (same
    position) are separated by the full delta record (every key). Returns (index array, ambiguous count)."""
    from mathutils import kdtree
    kd = kdtree.KDTree(len(bl_pos))
    for i, p in enumerate(bl_pos.tolist()):
        kd.insert(p, i)
    kd.balance()
    idx = np.full(len(eng_pos), -1, np.int64)
    amb = 0
    for i, p in enumerate(eng_pos.tolist()):
        hits = kd.find_range(p, radius)
        if not hits:
            continue
        if len(hits) == 1:
            idx[i] = hits[0][1]
            continue
        cand = np.array([h[1] for h in hits], np.int64)
        if eng_rec is not None:
            err = np.abs(bl_rec[cand] - eng_rec[i][None, :]).max(axis=1) + np.array([h[2] for h in hits])
        else:
            err = np.array([h[2] for h in hits])
        best = np.sort(err)
        if len(best) > 1 and best[1] - best[0] < 1e-9:
            amb += 1
        idx[i] = cand[int(np.argmin(err))]
    return idx, amb


def _expressions(controls, key_inputs, inbetweens, morph_names, sweep=True):
    """Core expressions + sweep. Weights are morph-channel (= face control) weights."""
    out = [(n, w, "core") for n, w in CORE_EXPRESSIONS]
    for c in sorted(controls) if sweep else []:
        m = c[len("face_"):]
        if m not in morph_names:
            continue
        out.append((f"{m}=1", {m: 1.0}, "sweep"))
        if m in inbetweens:
            for w in SWEEP_INBETWEEN_WEIGHTS:
                out.append((f"{m}={w}", {m: w}, "sweep"))
    return out


def parity(bpy, np, blend, pkg, controls, key_inputs, log=print, sweep=True):
    man, meshes, by_obj = load_package(np, pkg)
    exporter = str(man.get("exporter_version", "4"))
    inbetweens = man.get("morph_inbetweens", {})
    morph_names = set(man.get("morph_names", []))
    root = _root(bpy)
    rig = next(o for o in root.all_objects if o.type == "ARMATURE")
    rig.data.pose_position = "REST"  # as the exporter
    # masks off, as the exporter (it keeps all vertices and drops masked faces)
    for o in root.all_objects:
        if o.type == "MESH":
            for m in o.modifiers:
                if m.type == "MASK" and m.mode == "VERTEX_GROUP" and m.show_viewport and m.vertex_group in o.vertex_groups:
                    m.show_viewport = False
    keyed = sorted(n for n in by_obj if bpy.data.objects[n].data.shape_keys)
    unkeyed = sorted(n for n in by_obj if n not in keyed)
    # correctives: keys whose driver reads anything but face_* controls; combinations: 2+ face controls
    correctives = sorted(f"{o}:{k}" for (o, k), ins in key_inputs.items() if None in ins)
    combos = sorted(f"{o}:{k}" for (o, k), ins in key_inputs.items() if None not in ins and len(ins) > 1)
    _set_controls(bpy, controls, {})
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    radius = 4 * (GRID_M if exporter != "4" else 1e-6)
    objs = {}
    neutral_all = {"max_mm": 0.0, "objects": 0, "vertices": 0, "fail": []}
    for name in keyed + unkeyed:
        o = bpy.data.objects[name]
        bl = _to_engine(np, _evaluated_world(bpy, np, o, deps))
        eng_pos = np.concatenate([meshes[mi]["pos"] for mi in by_obj[name]])
        ext = float(np.abs(bl).max())
        if name in keyed:
            raw = _raw_deltas(np, o)
            knames = list(raw)
            draw = {k: _to_engine(np, v) for k, v in raw.items()}
            # dense engine deltas over the concatenated parts
            dense, off = {k: np.zeros_like(eng_pos) for k in knames}, 0
            for mi in by_obj[name]:
                for k, (vi, dp) in meshes[mi]["morphs"].items():
                    if k in dense:
                        dense[k][off + vi] = dp
                off += len(meshes[mi]["pos"])
            eng_rec = np.hstack([dense[k] for k in knames]) if knames else None
            bl_rec = np.hstack([draw[k] for k in knames]) if knames else None
        else:
            eng_rec = bl_rec = None
        idx, amb = _match(bpy, np, eng_pos, bl, eng_rec, bl_rec, radius)
        unmatched = int((idx < 0).sum())
        if unmatched:
            neutral_all["fail"].append(f"{name}: {unmatched} engine vertices without a Blender vertex")
            idx = np.where(idx < 0, 0, idx)
        err0 = np.abs(eng_pos - bl[idx]).max(axis=1) if len(idx) else np.zeros(0)
        b0 = quant_bound(exporter, ext, 0.0, 0.0)
        neutral_all["max_mm"] = max(neutral_all["max_mm"], float(err0.max() * 1e3) if len(err0) else 0.0)
        neutral_all["objects"] += 1
        neutral_all["vertices"] += len(idx)
        if len(err0) and err0.max() > b0:
            neutral_all["fail"].append(f"{name}: rest error {err0.max() * 1e3:.6f} mm > bound {b0 * 1e3:.6f} mm")
        if name not in keyed:
            continue
        dext = max((float(np.abs(v).max()) for v in draw.values()), default=0.0)
        db = delta_bound(exporter, dext)
        derr = {k: float(np.abs(dense[k] - draw[k][idx]).max()) for k in knames}
        objs[name] = {"idx": idx, "eng_pos": eng_pos, "dense": dense, "ext": ext, "dext": dext, "keys": knames,
                      "ambiguous": amb, "unmatched": unmatched,
                      "delta": {"max_mm": max(derr.values(), default=0.0) * 1e3, "bound_mm": db * 1e3,
                                "worst_key": max(derr, key=derr.get) if derr else None,
                                "fail": sorted(k for k, e in derr.items() if e > db)}}
        log(f"[face_parity]   {name}: {len(idx)} vertices, {len(knames)} keys, raw-delta max "
            f"{objs[name]['delta']['max_mm']:.6f} mm (bound {db * 1e3:.6f}), ambiguous {amb}")
    # expressions
    exprs = []
    for ename, w, group in _expressions(controls, key_inputs, inbetweens, morph_names, sweep):
        missing = [m for m in w if f"face_{m}" not in controls]
        if missing:
            exprs.append({"name": ename, "group": group, "weights": w, "pass": False,
                          "problems": [f"no face_* control for {missing}"]})
            continue
        _set_controls(bpy, controls, {f"face_{m}": v for m, v in w.items()})
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        ew = expand_inbetweens(inbetweens, w)
        wsum = sum(abs(v) for v in ew.values())
        rec = {"name": ename, "group": group, "weights": w, "engine_morph_weights": ew, "objects": {}, "problems": []}
        mx, tot, cnt, moved_tot, moved_cnt = 0.0, 0.0, 0, 0.0, 0
        for name, d in objs.items():
            o = bpy.data.objects[name]
            bl = _to_engine(np, _evaluated_world(bpy, np, o, deps))[d["idx"]]
            eng = d["eng_pos"].copy()
            for m, wm in ew.items():
                if m in d["dense"]:
                    eng += wm * d["dense"][m]
            e = np.linalg.norm(eng - bl, axis=1)
            ec = np.abs(eng - bl).max(axis=1)
            b = quant_bound(exporter, d["ext"], d["dext"], wsum)
            moved = np.linalg.norm(bl - d["eng_pos"], axis=1) > 1e-6
            rec["objects"][name] = {"max_mm": float(e.max() * 1e3), "mean_mm": float(e.mean() * 1e3),
                                    "max_coord_mm": float(ec.max() * 1e3), "bound_mm": float(b * 1e3),
                                    "moved_vertices": int(moved.sum())}
            if ec.max() > b:
                rec["problems"].append(f"{name}: {int((ec > b).sum())} vertices beyond the bound, max "
                                       f"{ec.max() * 1e3:.6f} mm > {b * 1e3:.6f} mm")
            mx = max(mx, float(e.max()))
            tot += float(e.sum())
            cnt += len(e)
            moved_tot += float(e[moved].sum())
            moved_cnt += int(moved.sum())
        # correctives must stay at 0 in Blender (the engine never drives them)
        for ok in correctives:
            on, kn = ok.split(":", 1)
            v = bpy.data.objects[on].data.shape_keys.key_blocks[kn].value
            if abs(v) > 1e-6:
                rec["problems"].append(f"corrective {ok} is {v:.4f} in Blender (engine: 0)")
        rec.update({"max_mm": mx * 1e3, "mean_mm": tot / max(1, cnt) * 1e3,
                    "mean_moved_mm": moved_tot / max(1, moved_cnt) * 1e3, "moved_vertices": moved_cnt,
                    "bound_mm": max((x["bound_mm"] for x in rec["objects"].values()), default=0.0),
                    "pass": not rec["problems"]})
        exprs.append(rec)
    _set_controls(bpy, controls, {})
    delta_fail = {n: d["delta"]["fail"] for n, d in objs.items() if d["delta"]["fail"]}
    problems = list(neutral_all["fail"]) + [f"{n}: raw deltas beyond the bound: {k}" for n, k in delta_fail.items()]
    problems += [f"combination corrective {c}: the engine has no combination logic" for c in combos]
    problems += [f"{e['name']}: {p}" for e in exprs if e["group"] == "core" for p in e["problems"]]
    sweep_problems = [f"{e['name']}: {p}" for e in exprs if e["group"] == "sweep" for p in e["problems"]]
    return {"pass": not problems, "sweep_pass": not sweep_problems, "exporter_version": exporter,
            "package": os.path.basename(pkg), "chain_gaps": chain_gaps(bpy, inbetweens, keyed),
            "sweep_problems": sweep_problems,
            "rest_all_objects": neutral_all,
            "keyed_objects": {n: {k: v for k, v in d.items() if k in ("keys", "ambiguous", "unmatched", "delta", "ext")}
                              for n, d in objs.items()},
            "correctives": correctives, "combination_correctives": combos,
            "expressions": exprs, "problems": problems}


def chain_gaps(bpy, inbetweens, keyed):
    """Objects that carry the base key of an in-between chain but not its stop keys. The engine expands the chain by
    morph name for every block (expandInbetweens): such an object's base block stays at weight 0 until the last stop
    (0.75) and then ramps to 1, so it only matches Blender if the object's driver for the base key does the same."""
    out = {}
    for base, chain in sorted(inbetweens.items()):
        stops = {m for _, m in chain}
        for name in keyed:
            sk = bpy.data.objects[name].data.shape_keys
            kb = sk.key_blocks
            if base not in kb or any(m in kb for m in stops):
                continue
            d = sk.animation_data.drivers.find(f'key_blocks["{base}"].value') if sk.animation_data else None
            out.setdefault(base, []).append({"object": name, "driver": (d.driver.type + (
                f" {d.driver.expression}" if d.driver.type == "SCRIPTED" else "")) if d else None})
    return out


def expression_bones(bpy, controls, man):
    """Info (not gating): Blender's driven bone angle per expression_bones morph at weight 1 vs the exported degrees.
    The engine rotates the bone from the package; Blender drives the pose bone. Measured in POSE position."""
    import math as _m
    root = _root(bpy)
    rig = next(o for o in root.all_objects if o.type == "ARMATURE")
    out = {}
    spec = json.loads(root.get("ps_expression_bones", "{}") or "{}")
    rig.data.pose_position = "POSE"
    for morph, lst in spec.items():
        if f"face_{morph}" not in controls:
            continue
        _set_controls(bpy, controls, {f"face_{morph}": 1.0})
        bpy.context.view_layer.update()
        for e in lst:
            pb = rig.pose.bones.get(e["bone"])
            if pb is None:
                continue
            ang = _m.degrees(pb.matrix_basis.to_quaternion().angle)
            out.setdefault(morph, []).append({"bone": e["bone"], "blender_deg": round(ang, 4),
                                              "package_deg": float(e["degrees"]),
                                              "diff_deg": round(ang - float(e["degrees"]), 4)})
    _set_controls(bpy, controls, {})
    rig.data.pose_position = "REST"
    bpy.context.view_layer.update()
    return out


def run_master(blend, package=None, accept=None, log=print, sweep=True):
    """Full check of one master. Returns the report dict (never raises on a failed check; PinError propagates)."""
    import numpy as np
    bpy = _bpy()
    t0 = time.time()
    ver, h = running_build()
    pin = check_pin(ver, h, accept or os.environ.get(PIN_ENV))
    blend = os.path.abspath(blend)
    tmp = None
    if package is None:
        import importlib
        sys.path.insert(0, HERE)
        EE = importlib.import_module("export_engine")
        tmp = tempfile.TemporaryDirectory(prefix="face_parity_")
        package = os.path.join(tmp.name, "pkg")
        argv = sys.argv
        sys.argv = ["face_parity", "--", "--blend", blend, "--profile", PROFILE, "--out", package]
        try:
            EE.main()
        finally:
            sys.argv = argv
    t_export = time.time() - t0
    bpy.ops.wm.open_mainfile(filepath=blend)  # fresh state after the export (never saved)
    root = _root(bpy)
    controls, key_inputs, face_objects = face_controls(bpy, root)
    knobs = knob_check(bpy, root, face_objects)
    man = json.load(open(os.path.join(package, "character.json")))
    bones = expression_bones(bpy, controls, man)
    par = parity(bpy, np, blend, package, controls, key_inputs, log=log, sweep=sweep)
    rep = {"schema": SCHEMA, "character": root.get("ps_character_id", root.name),
           "master": os.path.relpath(blend, ROOT) if blend.startswith(ROOT) else blend,
           "blender": pin, "knob_free": knobs, "parity": par, "expression_bones_info": bones,
           "seconds": {"export": round(t_export, 1), "total": round(time.time() - t0, 1)},
           "pass": bool(knobs["pass"] and par["pass"]), "sweep_pass": par["sweep_pass"]}
    if tmp is not None:
        tmp.cleanup()
    return rep


def summary_lines(rep):
    p = rep["parity"]
    lines = [f"[face_parity] {rep['character']} ({rep['master']}): {'PASS' if rep['pass'] else 'FAIL'}  "
             f"Blender {rep['blender']['running']['version']}+{rep['blender']['running']['build_hash']}"
             + (f" (override {rep['blender']['override']})" if rep['blender']['override'] else ""),
             f"  knob-free: {'PASS' if rep['knob_free']['pass'] else 'FAIL'} "
             f"({len(rep['knob_free']['face_objects'])} face objects) {rep['knob_free']['problems'] or ''}",
             f"  rest (all {p['rest_all_objects']['objects']} exported objects, {p['rest_all_objects']['vertices']} "
             f"vertices): max {p['rest_all_objects']['max_mm']:.6f} mm"]
    for e in p["expressions"]:
        if e["group"] == "core":
            lines.append(f"  {e['name']:<14} max {e.get('max_mm', 0):.6f} mm  mean {e.get('mean_mm', 0):.6f} mm  "
                         f"mean(moved) {e.get('mean_moved_mm', 0):.6f} mm  bound {e.get('bound_mm', 0):.6f} mm  "
                         f"{'PASS' if e['pass'] else 'FAIL ' + '; '.join(e['problems'])}")
    sw = [e for e in p["expressions"] if e["group"] == "sweep"]
    if sw:
        lines.append(f"  sweep ({len(sw)} expressions): {'PASS' if p['sweep_pass'] else 'FAIL (reported; --strict gates)'}"
                     f" max {max(e.get('max_mm', 0) for e in sw):.6f} mm, {sum(not e['pass'] for e in sw)} failing")
    for base, objs in p.get("chain_gaps", {}).items():
        lines.append(f"  chain gap {base}: base key without its in-between keys on "
                     + ", ".join(f"{o['object']} ({o['driver']})" for o in objs))
    for pr in p["problems"][:10]:
        lines.append(f"  problem: {pr}")
    return lines


def main(argv=None):
    import argparse
    argv = argv if argv is not None else (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    ap = argparse.ArgumentParser(prog="face_parity")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--character")
    g.add_argument("--blend")
    g.add_argument("--all", action="store_true", help="every character's current (approved) master")
    ap.add_argument("--first", help="with --all: check this character first (the face-plan pilot)")
    ap.add_argument("--version")
    ap.add_argument("--package", help="compare this existing package instead of exporting the master")
    ap.add_argument("--out", help="JSON report (with --all: one file holding a list)")
    ap.add_argument("--accept-blender", help="<version>+<hash>: accept this non-pinned build (intentional upgrade)")
    ap.add_argument("--no-sweep", action="store_true", help="core expressions only (faster)")
    ap.add_argument("--strict", action="store_true", help="the sweep gates too (default: core expressions gate)")
    a = ap.parse_args(argv)
    try:
        ver, h = running_build()
        check_pin(ver, h, a.accept_blender or os.environ.get(PIN_ENV))
    except PinError as exc:
        print("=" * 100 + f"\n[face_parity] FAIL (Blender build pin): {exc}\n" + "=" * 100, file=sys.stderr)
        return 3
    if a.all:
        targets = [master_path(c) for c in current_characters(a.first)]
    elif a.character:
        targets = [master_path(a.character, a.version)]
    else:
        targets = [(a.blend, None)]
    reps = []
    for blend, _ in targets:
        try:
            rep = run_master(blend, a.package if not a.all else None, a.accept_blender, sweep=not a.no_sweep)
        except SystemExit as exc:  # export_engine refuses the master
            print(f"[face_parity] export failed for {blend}: {exc}", file=sys.stderr)
            return 2
        reps.append(rep)
        print("\n".join(summary_lines(rep)))
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump(reps if a.all else reps[0], open(a.out, "w"), indent=1, sort_keys=True)
    return 0 if all(r["pass"] and (r["sweep_pass"] or not a.strict) for r in reps) else 1


if __name__ == "__main__":
    code = main()
    if code:
        sys.exit(code)
