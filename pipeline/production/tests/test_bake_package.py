"""T-205 tests: bake packages (pipeline/production/bake_package.py) and the PC renderer (tools/pc/render_package.py).
Fast: no Blender, no engine (a fake Blender checks what the real one would read).

    python3 pipeline/production/tests/test_bake_package.py

1. Determinism: the same bake, cast and source tree packed twice -> byte-identical MANIFEST.json and zip; a changed
   input file changes exactly that file's hash.
2. Completeness: the zip, copied alone into a clean temporary folder (the fixture's source tree deleted, no engine on
   PATH), verifies and "renders": the fake Blender runs the package's shot_render.py in the package folder and finds
   the bake, the resolved scene, every cast master and package file and every prop asset through package-relative
   paths, plus every local module shot_render.py imports. No packaged file is an executable; the render command never
   names plush-render.
3. Verification failures: a changed, a missing and an unlisted file, and a zip entry outside the package folder, each
   stop the PC run (exit 3) before Blender starts.
4. A render profile the package does not have (e.g. preview_eevee before T-201) fails with a clear message (exit 2).
5. The packaged render code list covers every pipeline/charsys module the render code imports (real repository)."""
import ast
import contextlib
import importlib.util
import io
import json
import os
import shutil
import stat
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FAILS = []


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bp = load("bake_package", "pipeline/production/bake_package.py")
pc = bp.load_pc_tool()


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f": {detail}" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data if isinstance(data, str) else json.dumps(data, indent=1), encoding="utf-8")
    return str(path)


def fixture(base):
    """A prepared and baked shot outside the repository: ep/shots/s1/{shot.scene.json, build/...}, a published master
    with its manifest, an engine package (character.json + geometry.bin), a prop asset in ep/content/assets."""
    base = Path(base)
    master = write(base / "store/kid/versions/1.0.0/kid_master.blend", b"BLENDER-fake-master\x00\x01")
    write(base / "store/kid/versions/1.0.0/manifest.json",
          {"character_id": "kid", "version": "1.0.0", "files": {"kid_master.blend": {"sha256": pc.sha256(master)}}})
    pkg = base / "ep/shots/s1/build/packages/kid_0123456789abcdef"
    write(pkg / "character.json", {"skeleton": [{"name": "hips", "source_name": "DEF-hips"}]})
    write(pkg / "geometry.bin", b"\x00" * 64)
    write(base / "ep/content/assets/cube.asset.json", {"id": "prop.cube", "mesh": {"primitive": "box", "size": [1, 1, 1]}})
    write(base / "ep/content/assets/unused.asset.json", {"id": "prop.unused"})
    shot = write(base / "ep/shots/s1/shot.scene.json", {"frameStart": 1, "frameEnd": 4, "production": {
        "cast": {"kid": {"version_dir": "store/kid/versions/1.0.0"}}, "render": {"resolution": [64, 36], "samples": 2}}})
    scene = write(base / "ep/shots/s1/build/shot.resolved.scene.json",
                  {"characters": [{"name": "kid", "asset": "packages/kid_0123456789abcdef/character.json"}],
                   "props": [{"name": "c", "id": "prop.cube"}]})
    write(base / "ep/shots/s1/build/cast.json", {"kid": {"master": master, "character_id": "kid", "package": str(pkg)}})
    bake = write(base / "run/bake.json", {"format": "plush.shot_bake", "version": 1, "frames": [1, 4], "fps": [24, 1],
                                          "scene_path": scene, "render": {"width": 64, "height": 36},
                                          "characters": [{"name": "kid", "package": str(pkg / "character.json"),
                                                          "bones": ["hips"], "morphs": []}],
                                          "frame_data": [{"frame": f, "props": {"c": [1] * 16}} for f in range(1, 5)]})
    return {"bake": bake, "shot": shot, "master": master}


