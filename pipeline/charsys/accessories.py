"""Reusable accessories (spec.accessories.items[*].type). Accessories are separate rigid parts bound to a bone and
placed only from landmarks and the head surface, never inside a face or body generator.

glasses/1:
  rim:     radius_m or radius_eye_spacing (fraction of the distance between the eye centres), aspect (height/width),
           shape_n (superellipse exponent: 2 round, 3-5 rounded rectangle), offset_up_m (rim centre above the eye
           centre), eye_clearance_m (gap in front of the eye, lids and lashes), skin_clearance_m, wrap_deg
           (each rim turned outwards to follow the face), segments
  wire_radius_m: frame wire thickness
  bridge:  lift_m (bridge above the rim centres), forward_m
  temples: skin_offset_m (gap to the head side), drop_m (hook behind the ear), enabled
  lens:    enabled (thin clear discs; parented to the head bone, not exported to the engine, which has no
           transparent materials)
  material: srgb, roughness, metallic
The frame (rims, bridge, temples) is one object "<name>"; lenses "<name>_lens"."""
import math

import bpy
from mathutils import Matrix, Vector

import geom as G


def _f(d, k, default):
    return float(d.get(k, default)) if d is not None else float(default)


def _superellipse(cx, cz, rx, rz, n, seg):
    pts = []
    for i in range(seg):
        t = 2 * math.pi * i / seg
        c, s = math.cos(t), math.sin(t)
        pts.append((cx + math.copysign(abs(c) ** (2 / n), c) * rx, cz + math.copysign(abs(s) ** (2 / n), s) * rz))
    return pts


