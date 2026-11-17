"""Versioned character asset store (plain Python, no Blender).

Layout (one immutable folder per version; nothing in a published version is ever rewritten):
  assets/characters/<id>/versions/index.json           versions, pointers ("approved", "reference"), history
  assets/characters/<id>/versions/<ver>/manifest.json  file list with sha256 and size, spec hash, parent, provenance
  assets/characters/<id>/versions/<ver>/<id>_master.blend   master: geometry, face controls, hair, clothing,
                                                         accessories, rig + weights, materials, landmarks (one file,
                                                         so rig, facial controls and materials stay together)
  assets/characters/<id>/versions/<ver>/<id>.glb       interchange export (meshes, skeleton, weights, morph targets)
  .../spec.json  components.json  animation_compat.json  build_report.json

Commands:
  publish  --build <dir> --version <x.y.z> --notes "..." [--parent <ver>] [--identity-change-approved-by "..."]
           [--without-glb]                    (the .glb is not needed for reuse: shots link the master)
  approve  --version <ver> --by "<owner>" [--notes "..."]   moves the "approved" pointer (owner decision only)
  verify   [--version <ver>]                  re-hashes files against the manifest
  restore  --version <ver> --to <dir>         copies a version out (verified), never writes into the store
  regenerate --version <ver> --blender <exe> --out <dir>    determinism check: rebuilds the version from its stored
           spec.json with the current code into <dir> (outside the store) and compares geometry fingerprints
           (fingerprint_v2, 0.1 mm and 0.01 mm grids) with the stored master; the store is only read
  list

Overwrite guard (T-075): nothing ever writes into a published version. publish refuses an existing version folder
and any version number the index has ever recorded (also after a folder was removed), and copies through a hidden
staging folder that is renamed into place only when complete. refuse_store_target() is the shared guard for every
other writer (build_character.py refuses assets/ itself; episode.py, run_shot.py and restore use this one).
All take [--store <dir>] (default assets/characters/<id>/versions) and [--character <id>].
Published files are made read-only. Episodes must link (not copy) the master; see episode.py."""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import stat
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import spec as S  # noqa: E402

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
STORES_GLOB = os.path.join(ROOT, "assets", "characters")


def store_of(path):
    """The asset store (a versions/ folder) that contains `path`, or None. A store is either a repository store
    (assets/characters/<id>/versions) or any folder holding an index.json whose ancestors include `path`'s
    published version folders (test stores in temporary folders)."""
    p = os.path.abspath(path)
    chars = os.path.abspath(STORES_GLOB)
    if os.path.commonpath([p, chars]) == chars:
        parts = os.path.relpath(p, chars).split(os.sep)
        if len(parts) >= 2 and parts[1] == "versions":
            return os.path.join(chars, parts[0], "versions")
    d = p
    while True:
        if os.path.isfile(os.path.join(d, "index.json")) and os.path.basename(d) == "versions" and \
                "character_id" in _safe_json(os.path.join(d, "index.json")):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            return None
        d = nd