FAKE_BLENDER = r'''#!PYTHON
"""Fake Blender: checks, from the working folder, everything shot_render.py would read; writes frames + report."""
import ast, json, os, sys
argv = sys.argv[1:]
log = {"argv": argv, "cwd": os.getcwd(), "path": os.environ.get("PATH", ""), "problems": []}
P = log["problems"]
script = argv[argv.index("-P") + 1]
args = argv[argv.index("--") + 1:]
opt = lambda k: args[args.index(k) + 1]
if os.path.basename(script) != "shot_render.py" or not os.path.isfile(script):
    P.append(f"render script {script}")
here = os.path.dirname(script)
for node in ast.walk(ast.parse(open(script).read())):
    names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
        [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
    for n in names:
        if n.split(".")[0] in ("episode", "render_engine", "materials") and not (
                os.path.isfile(os.path.join(here, n.replace(".", "/") + ".py"))
                or os.path.isfile(os.path.join(here, n.split(".")[0], "__init__.py"))):
            P.append(f"module {n}")
if not os.path.isfile(os.path.join(here, "render_profiles.json")):
    P.append("render_profiles.json")
for k in ("--bake", "--cast"):
    if os.path.isabs(opt(k)) or not os.path.isfile(opt(k)):
        P.append(f"{k} {opt(k)}")
bake, cast = json.load(open(opt("--bake"))), json.load(open(opt("--cast")))
if os.path.isabs(bake["scene_path"]) or not os.path.isfile(bake["scene_path"]):
    P.append("scene_path " + bake["scene_path"])
for ch in bake["characters"]:
    info = cast[ch["name"]]
    if not os.path.isfile(info["master"]) or not os.path.isfile(os.path.join(info["package"], "character.json")):
        P.append("cast " + ch["name"])
lib = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(bake["scene_path"]))), "content", "assets")
ids = {json.load(open(os.path.join(lib, n)))["id"] for n in os.listdir(lib)} if os.path.isdir(lib) else set()
for p in json.load(open(bake["scene_path"])).get("props", []):
    if p["id"] not in ids:
        P.append("asset " + p["id"])
out = opt("--out")
os.makedirs(out, exist_ok=True)
fa, fb = bake["frames"]
for f in range(fa, fb + 1):
    open(os.path.join(out, f"frame_{f:04d}.png"), "wb").write(b"\x89PNG\r\n\x1a\n")
json.dump({"frames": [fa, fb], "not_rendered": []}, open(os.path.join(out, "shot_render.json"), "w"))
json.dump(log, open(os.environ["FAKE_BLENDER_LOG"], "w"))
sys.exit(1 if P else 0)
'''


def fake_blender(d):
    p = Path(d) / "fake_blender.py"
    p.write_text(FAKE_BLENDER.replace("#!PYTHON", "#!" + sys.executable))
    p.chmod(p.stat().st_mode | stat.S_IXUSR)
    return str(p)


def pack(fx, out):
    with contextlib.redirect_stdout(io.StringIO()):
        code = bp.main(["--from-bake", fx["bake"], "--shot", fx["shot"], "--out", str(out)])
    zips = sorted(Path(out).glob("*.bake.zip"))
    return code, zips[0] if zips else None


def run_pc(args):
    err, outp = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(outp):
        code = pc.main(args)
    return code, err.getvalue() + outp.getvalue()


