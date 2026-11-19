import sys, json, bpy
sys.path.insert(0, "/home/user/Animation/pipeline/charsys")
import body_generic as BG, spec as S
R = "/home/user/Animation/"
specs = {"boy": "assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.2.1.0.spec.json",
         "girl": "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.12.0.spec.json"}
out = {"note": "body_generic.hand_frames of the current approved specs (recorded with Blender 5.3.0 for the plain T-121 tests)", "characters": {}}
for k, p in specs.items():
    spec, _ = S.load(R + p); P, H = spec["body"]["params"], float(spec["body"]["height_m"])
    J = BG.joints(P, H, spec["rig"].get("joints")); fr = BG.hand_frames(P, H, J)
    out["characters"][k] = {"spec": p, "height_m": H, "hand": P["hand"], "frames": {s: {"wrist": [round(c, 7) for c in J[f"wrist.{s}"]], "sx": sx,
        "d": [round(c, 7) for c in fr[s]["d"]], "palm_n": [round(c, 7) for c in fr[s]["palm_n"]], "side_v": [round(c, 7) for c in fr[s]["side_v"]],
        "thumb": [[round(c, 7) for c in v] for v in fr[s]["thumb"]]} for s, sx in (("L", 1), ("R", -1))}}
json.dump(out, open(R + "docs/evaluation/characters/T-121/hand_frames.json", "w"), indent=1)
vg = {"note": "vertex groups and finger deform bones of the built boy 2.1.0 hands (default build vs the hands_r2/1 override)"}
for label, m in (("current", "<build-dir>/boy_def_branch"), ("hands_r2", "<build-dir>/boy_r2")):
    bpy.ops.wm.open_mainfile(filepath=m + "/boy_yellow_hoodie_master.blend")
    rig = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
    e = {}
    for s in ("L", "R"):
        h = bpy.data.objects[f"hand.{s}"]
        used = set()
        for v in h.data.vertices:
            for g in v.groups:
                if g.weight > 0.05: used.add(h.vertex_groups[g.group].name)
        e[s] = {"vertices": len(h.data.vertices), "vertex_groups": sorted(g.name for g in h.vertex_groups), "groups_with_weight": sorted(used)}
    e["finger_deform_bones"] = sorted(b.name for b in rig.data.bones if b.use_deform and b.name.startswith(("DEF-f_", "DEF-thumb", "DEF-palm")))
    vg[label] = e
json.dump(vg, open(R + "docs/evaluation/characters/T-121/hand_vertex_groups.json", "w"), indent=1)
