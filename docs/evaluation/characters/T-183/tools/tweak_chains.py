"""T-183: try chain parameters on a built candidate without a rebuild: copies the girl's package, sets keys on the
chains whose name matches, bakes into <shot build>/exp/<name>/bake.json.

    python3 tweak_chains.py <name> <chain pattern>:<key>=<number> [...]      (e.g. 'ringlets_side_b.*:limit_deg=12')"""
import fnmatch
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
B = ROOT + "/episodes/e909_two_char_acting/shots/s010_t183/build"
name = sys.argv[1]
src = os.path.dirname(json.load(open(B + "/cast.json"))["girl"]["package"] + "/")
out = f"{B}/exp/{name}"
os.makedirs(out + "/packages/girl", exist_ok=True)
doc = json.load(open(src + "/character.json"))
for a in sys.argv[2:]:
    pat, kv = a.split(":", 1)
    k, v = kv.split("=", 1)
    n = 0
    for ch in doc["dynamics"]["chains"]:
        if fnmatch.fnmatchcase(ch["name"], pat):
            ch[k] = float(v)
            n += 1
    print(f"{pat}: {k} = {v} on {n} chains")
json.dump(doc, open(out + "/packages/girl/character.json", "w"))
if not os.path.exists(out + "/packages/girl/geometry.bin"):
    os.symlink(src + "/geometry.bin", out + "/packages/girl/geometry.bin")
scene = json.load(open(B + "/shot.resolved.scene.json"))
for c in scene["characters"]:
    c["asset"] = out + "/packages/girl/character.json" if c["name"] == "girl" else B + "/" + c["asset"]
json.dump(scene, open(out + "/scene.json", "w"))
r = subprocess.run([ROOT + "/build/apps/render-cli/plush-render", out + "/scene.json", "--bake", out + "/bake.json"], capture_output=True, text=True)
print(out + "/bake.json" if r.returncode == 0 else (r.stdout[-1500:] + r.stderr[-1500:]))
sys.exit(r.returncode)