def main():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        fx = fixture(td / "src")
        # 1. determinism
        c1, z1 = pack(fx, td / "out1")
        c2, z2 = pack(fx, td / "out2")
        check("pack succeeds", c1 == 0 and c2 == 0 and z1 is not None and z2 is not None)
        m1 = (z1.parent / z1.name[:-len(".bake.zip")] / "MANIFEST.json").read_bytes()
        m2 = (z2.parent / z2.name[:-len(".bake.zip")] / "MANIFEST.json").read_bytes()
        check("same input -> identical MANIFEST.json", m1 == m2)
        check("same input -> identical zip", z1.read_bytes() == z2.read_bytes())
        man = json.loads(m1)
        check("package name and frames", z1.name.startswith("ep_s1_") and man["frames"] == [1, 4]
              and "_f" not in z1.name, z1.name)
        check("no host paths in the package", str(td) not in (m1 + (z1.parent / z1.name[:-9] / "bake.json").read_bytes()
                                                                 + (z1.parent / z1.name[:-9] / "cast.json").read_bytes()).decode())
        check("only the named prop asset is packaged", "content/assets/cube.asset.json" in man["files"]
              and "content/assets/unused.asset.json" not in man["files"])
        check("engine-only geometry.bin is recorded, not shipped",
              "geometry.bin" in man["engine_packages"]["kid"] and not any(f.endswith("geometry.bin") for f in man["files"]))
        check("published manifest packaged", man["files"].get("characters/kid/manifest.json") is not None
              and man["cast_provenance"]["kid"]["published_version"] == "1.0.0")
        Path(fx["master"]).write_bytes(b"BLENDER-fake-master\x00\x02")
        man_path = Path(fx["master"]).parent / "manifest.json"
        vm = json.loads(man_path.read_text())
        vm["files"]["kid_master.blend"]["sha256"] = pc.sha256(fx["master"])
        man_path.write_text(json.dumps(vm))
        c3, z3 = pack(fx, td / "out3")
        m3 = json.loads((z3.parent / z3.name[:-9] / "MANIFEST.json").read_bytes())
        changed = sorted(k for k in man["files"] if man["files"][k] != m3["files"].get(k))
        check("a changed input changes exactly its files' hashes",
              changed == ["characters/kid/kid_master.blend", "characters/kid/manifest.json"], str(changed))

        # 2. completeness: the zip alone, in a clean folder, source tree gone, no engine on PATH
        clean = td / "pc"
        clean.mkdir()
        zc = clean / z1.name
        shutil.copyfile(z1, zc)
        shutil.rmtree(td / "src")
        blender = fake_blender(td)
        os.environ["FAKE_BLENDER_LOG"] = str(td / "fake_log.json")
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = str(td / "empty")
        try:
            code, text = run_pc([str(zc), "--blender", blender])
        finally:
            os.environ["PATH"] = old_path
        log = json.loads((td / "fake_log.json").read_text()) if (td / "fake_log.json").exists() else {"problems": ["no run"]}
        folder = clean / z1.name[:-9]
        check("render from the unpacked package alone", code == 0 and not log["problems"], f"{code} {log['problems']} {text[-500:]}")
        check("renders in the package folder", os.path.realpath(log.get("cwd", "")) == os.path.realpath(folder))
        check("frames and report written outside the package",
              sorted(p.name for p in (clean / f"{folder.name}_render_final720").glob("frame_*.png"))
              == [f"frame_{f:04d}.png" for f in range(1, 5)])
        check("shot's production.render applied (as run_shot)", "64" in log.get("argv", []) and
              log["argv"][log["argv"].index("--samples") + 1] == "2")
        check("render command never names the engine", not any("plush-render" in a for a in log.get("argv", [])))
        exe = [r for r in man["files"] if "plush-render" in r or r.endswith((".exe", ".dll", ".so"))]
        for r in man["files"]:
            head = (folder / r).read_bytes()[:4]
            if head in (b"\x7fELF", b"MZ\x90\x00") or os.stat(folder / r).st_mode & stat.S_IXUSR:
                exe.append(r)
        check("no executable in the package", not exe, str(exe))
        code, _ = run_pc([str(zc), "--verify-only"])
        check("an existing unpacked folder is re-verified", code == 0)

        # 3. verification failures stop the run before Blender
        def tampered(edit, label):
            d = td / f"t_{label}"
            shutil.copytree(folder, d / folder.name)
            edit(d / folder.name)
            (td / "fake_log.json").unlink(missing_ok=True)
            code, text = run_pc([str(d / folder.name), "--blender", blender])
            check(f"{label} file -> verification fails (exit 3)", code == 3 and not (td / "fake_log.json").exists(),
                  f"{code} {text[-300:]}")
            return text
        txt = tampered(lambda f: (f / "bake.json").write_bytes((f / "bake.json").read_bytes().replace(b'"fps"', b'"FPS"')),
                       "changed")
        check("message names the changed file", "changed (sha256 differs from the manifest): bake.json" in txt, txt)
        tampered(lambda f: (f / "content/assets/cube.asset.json").unlink(), "missing")
        tampered(lambda f: (f / "extra.py").write_text("print(1)"), "unlisted")
        evil = td / "evil.bake.zip"
        with zipfile.ZipFile(evil, "w") as z:
            z.writestr("pkg/MANIFEST.json", "{}")
            z.writestr("pkg/../../evil.txt", "x")
        code, _ = run_pc([str(evil), "--verify-only"])
        check("zip entry outside the package refused (exit 3)", code == 3 and not (td / "evil.txt").exists())

        # 4. missing profile
        code, text = run_pc([str(folder), "--profile", "no_such_profile", "--blender", blender])
        check("missing render profile -> clear failure (exit 2)", code == 2 and "not in this package" in text, text)
        profiles = json.loads((folder / man["render_profiles"]).read_text())
        if "preview_eevee" not in profiles["profiles"]:
            code, text = run_pc([str(folder), "--profile", "preview_eevee", "--verify-only"])
            check("--profile preview_eevee before T-201 -> clear failure", code == 2 and "preview_eevee" in text, text)

    # 5. render code list complete (real repository)
    try:
        bp.check_render_code(bp.render_code_files())
        ok = True
    except SystemExit as e:
        ok, detail = False, str(e.code)
    check("RENDER_CODE covers the render code's imports", ok, "" if ok else detail)
    shot_render = ast.parse((ROOT / "pipeline/charsys/shot_render.py").read_text(encoding="utf-8"))
    imported = {a.name for n in ast.walk(shot_render) if isinstance(n, ast.Import) for a in n.names}
    check("shot_render's local imports are packaged", {"episode", "render_engine"} <= imported and all(
        f"pipeline/charsys/{m}.py" in bp.RENDER_CODE for m in ("episode", "render_engine")))
    print("FAILED: " + ", ".join(FAILS) if FAILS else "all bake package tests passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
