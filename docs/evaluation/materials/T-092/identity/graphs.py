import bpy, sys, json, hashlib
sys.path.insert(0, "/home/user/Animation/pipeline/charsys/tests")
argv = sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.open_mainfile(filepath=argv[0])
import importlib.util
spec = importlib.util.spec_from_file_location("g", "/home/user/Animation/pipeline/charsys/tests/test_materials_r2_graphs.py")
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
out = {"materials": {m.name: hashlib.sha256(json.dumps(g.material_digest(m), sort_keys=True).encode()).hexdigest()
                     for m in bpy.data.materials if m.node_tree},
       "node_groups": {n.name: hashlib.sha256(json.dumps(g.tree_digest(n), sort_keys=True).encode()).hexdigest()
                       for n in bpy.data.node_groups},
       "fibre_mods": {o.name: g.fibre_digest(o)["inputs"] for o in bpy.data.objects if "PS Surface Fibres" in o.modifiers}}
json.dump(out, open(argv[1], "w"), indent=1, sort_keys=True, default=str)
