"""Renders a bake package (T-205) on the owner's PC with Blender alone: no engine executable, no prepare stage, no
change to any system setting.

    python tools/pc/render_package.py <package.zip | unpacked package folder>
        [--profile final720 | preview_eevee | review | legacy128] [--blender <blender.exe>] [--frames A-B]
        [--resolution W H] [--samples N] [--out <folder>] [--video] [--verify-only]

A bake package (plush.bake_package/1) is made in the cloud by pipeline/production/bake_package.py: the engine's
bake.json, the cast (character masters + the engine package files the renderer reads), the resolved scene, the prop
assets and the render code (pipeline/charsys/shot_render.py and what it imports), all listed with sha256 in
MANIFEST.json. This script:

  1. unpacks the zip next to it (into <zip folder>/<package name>/; an existing folder is re-verified, never
     trusted) - entries outside the package folder, links and duplicate names are refused;
  2. verifies every file against MANIFEST.json (missing, extra or changed files stop the run);
  3. renders with the package's own shot_render.py, exactly the command run_shot.py's render stage runs
     (resolution and samples: --resolution/--samples, else the shot's own production.render, else the profile;
     engine: --engine, else the profile's "engine" key, else cycles - T-201 preview_eevee renders with EEVEE);
  4. optionally (--video, needs ffmpeg on PATH) encodes shot.mp4 with the package's default delivery codec.

Outputs go to <zip folder>/<package name>_render_<profile>[-N]/ (a new folder per run) unless --out is given:
frame_####.png, shot.blend, shot_render.json, render.log. The package folder itself is never written to.

Runs with any Python 3.8+ (system Python or Blender's bundled python.exe): standard library only. Blender is found
from --blender, then the BLENDER environment variable, then `blender` on PATH, then the newest
"C:\\Program Files\\Blender Foundation\\Blender *\\blender.exe".
Exit codes: 0 done, 2 bad arguments / missing profile / no Blender, 3 package verification failed, 4 render failed."""
import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

FORMAT = "plush.bake_package"
VERSION = 1
MANIFEST = "MANIFEST.json"


class PackageError(Exception):
    """The package is incomplete, altered or unsafe to unpack (exit 3)."""


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_name(name):
    """A package-relative path: forward slashes, no drive, no absolute path, no '..' and no empty part."""
    parts = name.split("/")
    return (bool(name) and "\\" not in name and ":" not in name and not name.startswith("/")
            and all(p not in ("", ".", "..") for p in parts))


def list_files(folder):
    out = []
    for d, dirs, files in os.walk(folder):
        dirs.sort()
        for n in sorted(files):
            p = os.path.join(d, n)
            out.append(os.path.relpath(p, folder).replace(os.sep, "/"))
        for n in dirs:
            if os.path.islink(os.path.join(d, n)):
                raise PackageError(f"link in package: {os.path.relpath(os.path.join(d, n), folder)}")
    return out


def verify(folder):
    """Checks an unpacked package folder against its MANIFEST.json. Returns the manifest; raises PackageError with
    every problem found (missing, extra, changed files; unsafe names; wrong format)."""
    mpath = os.path.join(folder, MANIFEST)
    if not os.path.isfile(mpath):
        raise PackageError(f"{MANIFEST} missing in {folder}")
    try:
        man = json.load(open(mpath, encoding="utf-8"))
    except ValueError as e:
        raise PackageError(f"{MANIFEST} is not valid JSON: {e}")
    if man.get("format") != FORMAT or man.get("version") != VERSION:
        raise PackageError(f"not a {FORMAT}/{VERSION} package (format {man.get('format')!r} {man.get('version')!r})")
    files = man.get("files")
    if not isinstance(files, dict) or not files:
        raise PackageError(f"{MANIFEST} lists no files")
    problems = []
    for rel in sorted(files):
        if not safe_name(rel) or rel == MANIFEST:
            problems.append(f"unsafe file name in manifest: {rel!r}")
            continue
        p = os.path.join(folder, *rel.split("/"))
        if os.path.islink(p) or not os.path.isfile(p):
            problems.append(f"missing: {rel}")
        elif os.path.getsize(p) != files[rel].get("size") or sha256(p) != files[rel].get("sha256"):
            problems.append(f"changed (sha256 differs from the manifest): {rel}")
    extra = [r for r in list_files(folder) if r != MANIFEST and r not in files]
    problems += [f"not in the manifest: {r}" for r in extra]
    for key in ("bake", "cast", "render_entry", "render_profiles"):
        if man.get(key) not in files:
            problems.append(f"manifest entry {key!r} does not name a packaged file")
    if problems:
        raise PackageError("package verification failed:\n  " + "\n  ".join(problems))
    return man