def build_glasses(C, cfg, lm, ctx, face_parts, head_bone, obstacles=()):
    """lm: landmarks (eye_L/R centres of the eye fronts, ear_L/R); face_parts: objects that must stay behind the
    lenses (eyes, lids, lashes). Returns (frame, lens or None, report)."""
    name = cfg.get("name", "glasses")
    rc = cfg.get("rim", {})
    wire = _f(cfg, "wire_radius_m", 0.0016)
    eyes = {s: lm[f"eye_{s}"] for s in ("L", "R")}
    spacing = (eyes["L"] - eyes["R"]).length
    rx = _f(rc, "radius_m", 0) or _f(rc, "radius_eye_spacing", 0.43) * spacing
    rz = rx * _f(rc, "aspect", 1.0)
    n = _f(rc, "shape_n", 2.0)
    seg = int(rc.get("segments", 64))
    up = _f(rc, "offset_up_m", 0.0)
    wrap = math.radians(_f(rc, "wrap_deg", 0.0))
    rims, report = {}, {"rim_radius_m": [round(rx, 4), round(rz, 4)], "eye_spacing_m": round(spacing, 4)}
    for sx, side in ((1, "L"), (-1, "R")):
        e = eyes[side]
        cx, cz = e.x, e.z + up
        # rim plane depth: in front of everything of the eye (all shape keys) inside the rim, and of the skin
        front = []
        for ob in face_parts:
            if ob.name.endswith(f".{side}"):
                sets = [kb.data for kb in ob.data.shape_keys.key_blocks] if ob.data.shape_keys else [ob.data.vertices]
                mw = ob.matrix_world
                for data in sets:
                    for v in data:
                        p = mw @ v.co
                        if abs(p.x - cx) < rx * 1.05 and abs(p.z - cz) < rz * 1.05:
                            front.append(p.y)
        y0 = min(front) - _f(rc, "eye_clearance_m", 0.004) - wire
        ring2 = _superellipse(cx, cz, rx, rz, n, seg)
        R = Matrix.Rotation(sx * wrap, 3, "Z")  # wrap: the outer side goes back

        def place(y):
            return [Vector((cx, y, cz)) + R @ Vector((x - cx, 0, z - cz)) for x, z in ring2]
        y = y0
        for _ in range(6):  # push forward until every rim point clears the skin
            pts = place(y)
            worst = max((p.y + _f(rc, "skin_clearance_m", 0.003) + wire) - ctx.face_y(None, p.x, p.z) for p in pts)
            if worst <= 0:
                break
            y -= worst
        rims[side] = place(y)
        report[f"rim_{side}"] = {"centre_m": [round(cx, 4), round(y, 4), round(cz, 4)], "eye_gap_m": round(min(front) - y, 4)}
    mat = G.material(f"M_{name}", tuple(cfg.get("material", {}).get("srgb", (137, 85, 69))),
                     roughness=_f(cfg.get("material", {}), "roughness", 0.3))
    try:
        mat.node_tree.nodes.get("Principled BSDF").inputs["Metallic"].default_value = _f(cfg.get("material", {}), "metallic", 0.5)
    except Exception:  # pragma: no cover
        pass
    parts = []
    for side, pts in rims.items():
        loop = pts + [pts[0]]
        parts.append(G.tube(f"_{name}_rim.{side}", loop, [wire] * len(loop), [wire] * len(loop), C, up_hint=(0, -1, 0),
                            seg=10, cap_start=None, cap_end=None))
    # bridge: from the inner rim points, arching up over the nose
    inner = {s: max(rims[s], key=lambda p: -p.x if s == "L" else p.x) for s in rims}  # the point nearest the centre
    inner = {s: min(rims[s], key=lambda p, s=s: abs(p.x)) for s in rims}
    bc = cfg.get("bridge", {})
    a, b = inner["R"], inner["L"]
    zb = max(a.z, b.z) + _f(bc, "lift_m", 0.004)
    ymid = min(a.y, b.y, ctx.face_y(None, 0.0, zb) - _f(rc, "skin_clearance_m", 0.003) - wire) - _f(bc, "forward_m", 0.0)
    br = G.bezier(a, Vector((0.0, ymid, zb + (zb - a.z))), b, 11)
    parts.append(G.tube(f"_{name}_bridge", br, [wire] * len(br), [wire] * len(br), C, up_hint=(0, -1, 0), seg=10))
    tc = cfg.get("temples", {"enabled": True})
    if tc.get("enabled", True):
        for sx, side in ((1, "L"), (-1, "R")):
            hinge = max(rims[side], key=lambda p: sx * p.x)
            ear = lm.get(f"ear_{side}")
            end_y = (ear.y if ear is not None else 0.0) + _f(tc, "past_ear_m", 0.012)
            end_z = (ear.z if ear is not None else hinge.z) + _f(tc, "above_ear_m", 0.02)
            path = [hinge]
            for i in range(1, 13):
                t = i / 12
                yy = hinge.y + (end_y - hinge.y) * t
                zz = hinge.z + (end_z - hinge.z) * min(1.0, t * 1.4)
                xs = ctx.side_x(sx, yy, zz)
                xx = (xs + sx * _f(tc, "skin_offset_m", 0.004)) if xs is not None else hinge.x
                xx = sx * max(sx * xx, sx * hinge.x * (1 - t) + sx * xx * t)
                path.append(Vector((xx, yy, zz)))
            # route over obstacles (e.g. ears): lift each point above any obstacle vertex in its corridor, then smooth
            obs = [o.matrix_world @ v.co for o in obstacles for v in o.data.vertices]
            obs = [q for q in obs if sx * q.x > 0]
            clear = wire + _f(tc, "obstacle_clearance_m", 0.002)
            total = [0.0] * len(path)
            for _ in range(3):  # lift over obstacles, then put each lifted point back outside the head side
                lift = [0.0] * len(path)
                for i, p in enumerate(path):
                    near = [q.z for q in obs if abs(q.y - p.y) < 0.006 and abs(q.x - p.x) < 0.015]
                    if near and max(near) + clear > p.z:
                        lift[i] = max(near) + clear - p.z
                for _ in range(2):  # spread the lift to neighbours so the temple bends smoothly
                    lift = [max(lift[i], 0.6 * max(lift[max(i - 1, 0)], lift[min(i + 1, len(lift) - 1)])) for i in range(len(lift))]
                if max(lift) < 1e-5:
                    break
                path = [p + Vector((0, 0, h)) for p, h in zip(path, lift)]
                total = [t + h for t, h in zip(total, lift)]
                for i, p in enumerate(path[1:], 1):
                    xs = ctx.side_x(sx, p.y, p.z)
                    if xs is not None and sx * p.x < sx * xs + _f(tc, "skin_offset_m", 0.004):
                        path[i] = Vector((xs + sx * _f(tc, "skin_offset_m", 0.004), p.y, p.z))
            report.setdefault("temple_lift_m", {})[side] = round(max(total), 4)
            last = path[-1]
            path.append(last + Vector((0, 0.008, -_f(tc, "drop_m", 0.008))))
            parts.append(G.tube(f"_{name}_temple.{side}", path, [wire] * len(path), [wire * 0.8] * len(path), C,
                                up_hint=(0, 0, 1), seg=8, cap_start="round", cap_end="round"))
    frame = G.join(parts, name)
    G.assign(frame, mat)
    lens = None
    lc = cfg.get("lens", {"enabled": True})
    if lc.get("enabled", True):
        verts, faces = [], []
        for side, pts in rims.items():
            c = sum(pts, Vector()) / len(pts)
            base = len(verts)
            verts.append(tuple(c + Vector((0, 0.0004, 0))))
            verts += [tuple(c + (p - c) * 0.985 + Vector((0, 0.0004, 0))) for p in pts]
            k = len(pts)
            faces += [(base, base + 1 + i, base + 1 + (i + 1) % k) for i in range(k)]
        lens = G.new_object(f"{name}_lens", verts, faces, C)
        lm_ = bpy.data.materials.new(f"M_{name}_lens")
        lm_.use_nodes = True
        p = lm_.node_tree.nodes.get("Principled BSDF")
        p.inputs["Base Color"].default_value = (1, 1, 1, 1)
        p.inputs["Roughness"].default_value = 0.0
        p.inputs["Alpha"].default_value = _f(lc, "alpha", 0.05)
        try:
            lm_.surface_render_method = "BLENDED"
        except Exception:  # pragma: no cover
            pass
        G.assign(lens, lm_)
    report["objects"] = [frame.name] + ([lens.name] if lens else [])
    return frame, lens, report


def attach(rig, frame, lens, head_bone):
    """Frame: rigid skinning to the head bone (exported); lens: bone-parented (Blender only)."""
    frame.parent = rig
    frame.matrix_parent_inverse = rig.matrix_world.inverted()
    vg = frame.vertex_groups.new(name=head_bone)
    vg.add(list(range(len(frame.data.vertices))), 1.0, "REPLACE")
    m = frame.modifiers.new("Armature", "ARMATURE")
    m.object = rig
    if lens is not None:
        mw = lens.matrix_world.copy()
        lens.parent = rig
        lens.parent_type = "BONE"
        lens.parent_bone = head_bone
        lens.matrix_world = mw


def build(C, items, lm, ctx, face_parts, head_bone, obstacles=()):
    out, rep = [], {}
    for it in items or []:
        if not isinstance(it, dict):
            continue  # planned items (strings) are documentation only
        if it.get("type") == "glasses/1":
            frame, lens, r = build_glasses(C, it, lm, ctx, face_parts, head_bone, obstacles)
            out.append((frame, lens))
            rep[it.get("name", "glasses")] = r
        else:
            raise SystemExit(f"unsupported accessory type: {it.get('type')}")
    return out, rep
