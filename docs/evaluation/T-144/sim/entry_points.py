import json, os, sys
tree = sys.argv[1]
sys.path.insert(0, os.path.join(tree, "pipeline/charsys"))
import spec as S, versions as V
A = os.path.join(tree, "assets/characters")
entries = {
 "charsys (verify_charsys build) + face tests": ["boy_yellow_hoodie/spec/boy_yellow_hoodie.spec.json"],
 "determinism (test_determinism default --character boy)": ["boy_yellow_hoodie/spec/boy_yellow_hoodie.spec.json"],
 "build-determinism-girl (0.13.0)": ["girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.13.0.spec.json"],
 "boy2 (2.0.0-dev build -> test_boy2_face, test_hoodie)": ["boy_yellow_hoodie/spec/boy_yellow_hoodie.2.0.0-dev.spec.json"],
 "garments-v2-quick (pin+validate boy 2.0.0, girl 0.11.0)": ["boy_yellow_hoodie/spec/boy_yellow_hoodie.2.0.0.spec.json",
                                                            "girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.11.0.spec.json"],
 "material-presets (SPEC.load girl unversioned)": ["girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json"],
 "test_determinism --character current: third T-126a": ["girl_white_hair_blue_dress/spec/candidates/T-126a/girl_white_hair_blue_dress.0.1.0.spec.json"],
}
out = {"spec_entry_points": {}, "published_embedded_specs": {}}
for k, specs in entries.items():
    r = []
    for p in specs:
        try:
            S.load(os.path.join(A, p)); r.append({"spec": p, "loads": True})
        except Exception as e:
            r.append({"spec": p, "loads": False, "error": str(e)[:200]})
    out["spec_entry_points"][k] = r
for c in sorted(os.listdir(A)):
    vd = os.path.join(A, c, "versions")
    if not os.path.isdir(vd): continue
    for v in sorted(os.listdir(vd)):
        sp = os.path.join(vd, v, "spec.json")
        if not os.path.exists(sp): continue
        try:
            V.record(json.load(open(sp))); ok, err = True, ""
        except Exception as e:
            ok, err = False, str(e)[:200]
        out["published_embedded_specs"][f"{c} {v}"] = {"versions.record (export_engine / regenerate)": ok, "error": err}
print(json.dumps(out, indent=1))
