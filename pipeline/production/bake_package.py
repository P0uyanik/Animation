"""Bake packages (T-205): bake a shot in the cloud (Linux engine), render it anywhere with Blender alone.

    python3 pipeline/production/bake_package.py --shot episodes/<ep>/shots/<shot>/shot.scene.json --blender <blender>
        [--bake-engine build/apps/render-cli/plush-render] [--frames A-B] [--out build/bake_packages]
        [--smoke A-B]
    python3 pipeline/production/bake_package.py --from-bake <run dir>/bake.json [--shot <shot.scene.json>] [--out ...]
    python3 pipeline/production/bake_package.py --verify <package folder or .zip>

The first form runs run_shot.py's prepare and bake stages (--stages prepare,bake into a fresh --run-dir under
<out>/work/) and packs the result; --from-bake packs an existing bake (its cast.json is the one beside the bake's
resolved scene, i.e. the shot's build folder). Output: <out>/<name>/ and <out>/<name>.bake.zip (+ .zip.sha256), where
<name> = <episode>_<shot>_<commit 10>[_f<A>-<B> when the bake is a frame subset].

Package (plush.bake_package/1; every path relative to the package folder, which is the render's working folder):
  MANIFEST.json                         format, shot, frames, fps, production.render, source commit (+ dirty flag),
                                        cast provenance, engine-package file hashes, and "files": sha256 + size of
                                        every other file in the package (nothing unlisted is allowed)
  bake.json                             the engine bake; scene_path and character packages rewritten package-relative
  cast.json                             shot_render.py's cast (master, character_id, package; package-relative)
  scene/shot.resolved.scene.json        the scene the engine baked (props -> asset ids)
  characters/<name>/<cid>_master.blend  the linked master (checked: no external files or libraries)
  characters/<name>/manifest.json       its published-version manifest (when it comes from the asset store)
  characters/<name>/package/character.json  the engine package file the renderer reads (geometry.bin is engine-only:
                                        its hash is recorded, the file is not shipped)
  content/assets/<id>.asset.json        the prop assets the scene names (shot_render finds content/assets above
                                        the scene)
  code/pipeline/charsys/...             shot_render.py and everything it imports or reads (render_profiles.json,
                                        materials), from the source commit
No engine executable. Deterministic: same bake, cast and source tree -> byte-identical MANIFEST.json and zip (fixed
entry order, timestamps and permissions; no host paths, no timings). Rendering: tools/pc/render_package.py, which
also holds the verifier used by --verify."""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHARSYS = os.path.join(ROOT, "pipeline", "charsys")
FORMAT, VERSION = "plush.bake_package", 1
SCENE_REL = "scene/shot.resolved.scene.json"
RENDER_ENTRY = "code/pipeline/charsys/shot_render.py"
PROFILES_REL = "code/pipeline/charsys/render_profiles.json"
# shot_render.py and what it imports or reads at render time (repository paths). check_render_code() keeps this
# list honest: every pipeline/charsys module imported by a listed file must be listed.
RENDER_CODE = ["pipeline/charsys/shot_render.py", "pipeline/charsys/episode.py", "pipeline/charsys/render_engine.py",
               "pipeline/charsys/geom.py", "pipeline/charsys/render_profiles.json", "pipeline/charsys/hair_pushout.py",
               "pipeline/charsys/materials/__init__.py",
               "pipeline/charsys/materials/builder.py"]
ZIP_TIME = (1980, 1, 1, 0, 0, 0)
DEPS_SCRIPT = """import bpy, json, sys
out = {}
for m in sys.argv[sys.argv.index("--") + 1:]:
    bpy.ops.wm.open_mainfile(filepath=m)
    out[m] = sorted(set(bpy.utils.blend_paths(absolute=True, packed=False, local=False))
                    | {l.filepath for l in bpy.data.libraries})
print("BAKE_PACKAGE_DEPS " + json.dumps(out))
"""


_PC = []