def unpack(zip_path, dest_parent):
    """Unpacks <zip> into dest_parent/<package name>/ and verifies it. An existing folder of that name is verified
    instead (any difference stops the run: delete that folder to unpack again). Returns (folder, manifest)."""
    with zipfile.ZipFile(zip_path) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        tops = {n.split("/", 1)[0] for n in names}
        if len(tops) != 1:
            raise PackageError(f"{zip_path}: expected one top folder, found {sorted(tops)}")
        top = tops.pop()
        if len(set(n.lower() for n in names)) != len(names):
            raise PackageError(f"{zip_path}: duplicate entries (case-insensitive)")
        for i in infos:
            mode = (i.external_attr >> 16) & 0o170000
            if not safe_name(i.filename.rstrip("/")) or mode == 0o120000:
                raise PackageError(f"{zip_path}: unsafe entry {i.filename!r}")
        folder = os.path.join(dest_parent, top)
        if os.path.exists(folder):
            print(f"[render_package] {folder} exists: verifying it (delete it to unpack the zip again)")
            return folder, verify(folder)
        partial = folder + ".partial"
        if os.path.exists(partial):
            shutil.rmtree(partial)
        os.makedirs(partial)
        for i in infos:
            if i.is_dir():
                continue
            target = os.path.join(partial, *i.filename.split("/")[1:])
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(i) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
    try:
        man = verify(partial)
    except PackageError:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    os.replace(partial, folder)
    return folder, man


def find_blender(explicit):
    for c in (explicit, os.environ.get("BLENDER")):
        if c:
            if not (os.path.isfile(c) or shutil.which(c)):
                raise SystemExit(f"Blender not found at {c!r}")
            return c
    w = shutil.which("blender")
    if w:
        return w
    pf = [os.environ.get(k) for k in ("ProgramFiles", "ProgramW6432")] + [r"C:\Program Files"]
    found = []
    for base in filter(None, pf):
        found += glob.glob(os.path.join(base, "Blender Foundation", "Blender *", "blender.exe"))

    def ver(p):
        v = os.path.basename(os.path.dirname(p)).split(" ", 1)[-1]
        return [int(x) if x.isdigit() else 0 for x in v.split(".")]
    if found:
        return sorted(set(found), key=ver)[-1]
    raise SystemExit("Blender not found: pass --blender \"C:\\Program Files\\Blender Foundation\\Blender 5.3\\blender.exe\"")


def new_out(base):
    out, n = base, 1
    while os.path.exists(out) and os.listdir(out):
        n += 1
        out = f"{base}-{n}"
    return out


