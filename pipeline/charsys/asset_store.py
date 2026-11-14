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
  approve  --version <ver> --by "<owner>"     moves the "approved" pointer (owner decision only)
  verify   [--version <ver>]                  re-hashes files against the manifest
  restore  --version <ver> --to <dir>         copies a version out (verified), never writes into the store
  list
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


def publish(a):
    sd, cid = store_dir(a), a.character
    if not VERSION_RE.match(a.version):
        raise SystemExit("version must be x.y.z")
    vd = os.path.join(sd, a.version)
    if os.path.exists(vd):
        raise SystemExit(f"version {a.version} already exists: published versions are immutable; publish a new version")
    b = os.path.abspath(a.build)
    rep = json.load(open(os.path.join(b, "build_report.json")))
    spec = json.load(open(os.path.join(b, "spec.resolved.json")))
    if rep.get("character_id") != cid or spec["identity"]["id"] != cid:
        raise SystemExit(f"build is not {cid}")
    if S.sha256(spec) != rep["spec_sha256"]:
        raise SystemExit("spec.resolved.json does not match the spec hash stamped by the build")
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
    os.makedirs(vd)
    files = {}
    for f in payload(cid):
        src = os.path.join(b, "spec.resolved.json" if f == "spec.json" else f)
        if not os.path.exists(src):
            shutil.rmtree(vd)
            raise SystemExit(f"missing build output: {src}")
        dst = os.path.join(vd, f)
        shutil.copyfile(src, dst)
        files[f] = {"sha256": sha256_file(dst), "bytes": os.path.getsize(dst)}
    man = {"character_id": cid, "version": a.version, "parent": parent, "created": now(), "notes": a.notes,
           "spec_sha256": rep["spec_sha256"], "spec_version": spec["metadata"].get("spec_version"),
           "build": rep.get("build"), "blender": rep.get("blender"), "identity_changes": identity,
           "identity_change_approved_by": a.identity_change_approved_by or None, "files": files,
           "rig": {k: rep["rig"][k] for k in ("rigify_bones", "deform_bones", "unweighted_after_cleanup")}}
    json.dump(man, open(os.path.join(vd, "manifest.json"), "w"), indent=1)
    for f in os.listdir(vd):  # read-only: episode work cannot silently write into a published version
        os.chmod(os.path.join(vd, f), stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
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
    idx["history"].append({"at": now(), "action": "approve", "version": a.version, "previous": prev, "by": a.by})
    save_index(sd, idx)
    print(f"[asset_store] approved {cid} {a.version} (previous: {prev})")


def verify_version(sd, ver):
    vd = os.path.join(sd, ver)
    man = json.load(open(os.path.join(vd, "manifest.json")))
    bad = []
    for f, info in man["files"].items():
        p = os.path.join(vd, f)
        if not os.path.exists(p):
            bad.append(f"{f}: missing")
        elif sha256_file(p) != info["sha256"]:
            bad.append(f"{f}: hash mismatch")
        elif os.access(p, os.W_OK) and os.geteuid() != 0:
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
    if os.path.commonpath([to, sd]) == sd:
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


def list_(a):
    print(json.dumps(load_index(store_dir(a), a.character), indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["publish", "approve", "verify", "restore", "list"])
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
    a = ap.parse_args(argv)
    {"publish": publish, "approve": approve, "verify": verify, "restore": restore, "list": list_}[a.command](a)


if __name__ == "__main__":
    main()