def load_pc_tool():
    """tools/pc/render_package.py (standard library only): the verifier and renderer shared with the PC."""
    if _PC:
        return _PC[0]
    spec = importlib.util.spec_from_file_location("render_package", os.path.join(ROOT, "tools", "pc", "render_package.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _PC.append(mod)
    return mod


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def render_code_files():
    """RENDER_CODE plus every material JSON the material library loads."""
    mats = os.path.join(CHARSYS, "materials")
    extra = sorted(f"pipeline/charsys/materials/{n}" for n in os.listdir(mats) if n.endswith(".json"))
    return RENDER_CODE + extra


def check_render_code(files):
    """Every pipeline/charsys module imported (anywhere, also inside functions) by a packaged .py file is packaged."""
    have = set(files)
    missing = []
    for rel in files:
        if not rel.endswith(".py"):
            continue
        tree = ast.parse(open(os.path.join(ROOT, rel), encoding="utf-8").read())
        base = os.path.dirname(rel)
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            for n in names:
                for cand in (f"pipeline/charsys/{n.replace('.', '/')}.py",
                             f"pipeline/charsys/{n.replace('.', '/')}/__init__.py", f"{base}/{n}.py"):
                    if os.path.isfile(os.path.join(ROOT, cand)) and cand not in have:
                        # episode.py imports asset_store only in its own command-line main(), never at render time
                        if not (rel.endswith("episode.py") and n == "asset_store"):
                            missing.append(f"{rel} imports {cand}")
    if missing:
        raise SystemExit("bake package: render code list incomplete (RENDER_CODE):\n  " + "\n  ".join(missing))


def git(*args):
    try:
        return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def find_assets_dir(scene_path):
    """shot_render.find_assets: the nearest content/assets above the baked scene."""
    d = os.path.dirname(os.path.abspath(scene_path))
    while True:
        lib = os.path.join(d, "content", "assets")
        if os.path.isdir(lib):
            return lib
        if os.path.dirname(d) == d:
            return None
        d = os.path.dirname(d)


def jbytes(obj):
    return (json.dumps(obj, indent=1, sort_keys=True) + "\n").encode("utf-8")


def collect(bake_path, shot_path=None, blender=None):
    """The package contents: ({package path: bytes or source file path}, manifest without "files")."""
    bake = json.load(open(bake_path, encoding="utf-8"))
    if bake.get("format") != "plush.shot_bake" or bake.get("version") != 1:
        raise SystemExit(f"{bake_path}: not a plush.shot_bake/1 file")
    scene_path = bake["scene_path"]
    build = os.path.dirname(os.path.abspath(scene_path))
    cast_path = os.path.join(build, "cast.json")
    if not os.path.isfile(cast_path):
        raise SystemExit(f"no cast.json beside the baked scene ({cast_path}): run the prepare stage")
    cast = json.load(open(cast_path, encoding="utf-8"))
    scene = json.load(open(scene_path, encoding="utf-8"))
    if shot_path is None:
        prep = os.path.join(os.path.dirname(os.path.abspath(bake_path)), "prepare.json")
        shot_path = os.path.join(ROOT, json.load(open(prep))["shot"]) if os.path.isfile(prep) else os.path.join(
            os.path.dirname(build), "shot.scene.json")
    shot = json.load(open(shot_path, encoding="utf-8"))
    entries = {SCENE_REL: scene_path}
    pcast, prov = {}, {}
    engine_pkgs = {}
    for ch in bake["characters"]:
        name = ch["name"]
        if name not in cast:
            raise SystemExit(f"cast.json has no entry for baked character {name}")
        info = cast[name]
        cid, master = info["character_id"], info["master"]
        base = f"characters/{name}"
        mrel = f"{base}/{os.path.basename(master)}"
        entries[mrel] = master
        man_path = os.path.join(os.path.dirname(master), "manifest.json")
        msha = load_pc_tool().sha256(master)
        p = {"character_id": cid, "master_sha256": msha, **({"version": info["version"]} if "version" in info else {})}
        if os.path.isfile(man_path):
            vman = json.load(open(man_path, encoding="utf-8"))
            if vman.get("files", {}).get(os.path.basename(master), {}).get("sha256") == msha:
                entries[f"{base}/manifest.json"] = man_path
                p["published_version"] = vman.get("version")
            elif vman.get("character_id") == cid:
                raise SystemExit(f"{name}: master {master} does not match its manifest")
        pkg = info["package"]
        entries[f"{base}/package/character.json"] = os.path.join(pkg, "character.json")
        engine_pkgs[name] = {n: {"sha256": load_pc_tool().sha256(os.path.join(pkg, n)),
                                 "size": os.path.getsize(os.path.join(pkg, n))}
                             for n in sorted(os.listdir(pkg)) if os.path.isfile(os.path.join(pkg, n))}
        p["engine_package"] = os.path.basename(pkg)
        pcast[name] = {"master": mrel, "character_id": cid, "package": f"{base}/package",
                       **({"version": info["version"]} if "version" in info else {})}
        prov[name] = p
        ch["package"] = f"{base}/package/character.json"
    # prop assets named by the scene
    lib = find_assets_dir(scene_path)
    by_id = {}
    if lib:
        for n in sorted(os.listdir(lib)):
            if n.endswith(".asset.json"):
                by_id[json.load(open(os.path.join(lib, n), encoding="utf-8")).get("id")] = os.path.join(lib, n)
    missing_assets = []
    for prop in scene.get("props", []):
        pid = prop.get("id")
        if pid in by_id:
            entries[f"content/assets/{os.path.basename(by_id[pid])}"] = by_id[pid]
        else:
            missing_assets.append(pid)
    # render code
    code = render_code_files()
    check_render_code(code)
    for rel in code:
        entries[f"code/{rel}"] = os.path.join(ROOT, rel)
    if blender:
        check_master_deps(blender, [cast[c["name"]]["master"] for c in bake["characters"]])
    bake["scene_path"] = SCENE_REL
    entries["bake.json"] = (json.dumps(bake, indent=1) + "\n").encode("utf-8")
    entries["cast.json"] = jbytes(pcast)
    commit = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain", "--untracked-files=no"))
    shot_rel = os.path.relpath(os.path.abspath(shot_path), ROOT).replace(os.sep, "/")
    if shot_rel.startswith("../"):  # a shot outside the repository: no host path in the package
        shot_rel = "/".join(shot_rel.split("/")[-4:])
    meta = {"format": FORMAT, "version": VERSION, "shot": shot_rel, "scene": bake.get("scene", ""),
            "frames": bake["frames"], "shot_frames": [shot.get("frameStart", 1), shot.get("frameEnd", 48)],
            "fps": bake["fps"], "production_render": (shot.get("production") or {}).get("render", {}),
            "source_commit": commit, "source_dirty": dirty, "bake": "bake.json", "cast": "cast.json",
            "render_entry": RENDER_ENTRY, "render_profiles": PROFILES_REL, "cast_provenance": prov,
            "engine_packages": engine_pkgs, "missing_prop_assets": missing_assets,
            "engine_executable": "not included: render with Blender only (tools/pc/render_package.py)"}
    return entries, meta


def check_master_deps(blender, masters):
    """Fails when a master links a library or an unpacked file outside itself (the package would be incomplete)."""
    with tempfile.TemporaryDirectory() as td:
        script = os.path.join(td, "deps.py")
        open(script, "w").write(DEPS_SCRIPT)
        p = subprocess.run([blender, "-b", "--factory-startup", "-P", script, "--", *masters], capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
    line = next((ln for ln in (p.stdout + p.stderr).splitlines() if ln.startswith("BAKE_PACKAGE_DEPS ")), None)
    if p.returncode != 0 or line is None:
        raise SystemExit(f"master dependency check failed ({p.returncode}):\n{(p.stdout + p.stderr)[-1500:]}")
    deps = {m: d for m, d in json.loads(line.split(" ", 1)[1]).items() if d}
    if deps:
        raise SystemExit(f"masters use external files (not packable): {json.dumps(deps, indent=1)}")


def package_name(meta, shot_frames):
    parts = meta["shot"].split("/")
    ep, shot = (parts[-4], parts[-2]) if len(parts) >= 4 else ("shot", parts[-2] if len(parts) > 1 else "shot")
    name = f"{ep}_{shot}_{(meta['source_commit'] or 'nocommit')[:10]}"
    if list(meta["frames"]) != list(shot_frames):
        name += f"_f{meta['frames'][0]}-{meta['frames'][1]}"
    return name


def write_package(entries, meta, out_dir, name):
    """Writes <out>/<name>/ and <out>/<name>.bake.zip deterministically. Returns (folder, zip path, zip sha256)."""
    folder = os.path.join(out_dir, name)
    if os.path.exists(folder):
        shutil.rmtree(folder)
    files = {}
    for rel in sorted(entries):
        src = entries[rel]
        dst = os.path.join(folder, *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if isinstance(src, bytes):
            open(dst, "wb").write(src)
        else:
            shutil.copyfile(src, dst)
        files[rel] = {"sha256": load_pc_tool().sha256(dst), "size": os.path.getsize(dst)}
    man = dict(meta, files=files)
    open(os.path.join(folder, "MANIFEST.json"), "wb").write(jbytes(man))
    zpath = os.path.join(out_dir, f"{name}.bake.zip")
    tmp = zpath + ".tmp"
    with zipfile.ZipFile(tmp, "w") as z:
        for rel in ["MANIFEST.json"] + sorted(files):
            info = zipfile.ZipInfo(f"{name}/{rel}", date_time=ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            src = os.path.join(folder, *rel.split("/"))
            with open(src, "rb") as f, z.open(info, "w", force_zip64=os.path.getsize(src) > 1 << 30) as zf:
                shutil.copyfileobj(f, zf, 1 << 20)
    os.replace(tmp, zpath)
    zsha = load_pc_tool().sha256(zpath)
    open(zpath + ".sha256", "w").write(f"{zsha}  {os.path.basename(zpath)}\n")
    return folder, zpath, zsha


def smoke(zpath, frames, blender):
    """Unpacks the zip into a clean temporary folder and renders a few frames at tiny settings with
    tools/pc/render_package.py (Blender only: no engine, no prepare)."""
    pc = load_pc_tool()
    with tempfile.TemporaryDirectory(prefix="bake_package_smoke_") as td:
        z = os.path.join(td, os.path.basename(zpath))
        shutil.copyfile(zpath, z)
        out = os.path.join(td, "render")
        code = pc.main([z, "--blender", blender, "--frames", frames, "--resolution", "160", "90", "--samples", "1",
                        "--out", out])
        if code != 0:
            raise SystemExit(f"smoke render from the package failed ({code})")
        rep = json.load(open(os.path.join(out, "shot_render.json")))
        pngs = sorted(n for n in os.listdir(out) if n.startswith("frame_") and n.endswith(".png"))
        return {"frames": rep.get("frames"), "pngs": pngs, "not_rendered": rep.get("not_rendered")}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--shot")
    ap.add_argument("--blender")
    ap.add_argument("--bake-engine", default=os.path.join(ROOT, "build", "apps", "render-cli", "plush-render"))
    ap.add_argument("--frames", default="", help="bake only these frames (A-B)")
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "bake_packages"))
    ap.add_argument("--from-bake", help="pack an existing bake.json instead of running prepare + bake")
    ap.add_argument("--smoke", default="", help="after packing, render these frames (A-B) from the unpacked zip")
    ap.add_argument("--verify", help="verify a package folder or zip and exit")
    a = ap.parse_args(argv)
    if a.verify:
        pc = load_pc_tool()
        return pc.main([a.verify, "--verify-only"])
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    if a.from_bake:
        bake_path = os.path.abspath(a.from_bake)
    else:
        if not (a.shot and a.blender):
            ap.error("--shot and --blender are needed (or --from-bake)")
        if not os.path.isfile(a.bake_engine):
            ap.error(f"bake engine not found: {a.bake_engine}")
        os.makedirs(os.path.join(out, "work"), exist_ok=True)
        work = tempfile.mkdtemp(prefix="run_", dir=os.path.join(out, "work"))
        cmd = [sys.executable, os.path.join(ROOT, "pipeline", "production", "run_shot.py"), "--shot", a.shot,
               "--blender", a.blender, "--bake-engine", a.bake_engine, "--stages", "prepare,bake",
               "--run-dir", os.path.join(work, "run")] + (["--frames", a.frames] if a.frames else [])
        print("[bake_package] " + " ".join(cmd), flush=True)
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode != 0:
            raise SystemExit(f"prepare/bake failed ({p.returncode}):\n{(p.stdout + p.stderr)[-2500:]}")
        bake_path = os.path.join(work, "run", "bake.json")
    entries, meta = collect(bake_path, os.path.abspath(a.shot) if a.shot else None, a.blender)
    name = package_name(meta, meta["shot_frames"])
    folder, zpath, zsha = write_package(entries, meta, out, name)
    load_pc_tool().verify(folder)
    size = os.path.getsize(zpath)
    print(f"[bake_package] {zpath} ({size / 1e6:.1f} MB, sha256 {zsha}){' [source tree dirty]' if meta['source_dirty'] else ''}")
    if a.smoke:
        if not a.blender:
            ap.error("--smoke needs --blender")
        print("[bake_package] smoke render: " + json.dumps(smoke(zpath, a.smoke, a.blender)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
