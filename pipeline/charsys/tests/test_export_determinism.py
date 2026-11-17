"""Engine export determinism (T-056): export/5 packages are byte-reproducible and order-stable.

    python3 pipeline/charsys/tests/test_export_determinism.py --blender <blender> [--out <new dir>]
    python3 pipeline/charsys/tests/test_export_determinism.py --blender <blender> --out <new dir> \
        --characters boy,girl --runs 3          # full proof: clean builds + exports per character

Quick mode (default, a few seconds; plain Python driver, Blender as a subprocess, writes only into --out or a
temporary folder):
  1. the toy fixture (no embedded spec -> export/5, the default for new exports) exports twice to identical bytes;
  2. a scrambled copy of the fixture master (every mesh: vertices and polygons in another order, every triangle
     starting at another corner, 1 float32 ulp of noise on positions, shape keys and skin weights) exports to the
     same geometry.bin and character.json bytes as the original: the export does not depend on the order or the noise
     a build leaves in the master. Quads and n-gons keep their start corner: it decides Blender's split of the polygon
     into triangles, export/5 keeps that split (as export/4), and builds do not change it;
  3. export/5 content rules: no .blend byte hash in the manifest, exporter_version "5", positions on the 2^-15 m grid
     and morph deltas on the 2^-14 m grid, skin weights multiples of 1/1024 summing to exactly 1 with sorted
     influences, triangles rotated to their lowest index and sorted.
Full mode (--characters): for each character, --runs clean builds of its spec with the exporter pinned to export/5
(an override; the characters' own specs stay on export/4, docs/CHARACTER_SYSTEM_VERSIONS.md), each fingerprinted
(fingerprint_v2, 0.01 mm) and exported; all packages must be byte-identical and all fingerprints equal.
Writes export_determinism.json into --out."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CHARSYS = os.path.join(ROOT, "pipeline", "charsys")
EXPORTER = os.path.join(CHARSYS, "export_engine.py")
PROF = os.path.join(CHARSYS, "rig_profiles")
CHARS = {
    "boy": ("boy_yellow_hoodie", "assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.spec.json"),
    "girl": ("girl_auburn_bun_glasses", "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json"),
}
GRID = 2.0 ** -15        # export/5 position grid (export_engine.GRID_M)
DELTA_GRID = 2.0 ** -14  # export/5 morph delta grid (export_engine.DELTA_GRID_M)
STEPS = 1024             # export/5 weight steps (export_engine.WEIGHT_STEPS)
R = []

SCRAMBLE = r'''
import sys, random, bpy, bmesh, numpy as np
src, dst = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=src)
rnd = random.Random(56)
up = lambda x: float(np.nextafter(np.float32(x), np.float32(np.inf)))
for o in [o for o in bpy.data.objects if o.type == "MESH"]:
    bm = bmesh.new()
    bm.from_mesh(o.data)
    shapes = list(bm.verts.layers.shape.values())
    deform = bm.verts.layers.deform.active
    for f in list(bm.faces):  # every triangle starts at another corner (winding kept); see the module docstring
        if len(f.verts) != 3:
            continue
        vs, mi, sm = f.verts[:], f.material_index, f.smooth
        r = rnd.randrange(len(vs))
        bm.faces.remove(f)
        nf = bm.faces.new(vs[r:] + vs[:r])
        nf.material_index, nf.smooth = mi, sm
    for v in bm.verts:
        if rnd.random() < 0.3:  # one ulp of noise, the same on the mesh and on every shape key (deltas kept)
            ax = rnd.randrange(3)
            v.co[ax] = up(v.co[ax])
            for s in shapes:
                v[s][ax] = up(v[s][ax])
        if deform is not None and rnd.random() < 0.3:
            for g in list(v[deform].keys()):
                v[deform][g] = up(v[deform][g])
    keys = {e: rnd.random() for e in bm.verts}
    bm.verts.sort(key=lambda e: keys[e])
    keys = {e: rnd.random() for e in bm.faces}
    bm.faces.sort(key=lambda e: keys[e])
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
bpy.ops.wm.save_as_mainfile(filepath=dst)
'''


def check(name, ok, detail=None):
    R.append((name, bool(ok)))
    print(f"[test_export_determinism] {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}",
          flush=True)
    return ok


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def package_bytes(pkg):
    return {f: sha(os.path.join(pkg, f)) for f in ("geometry.bin", "character.json")}


def arr(buf, v):
    return np.frombuffer(buf, np.dtype(v["dtype"]).newbyteorder("<"), v["count"], v["offset"])


def content_rules(pkg):
    man = json.load(open(os.path.join(pkg, "character.json")))
    buf = open(os.path.join(pkg, "geometry.bin"), "rb").read()
    check("manifest has no .blend byte hash", "blend_sha256" not in man["source"], man["source"])
    check("exporter_version 5, recorded as export/5", man["exporter_version"] == "5"
          and man["versions"]["generators"]["exporter"] == "export/5", (man["exporter_version"], man["versions"]))
    on_grid = weights_ok = order_ok = tri_ok = True
    for m in man["meshes"]:
        n = m["vertices"]
        p = arr(buf, m["positions"]).astype(np.float64)
        on_grid &= bool(np.all(p / GRID == np.round(p / GRID)))
        w = arr(buf, m["weights"]).astype(np.float64).reshape(n, 4)
        j = arr(buf, m["joints"]).astype(np.int64).reshape(n, 4)
        q = w * STEPS
        weights_ok &= bool(np.all(q == np.round(q)) and np.all(q.sum(axis=1) == STEPS))
        key = -q * 65536 + j  # influences ordered by weight descending, then joint index; empty slots at the end
        order_ok &= bool(np.all(np.diff(key, axis=1) >= 0) and np.all(j[q == 0] == 0))
        t = arr(buf, m["indices"]).astype(np.int64).reshape(-1, 3)
        tri_ok &= bool(np.all(t[:, 0] == t.min(axis=1)) and np.array_equal(t, t[np.lexsort(t.T[::-1])]))
    for mo in man["morphs"]:
        d = arr(buf, mo["dpos"]).astype(np.float64)
        on_grid &= bool(np.all(d / DELTA_GRID == np.round(d / DELTA_GRID)) and np.all(np.abs(d).reshape(-1, 3).max(axis=1) > 0))
    check("positions on the 2^-15 m grid, morph deltas on the 2^-14 m grid (no zero morph entries)", on_grid)
    check("skin weights: multiples of 1/1024 summing to exactly 1", weights_ok)
    check("influences sorted by (weight desc, joint); empty slots use joint 0", order_ok)
    check("triangles start at their lowest index and are sorted", tri_ok)


def quick(blender, out):
    bl = lambda script, *args: subprocess.run([blender, "-b", "--factory-startup", "-P", script, "--", *args],  # noqa: E731
                                              cwd=ROOT, capture_output=True, text=True)
    prof = os.path.join(PROF, "humanoid_toy_fixture.json")
    blend = os.path.join(out, "fixture", "toy.blend")
    os.makedirs(os.path.dirname(blend))
    r = bl(os.path.join(CHARSYS, "tests", "fixtures", "make_toy_fixture.py"), blend)
    if not check("fixture builds", r.returncode == 0 and os.path.exists(blend), r.stderr[-400:] if r.returncode else None):
        return {}
    pk = {}
    for name, src in (("a", blend), ("a2", blend)):
        r = bl(EXPORTER, "--blend", src, "--profile", prof, "--out", os.path.join(out, name))
        check(f"fixture exports ({name})", r.returncode == 0, (r.stdout + r.stderr)[-400:] if r.returncode else None)
        pk[name] = package_bytes(os.path.join(out, name))
    check("same master, two exports: identical bytes", pk["a"] == pk["a2"], pk)
    scr = os.path.join(out, "scrambled", "toy.blend")  # same file name: the manifest records the basename
    os.makedirs(os.path.dirname(scr))
    script = os.path.join(out, "scramble.py")
    open(script, "w").write(SCRAMBLE)
    r = bl(script, blend, scr)
    check("scrambled master written", r.returncode == 0 and os.path.exists(scr), r.stderr[-600:] if r.returncode else None)
    probe = os.path.join(out, "probe.py")
    open(probe, "w").write("import sys, bpy, hashlib\nbpy.ops.wm.open_mainfile(filepath=sys.argv[-2])\n"
                           "m = bpy.data.objects['toy_body'].data\nh = hashlib.sha256()\n"
                           "for v in m.vertices: h.update(repr(v.co[:]).encode())\n"
                           "for p in m.polygons: h.update(repr(p.vertices[:]).encode())\n"
                           "for v in m.vertices: h.update(repr([(g.group, g.weight) for g in v.groups]).encode())\n"
                           "open(sys.argv[-1], 'w').write(h.hexdigest())\n")
    hashes = []
    for i, b in enumerate((blend, scr)):
        bl(probe, b, os.path.join(out, f"probe_{i}.txt"))
        hashes.append(open(os.path.join(out, f"probe_{i}.txt")).read())
    check("the scramble changed the master's mesh data (order, triangle start corners, noise)", hashes[0] != hashes[1])
    r = bl(EXPORTER, "--blend", scr, "--profile", prof, "--out", os.path.join(out, "b"))
    check("scrambled master exports", r.returncode == 0, (r.stdout + r.stderr)[-400:] if r.returncode else None)
    pk["b"] = package_bytes(os.path.join(out, "b"))
    check("scrambled master: geometry.bin byte-identical", pk["a"]["geometry.bin"] == pk["b"]["geometry.bin"])
    check("scrambled master: character.json byte-identical", pk["a"]["character.json"] == pk["b"]["character.json"])
    content_rules(os.path.join(out, "a"))
    return pk


def full(blender, out, characters, runs):
    sys.path.insert(0, CHARSYS)
    import determinism
    env = determinism.subprocess_env()
    os.makedirs(out, exist_ok=True)
    override = os.path.join(out, "exporter5.override.json")
    json.dump({"override": {"generators": {"exporter": "export/5"}}}, open(override, "w"), indent=1)
    res = {}
    for label in characters:
        cid, spec = CHARS[label]
        pkgs, fps = [], []
        for run in range(1, runs + 1):
            d = os.path.join(out, f"{label}_{run}")
            os.makedirs(d)
            with open(os.path.join(d, "build.log"), "w") as log:
                subprocess.run([blender, "-b", "--factory-startup", "-t", "1", "-P",
                                os.path.join(CHARSYS, "build_character.py"), "--", "--spec", os.path.join(ROOT, spec),
                                "--override", override, "--out", d, "--no-glb", "--no-compare"],
                               cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
            master = os.path.join(d, f"{cid}_master.blend")
            fp = os.path.join(d, "fingerprint_0.01mm.json")
            subprocess.run([blender, "-b", "--factory-startup", "-t", "1", "-P", os.path.join(CHARSYS, "fingerprint_v2.py"),
                            "--", master, fp, "--grid-m", "0.00001"], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, check=True)
            fpd = json.load(open(fp))
            fpd.pop("file", None)
            fps.append(hashlib.sha256(json.dumps(fpd, sort_keys=True).encode()).hexdigest())
            pkg = os.path.join(d, "package")
            with open(os.path.join(d, "export.log"), "w") as log:
                subprocess.run([blender, "-b", "--factory-startup", "-P", EXPORTER, "--", "--blend", master, "--profile",
                                os.path.join(PROF, "humanoid_rigify.json"), "--out", pkg],
                               cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
            pkgs.append(package_bytes(pkg))
            print(f"[test_export_determinism] {label} run {run}: {pkgs[-1]} fingerprint {fps[-1][:16]}", flush=True)
        check(f"{label}: {runs} clean builds + exports byte-identical", all(p == pkgs[0] for p in pkgs), pkgs)
        check(f"{label}: {runs} fingerprints identical", len(set(fps)) == 1, fps)
        content_rules(os.path.join(out, f"{label}_1", "package"))
        res[label] = {"packages": pkgs, "fingerprints_sha256": fps}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--characters", default="", help="comma list of " + ", ".join(CHARS) + " (full proof)")
    ap.add_argument("--runs", type=int, default=3)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.abspath(a.out) if a.out else tmp
        if os.path.exists(out) and os.listdir(out):
            raise SystemExit("--out must be new or empty")
        os.makedirs(out, exist_ok=True)
        report = {"quick": quick(a.blender, os.path.join(out, "quick"))}
        if a.characters:
            report["full"] = full(a.blender, os.path.join(out, "full"), [c for c in a.characters.split(",") if c], a.runs)
        ok = all(x for _, x in R)
        report["checks"] = [{"name": n, "pass": x} for n, x in R]
        report["pass"] = ok
        json.dump(report, open(os.path.join(out, "export_determinism.json"), "w"), indent=1)
        print(f"[test_export_determinism] {'ALL PASS' if ok else 'FAILURES'} ({sum(x for _, x in R)}/{len(R)})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
