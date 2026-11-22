"""T-183 round 3: try keys of a character's dynamics chains on a built shot without a rebuild (any shot, any character;
tweak_chains.py is the e909-only, numbers-only predecessor). Copies the character's package, edits the chains whose
name matches, bakes into <shot dir>/build/exp/<name>/bake.json.

    python3 tweak_package.py <shot dir> <name> <character> '<chain pattern>:<path>=<json>' [...] [--scene='<path>=<json>']

<path> is a dotted path inside the chain, with [i] for a list index: 'ringlets_back*:contact.radii[1]=0.012',
'ringlets_*:contact.locks=true', '*:damping=14'. A value 'x<number>' multiplies the present number.
--scene sets a key of the character's scene "dynamics" override the same way (e.g. --scene='substep_hz=480').
"""
import fnmatch
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))


def put(obj, path, value):
    keys = [int(k) if k.isdigit() else k for k in re.findall(r"[^.\[\]]+", path)]
    for k in keys[:-1]:
        if isinstance(obj, dict) and k not in obj:
            obj[k] = {}
        obj = obj[k]
    if isinstance(value, str) and value.startswith("x"):
        value = obj[keys[-1]] * float(value[1:])
    obj[keys[-1]] = value


def parse(v):
    try:
        return json.loads(v)
    except ValueError:
        return v


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    shot, name, who = os.path.abspath(args[0]), args[1], args[2]
    B = shot + "/build"
    cast = json.load(open(B + "/cast.json"))
    src = os.path.dirname(cast[who]["package"] + "/")
    src = src if os.path.isabs(src) else os.path.join(ROOT, src)
    out = f"{B}/exp/{name}"
    os.makedirs(f"{out}/packages/{who}", exist_ok=True)
    doc = json.load(open(src + "/character.json"))
    for a in args[3:]:
        pat, kv = a.split(":", 1)
        k, v = kv.split("=", 1)
        n = 0
        for ch in doc["dynamics"]["chains"]:
            if fnmatch.fnmatchcase(ch["name"], pat):
                put(ch, k, parse(v))
                n += 1
        print(f"{pat}: {k} = {v} on {n} chains")
    json.dump(doc, open(f"{out}/packages/{who}/character.json", "w"))
    for f in os.listdir(src):
        if f != "character.json" and not os.path.exists(f"{out}/packages/{who}/{f}"):
            os.symlink(f"{src}/{f}", f"{out}/packages/{who}/{f}")
    scene = json.load(open(B + "/shot.resolved.scene.json"))
    for c in scene["characters"]:
        c["asset"] = f"{out}/packages/{who}/character.json" if c["name"] == who else os.path.join(B, c["asset"])
        if c["name"] == who:
            for a in sys.argv[1:]:
                if a.startswith("--scene="):
                    k, v = a[8:].split("=", 1)
                    c["dynamics"] = c.get("dynamics") if isinstance(c.get("dynamics"), dict) else {}
                    put(c["dynamics"], k, parse(v))
    # the scene stays beside the resolved one so that relative asset paths (props) resolve as in the shot's bake
    spath = f"{B}/exp_{name}.scene.json"
    json.dump(scene, open(spath, "w"))
    r = subprocess.run([ROOT + "/build/apps/render-cli/plush-render", spath, "--bake", out + "/bake.json"], capture_output=True, text=True)
    print(out + "/bake.json" if r.returncode == 0 else (r.stdout[-1500:] + r.stderr[-1500:]))
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