def render_command(folder, man, profiles, a, blender, out):
    """The render stage of run_shot.py (stages_run, "render"), with the package's paths relative to its folder."""
    pdata = profiles["profiles"][a.profile]
    r = man.get("production_render") or {}
    res = a.resolution or r.get("resolution") or pdata.get("resolution")
    samples = a.samples or r.get("samples") or pdata["samples"]
    engine = a.engine or pdata.get("engine") or "cycles"
    cmd = [blender, "-b", "--factory-startup", "-P", os.path.join(folder, *man["render_entry"].split("/")), "--",
           "--bake", man["bake"], "--cast", man["cast"], "--out", out,
           "--profile", a.profile, "--samples", str(samples), "--light-scale", str(r.get("light_scale", 1.0))]
    cmd += (["--resolution", str(res[0]), str(res[1])] if res else []) + (["--frames", a.frames] if a.frames else [])
    cmd += ["--engine", "eevee"] if engine == "eevee" else []
    return cmd, {"resolution": list(res) if res else None, "samples": samples, "engine": engine}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Verify and render a T-205 bake package with Blender (no engine).")
    ap.add_argument("package", help="the bake package .zip (or an unpacked package folder)")
    ap.add_argument("--profile", help="render profile (default: the package's default, final720)")
    ap.add_argument("--blender")
    ap.add_argument("--frames", default="", help="A-B (default: every baked frame)")
    ap.add_argument("--resolution", type=int, nargs=2)
    ap.add_argument("--samples", type=int)
    ap.add_argument("--engine", choices=("cycles", "eevee"), help="default: the profile's engine, else cycles")
    ap.add_argument("--out", help="output folder (default: next to the package, a new folder per run)")
    ap.add_argument("--video", action="store_true", help="also encode shot.mp4 (needs ffmpeg on PATH)")
    ap.add_argument("--verify-only", action="store_true", help="unpack and verify, do not render")
    a = ap.parse_args(argv)
    src = os.path.abspath(a.package)
    try:
        if os.path.isdir(src):
            folder, man = src, verify(src)
        elif zipfile.is_zipfile(src):
            folder, man = unpack(src, os.path.dirname(src))
        else:
            print(f"[render_package] not a zip or folder: {src}", file=sys.stderr)
            return 2
    except PackageError as e:
        print(f"[render_package] {e}", file=sys.stderr)
        return 3
    print(f"[render_package] verified {len(man['files'])} files of {os.path.basename(folder)} "
          f"(shot {man.get('shot')}, frames {man.get('frames')}, source commit {man.get('source_commit')})")
    profiles = json.load(open(os.path.join(folder, *man["render_profiles"].split("/")), encoding="utf-8"))
    a.profile = a.profile or profiles["default_profile"]
    if a.profile not in profiles["profiles"]:
        print(f"[render_package] render profile {a.profile!r} is not in this package (it has: "
              f"{', '.join(profiles['profiles'])}). The package was made at commit {man.get('source_commit')}; a "
              f"profile added later needs a package made from a newer commit.", file=sys.stderr)
        return 2
    if a.verify_only:
        return 0
    blender = find_blender(a.blender)
    out = os.path.abspath(a.out) if a.out else new_out(f"{folder}_render_{a.profile}")
    if os.path.commonpath([out, folder]) == folder:
        print("[render_package] the output folder must be outside the package folder", file=sys.stderr)
        return 2
    os.makedirs(out, exist_ok=True)
    cmd, eff = render_command(folder, man, profiles, a, blender, out)
    print(f"[render_package] rendering with {blender}: profile {a.profile}, {eff['engine']}, resolution "
          f"{eff['resolution'] or 'from the bake'}, {eff['samples']} samples -> {out}")
    log = os.path.join(out, "render.log")
    if os.name == "nt" and cmd[0].lower().endswith(".py"):  # a test's fake Blender
        cmd = [sys.executable] + cmd
    with open(log, "w", encoding="utf-8", errors="replace") as lf:
        p = subprocess.run(cmd, cwd=folder, stdout=lf, stderr=subprocess.STDOUT)  # package-relative paths
    if p.returncode != 0:
        tail = open(log, encoding="utf-8", errors="replace").read()[-1500:]
        print(f"[render_package] Blender failed ({p.returncode}); see {log}\n{tail}", file=sys.stderr)
        return 4
    if a.video:
        ff = shutil.which("ffmpeg")
        if not ff:
            print("[render_package] --video: ffmpeg not on PATH; frames are rendered, no shot.mp4", file=sys.stderr)
        else:
            rep = json.load(open(os.path.join(out, "shot_render.json"), encoding="utf-8"))
            num, den = man.get("fps", [24, 1])
            codec = profiles["encode"]["codecs"][profiles["encode"]["default"]]["args"]
            v = subprocess.run([ff, "-y", "-loglevel", "error", "-framerate", f"{num}/{den}", "-start_number",
                                str(rep["frames"][0]), "-i", os.path.join(out, "frame_%04d.png"), *codec,
                                os.path.join(out, "shot.mp4")])
            if v.returncode != 0:
                print("[render_package] ffmpeg failed; frames are rendered", file=sys.stderr)
                return 4
    print(f"[render_package] done: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