def _safe_json(p):
    try:
        data = json.load(open(p, encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def refuse_store_target(path, what="output"):
    """Raises SystemExit when `path` lies inside an asset store: published versions are immutable, and new builds,
    shots and restores go to a build folder; a new version only through `publish`."""
    sd = store_of(path)
    if sd:
        raise SystemExit(f"refusing to write {what} into the asset store ({sd}): published versions are immutable; "
                         "write to a build folder and publish a new version")


MAX_FILE_BYTES = 95 * 1000 * 1000  # GitHub refuses files over 100 MB; keep a margin


def payload(cid):
    return [f"{cid}_master.blend", f"{cid}.glb", "spec.json", "components.json", "animation_compat.json", "build_report.json"]


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def store_dir(a):
    return os.path.abspath(a.store or os.path.join(ROOT, "assets", "characters", a.character, "versions"))


def load_index(sd, cid):
    p = os.path.join(sd, "index.json")
    if os.path.exists(p):
        return json.load(open(p))
    return {"character_id": cid, "versions": {}, "pointers": {"approved": None, "reference": None}, "history": []}


def save_index(sd, idx):
    p = os.path.join(sd, "index.json")
    tmp = p + ".tmp"
    json.dump(idx, open(tmp, "w"), indent=1)
    os.replace(tmp, p)  # atomic: a crash never leaves a half-written index


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def used_versions(idx):
    """Every version number the store has ever recorded (index entries and history): never reused."""
    return set(idx.get("versions", {})) | {h.get("version") for h in idx.get("history", []) if h.get("version")}


def input_spec_of(rep, resolved):
    """Builds on the body_generic path write spec.resolved.json AFTER fitting (eye positions, generated control
    list), so its hash is not the stamped input hash. For those builds the input spec is recomposed from the spec
    and overrides recorded in build_report.json and must match the stamped hash exactly; it becomes the version's
    spec.json (what regenerate rebuilds from) and the fitted file is stored as spec.resolved.json.
    Returns (input spec, fitted spec). Any other mismatch is refused (a spec edited after the build)."""
    if "body_generic" not in str(rep.get("build", "")) or not rep.get("spec_path"):
        raise SystemExit("spec.resolved.json does not match the spec hash stamped by the build")
    src = os.path.join(ROOT, rep["spec_path"])
    ovs = [os.path.join(ROOT, o) for o in rep.get("overrides", [])]
    if not all(os.path.isfile(p) for p in [src] + ovs):
        raise SystemExit("spec.resolved.json does not match the spec hash stamped by the build, and the build's input "
                         "spec files are not available to recompose it")
    spec, _ = S.load(src, ovs)
    if S.sha256(spec) != rep["spec_sha256"]:
        raise SystemExit("neither spec.resolved.json nor the recomposed input spec matches the spec hash stamped by "
                         "the build (inputs changed since the build?)")
    if spec.get("identity", {}).get("id") != resolved.get("identity", {}).get("id") or \
            S.canonical(spec.get("identity")) != S.canonical(resolved.get("identity")):
        raise SystemExit("spec.resolved.json is not a build of the recorded input spec")
    return spec, resolved


def publish(a):
    sd, cid = store_dir(a), a.character
    if not VERSION_RE.match(a.version or ""):
        raise SystemExit("version must be x.y.z")
    vd = os.path.join(sd, a.version)
    if os.path.lexists(vd):
        raise SystemExit(f"version {a.version} already exists: published versions are immutable; publish a new version")
    if a.version in used_versions(load_index(sd, cid)):
        raise SystemExit(f"version number {a.version} was already published (index history): version numbers are never "
                         "reused; publish a new version")
    b = os.path.abspath(a.build)
    if store_of(b):
        raise SystemExit("the build folder lies inside an asset store; build elsewhere (build_character.py --out)")
    rep = json.load(open(os.path.join(b, "build_report.json")))
    spec = json.load(open(os.path.join(b, "spec.resolved.json")))
    if rep.get("character_id") != cid or spec["identity"]["id"] != cid:
        raise SystemExit(f"build is not {cid}")
    resolved_out = None
    if S.sha256(spec) != rep["spec_sha256"]:
        spec, resolved_out = input_spec_of(rep, spec)
    if rep.get("rig", {}).get("unweighted_after_cleanup", 1) != 0:
        raise SystemExit("build has unweighted vertices; not publishable")
    idx = load_index(sd, cid)
    parent = a.parent or idx["pointers"].get("approved") or idx["pointers"].get("reference")
    identity = []
    if parent:
        pspec = json.load(open(os.path.join(sd, parent, "spec.json")))
        identity = S.identity_changes(pspec, spec)
        if identity and not a.identity_change_approved_by:
            raise SystemExit(f"identity sections changed vs {parent}: {identity}. Character identity is only changed with "
                             "explicit owner approval: pass --identity-change-approved-by \"<who, when>\"")
    os.makedirs(sd, exist_ok=True)
    stage = os.path.join(sd, f".{a.version}.partial")  # hidden staging folder, renamed into place when complete
    if os.path.lexists(stage):
        shutil.rmtree(stage)
    os.makedirs(stage)
    files, not_stored = {}, {}
    names = payload(cid) + (["spec.resolved.json"] if resolved_out is not None else [])
    for f in names:
        if a.without_glb and f == f"{cid}.glb":
            not_stored[f] = ("not needed for reuse: shots link the master and engine packages are exported from it "
                             "(run_shot.py); reproducible from the master")
            continue
        dst = os.path.join(stage, f)
        if f == "spec.json" and resolved_out is not None:  # the recomposed input spec (hash checked above)
            json.dump(spec, open(dst, "w"), indent=1)
        else:
            src = os.path.join(b, "spec.resolved.json" if f == "spec.json" else f)
            if not os.path.exists(src):
                shutil.rmtree(stage)
                raise SystemExit(f"missing build output: {src}")
            shutil.copyfile(src, dst)
        files[f] = {"sha256": sha256_file(dst), "bytes": os.path.getsize(dst)}
        if files[f]["bytes"] > MAX_FILE_BYTES:
            shutil.rmtree(stage)
            raise SystemExit(f"{f} is {files[f]['bytes']} bytes, over the {MAX_FILE_BYTES} byte limit (GitHub)")
    man = {"character_id": cid, "version": a.version, "parent": parent, "created": now(), "notes": a.notes,
           "spec_sha256": rep["spec_sha256"], "spec_version": spec["metadata"].get("spec_version"),
           "build": rep.get("build"), "blender": rep.get("blender"), "identity_changes": identity,
           "identity_change_approved_by": a.identity_change_approved_by or None, "files": files,
           "rig": {k: rep["rig"][k] for k in ("rigify_bones", "deform_bones", "unweighted_after_cleanup")}}
    if resolved_out is not None:
        man["spec_resolved"] = ("spec.resolved.json is the build's fitted spec (body_generic writes fitted values); "
                                "spec.json is the input spec it was built from (hash = spec_sha256)")
    if not_stored:  # key only present when something was left out, so earlier manifests keep their exact layout
        man["not_stored"] = not_stored
    json.dump(man, open(os.path.join(stage, "manifest.json"), "w"), indent=1)
    for f in os.listdir(stage):  # read-only: episode work cannot silently write into a published version
        os.chmod(os.path.join(stage, f), stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    if os.path.lexists(vd):  # re-checked right before the rename: never replace a published folder
        shutil.rmtree(stage)
        raise SystemExit(f"version {a.version} appeared while publishing; nothing written")
    os.rename(stage, vd)
    idx["versions"][a.version] = {"created": man["created"], "parent": parent, "notes": a.notes, "status": a.status,
                                  "spec_sha256": man["spec_sha256"]}
    if a.status == "reference":
        idx["pointers"]["reference"] = a.version
    idx["history"].append({"at": man["created"], "action": "publish", "version": a.version, "status": a.status})
    save_index(sd, idx)
    print(f"[asset_store] published {cid} {a.version} -> {vd}")


def approve(a):
    sd, cid = store_dir(a), a.character
    idx = load_index(sd, cid)
    if a.version not in idx["versions"]:
        raise SystemExit(f"unknown version {a.version}")
    if not a.by:
        raise SystemExit("--by is required (approval is an owner decision)")
    if verify_version(sd, a.version)["ok"] is not True:
        raise SystemExit("version failed verification; not approved")
    prev = idx["pointers"].get("approved")
    idx["pointers"]["approved"] = a.version
    idx["versions"][a.version]["status"] = "approved"
    entry = {"at": now(), "action": "approve", "version": a.version, "previous": prev, "by": a.by}
    if a.notes:
        entry["notes"] = a.notes
        idx["versions"][a.version]["approval_notes"] = a.notes
    idx["history"].append(entry)
    save_index(sd, idx)
    print(f"[asset_store] approved {cid} {a.version} (previous: {prev})")


def verify_version(sd, ver, require_readonly=True):
    """Hashes, spec hash and file list of one version. require_readonly=False skips the file-mode check (a git
    checkout does not keep read-only modes; tools/check_assets.py checks the diff instead)."""
    vd = os.path.join(sd, ver)
    man = json.load(open(os.path.join(vd, "manifest.json")))
    bad = []
    for f, info in man["files"].items():
        p = os.path.join(vd, f)
        if not os.path.exists(p):
            bad.append(f"{f}: missing")
        elif sha256_file(p) != info["sha256"]:
            bad.append(f"{f}: hash mismatch")
        elif require_readonly and os.access(p, os.W_OK) and hasattr(os, "geteuid") and os.geteuid() != 0:
            bad.append(f"{f}: writable")
    spec = json.load(open(os.path.join(vd, "spec.json")))
    if S.sha256(spec) != man["spec_sha256"]:
        bad.append("spec.json: spec hash mismatch")
    extra = sorted(set(os.listdir(vd)) - set(man["files"]) - {"manifest.json"})
    if extra:
        bad.append(f"unexpected files: {extra}")
    return {"version": ver, "ok": not bad, "problems": bad}


def verify(a):
    sd = store_dir(a)
    idx = load_index(sd, a.character)
    vers = [a.version] if a.version else sorted(idx["versions"])
    res = [verify_version(sd, v) for v in vers]
    print(json.dumps(res, indent=1))
    if not all(r["ok"] for r in res):
        raise SystemExit(1)


def restore(a):
    sd = store_dir(a)
    ver = a.version
    if ver in ("approved", "reference"):
        ver = load_index(sd, a.character)["pointers"].get(ver)
        if not ver:
            raise SystemExit(f"no {a.version} version")
    v = verify_version(sd, ver)
    if not v["ok"]:
        raise SystemExit(f"stored version {ver} failed verification: {v['problems']}")
    to = os.path.abspath(a.to)
    if os.path.commonpath([to, sd]) == sd or store_of(to):
        raise SystemExit("restore target must be outside the store")
    if os.path.exists(to) and os.listdir(to):
        raise SystemExit("restore target must be new or empty")
    os.makedirs(to, exist_ok=True)
    vd = os.path.join(sd, ver)
    for f in os.listdir(vd):
        shutil.copyfile(os.path.join(vd, f), os.path.join(to, f))
        os.chmod(os.path.join(to, f), stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    man = json.load(open(os.path.join(to, "manifest.json")))
    bad = [f for f, i in man["files"].items() if sha256_file(os.path.join(to, f)) != i["sha256"]]
    if bad:
        raise SystemExit(f"restored copy differs: {bad}")
    print(f"[asset_store] restored {a.character} {ver} -> {to} (verified)")


def _fingerprint(blender, master, out_json, grid, env):
    import subprocess
    subprocess.run([blender, "-b", "--factory-startup", "-t", "1", "-P", os.path.join(HERE, "fingerprint_v2.py"), "--",
                    master, out_json, "--grid-m", grid], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, check=True)
    data = json.load(open(out_json, encoding="utf-8"))
    data.pop("file", None)
    return data


def regenerate(a):
    """Determinism check: rebuild a stored version from its spec.json and compare geometry fingerprints."""
    import subprocess
    import determinism
    sd, cid = store_dir(a), a.character
    ver = a.version
    if ver in ("approved", "reference"):
        ver = load_index(sd, cid)["pointers"].get(ver)
        if not ver:
            raise SystemExit(f"no {a.version} version")
    if not a.blender or not a.out:
        raise SystemExit("regenerate needs --blender and --out")
    v = verify_version(sd, ver, require_readonly=False)
    if not v["ok"]:
        raise SystemExit(f"stored version {ver} failed verification: {v['problems']}")
    out = os.path.abspath(a.out)
    refuse_store_target(out, "the regenerated build")
    if os.path.exists(out) and os.listdir(out):
        raise SystemExit("--out must be new or empty")
    os.makedirs(out, exist_ok=True)
    vd = os.path.join(sd, ver)
    man = json.load(open(os.path.join(vd, "manifest.json")))
    master = os.path.join(vd, f"{cid}_master.blend")
    before = sha256_file(master)
    env = determinism.subprocess_env()
    build = os.path.join(out, "build")
    with open(os.path.join(out, "build.log"), "w") as log:
        subprocess.run([a.blender, "-b", "--factory-startup", "-t", "1", "-P", os.path.join(HERE, "build_character.py"),
                        "--", "--spec", os.path.join(vd, "spec.json"), "--out", build, "--no-glb", "--no-compare"],
                       cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    rep = json.load(open(os.path.join(build, "build_report.json")))
    res = {"character_id": cid, "version": ver, "spec_sha256_stored": man["spec_sha256"],
           "spec_sha256_rebuilt": rep.get("spec_sha256"), "grids": {}}
    ok = rep.get("spec_sha256") == man["spec_sha256"]
    for label, grid in (("0.1mm", "0.0001"), ("0.01mm", "0.00001")):
        fs = _fingerprint(a.blender, master, os.path.join(out, f"stored_{label}.json"), grid, env)
        fn = _fingerprint(a.blender, os.path.join(build, f"{cid}_master.blend"), os.path.join(out, f"rebuilt_{label}.json"),
                          grid, env)
        changed = sorted(n for n in set(fs.get("objects", {})) | set(fn.get("objects", {}))
                         if fs["objects"].get(n) != fn["objects"].get(n))
        same = fs == fn
        res["grids"][label] = {"identical": same, "changed_objects": changed,
                               "other_differences": sorted(k for k in set(fs) | set(fn) if k != "objects" and fs.get(k) != fn.get(k))}
        ok = ok and same
    res["stored_master_unchanged"] = sha256_file(master) == before
    res["pass"] = bool(ok and res["stored_master_unchanged"])
    json.dump(res, open(os.path.join(out, "regenerate.json"), "w"), indent=1, sort_keys=True)
    print(json.dumps(res, indent=1, sort_keys=True))
    if not res["pass"]:
        raise SystemExit(1)


def list_(a):
    print(json.dumps(load_index(store_dir(a), a.character), indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["publish", "approve", "verify", "restore", "regenerate", "list"])
    ap.add_argument("--character", default="boy_yellow_hoodie")
    ap.add_argument("--store", default="")
    ap.add_argument("--build")
    ap.add_argument("--version")
    ap.add_argument("--parent")
    ap.add_argument("--notes", default="")
    ap.add_argument("--status", default="candidate", choices=["candidate", "reference"])
    ap.add_argument("--identity-change-approved-by", default="")
    ap.add_argument("--by", default="")
    ap.add_argument("--to")
    ap.add_argument("--without-glb", action="store_true", help="publish: leave the .glb out (recorded in the manifest)")
    ap.add_argument("--blender", default="", help="regenerate: Blender executable")
    ap.add_argument("--out", default="", help="regenerate: new or empty folder outside the store")
    a = ap.parse_args(argv)
    {"publish": publish, "approve": approve, "verify": verify, "restore": restore, "regenerate": regenerate,
     "list": list_}[a.command](a)


if __name__ == "__main__":
    main()
