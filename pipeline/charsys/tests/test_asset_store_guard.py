"""T-075 tests: the overwrite guard of the asset store and tools/check_assets.py (plain Python; temporary stores and
a temporary git repository, never the real store, except the read-only generator test below).

    python3 pipeline/charsys/tests/test_asset_store_guard.py [--blender <exe>] [--out <result.json>]

With --blender, build_character.py (the generator) is pointed at a real published version folder and must refuse
before writing anything; every file of that version is hashed before and after (byte-identical)."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import asset_store as AS  # noqa: E402
import spec as S  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import check_assets as CA  # noqa: E402

RESULTS = []
CID = "c_test"


def check(name, ok, detail=None):
    RESULTS.append({"check": name, "pass": bool(ok), "detail": detail})
    print(f"[test_asset_store_guard] {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}",
          flush=True)


def code(fn, *args):
    try:
        r = fn(list(args))
        return r if isinstance(r, int) else 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1


def store(*args):
    return code(AS.main, "--character", CID, *args)


def tree_hashes(d):
    out = {}
    for base, _, files in os.walk(d):
        for f in files:
            p = os.path.join(base, f)
            out[os.path.relpath(p, d)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


def fake_build(d, cid=CID, note="", spec=None, build="charsys/1", extra_report=None):
    """A build folder with the layout build_character.py writes (contents are placeholders)."""
    os.makedirs(d)
    spec = spec or {"identity": {"id": cid}, "proportions": {"h": 1.0}, "metadata": {"spec_version": "1.0.0",
                                                                                     "notes": note}}
    json.dump(spec, open(os.path.join(d, "spec.resolved.json"), "w"), indent=1)
    rep = {"character_id": cid, "spec_sha256": S.sha256(spec), "build": build, "blender": "test",
           "rig": {"rigify_bones": 1, "deform_bones": 1, "unweighted_after_cleanup": 0}}
    rep.update(extra_report or {})
    json.dump(rep, open(os.path.join(d, "build_report.json"), "w"), indent=1)
    for f in (f"{cid}_master.blend", f"{cid}.glb"):
        open(os.path.join(d, f), "wb").write(os.urandom(64) + note.encode())
    for f in ("components.json", "animation_compat.json"):
        json.dump({"f": f, "note": note}, open(os.path.join(d, f), "w"))
    return d


def test_publish_guard(tmp):
    st = os.path.join(tmp, "versions")
    b1, b2 = fake_build(os.path.join(tmp, "b1"), note="one"), fake_build(os.path.join(tmp, "b2"), note="two")
    check("publish 1.0.0", store("publish", "--store", st, "--build", b1, "--version", "1.0.0", "--status", "reference") == 0)
    before = tree_hashes(st)
    check("overwrite of a published version refused (non-zero exit)",
          store("publish", "--store", st, "--build", b2, "--version", "1.0.0") != 0)
    check("refused overwrite leaves every store file byte-identical (incl. index.json)", tree_hashes(st) == before)
    # a version number is never reused, even when its folder has gone (index history keeps it)
    st2 = os.path.join(tmp, "copy", "versions")
    shutil.copytree(st, st2)
    for base, dirs, files in os.walk(os.path.join(st2, "1.0.0")):
        for f in files:
            os.chmod(os.path.join(base, f), 0o644)
    shutil.rmtree(os.path.join(st2, "1.0.0"))
    check("reusing a version number recorded in the index refused (folder removed)",
          store("publish", "--store", st2, "--build", b2, "--version", "1.0.0") != 0)
    check("refused publish writes nothing", not os.path.exists(os.path.join(st2, "1.0.0"))
          and not any(d.startswith(".") for d in os.listdir(st2)))
    # a build folder inside the store is refused
    inside = os.path.join(st, "1.0.0")
    check("publish from a build folder inside the store refused",
          store("publish", "--store", st, "--build", inside, "--version", "1.1.0") != 0)
    check("store_of finds the store for paths inside it", AS.store_of(os.path.join(st, "1.0.0", "x.blend")) == st
          and AS.store_of(tmp) is None, AS.store_of(os.path.join(st, "1.0.0", "x.blend")))
    check("repository stores are recognised (no file needed)",
          AS.store_of(os.path.join(ROOT, "assets", "characters", "any_id", "versions", "9.9.9")) ==
          os.path.join(ROOT, "assets", "characters", "any_id", "versions"))
    check("refuse_store_target refuses the store and accepts a build folder",
          code(lambda _: AS.refuse_store_target(os.path.join(st, "1.0.0", "out"))) != 0
          and code(lambda _: AS.refuse_store_target(os.path.join(tmp, "build"))) == 0)
    check("restore into the store refused",
          store("restore", "--store", st, "--version", "1.0.0", "--to", os.path.join(st, "restored")) != 0)
    # new version: published through the staging folder; --without-glb records the omission
    check("publish 1.1.0 without the glb",
          store("publish", "--store", st, "--build", b2, "--version", "1.1.0", "--without-glb") == 0)
    man = json.load(open(os.path.join(st, "1.1.0", "manifest.json")))
    check("manifest records the glb as not stored; no glb file; no staging folder left",
          f"{CID}.glb" in man.get("not_stored", {}) and f"{CID}.glb" not in man["files"]
          and not os.path.exists(os.path.join(st, "1.1.0", f"{CID}.glb"))
          and not any(d.startswith(".") for d in os.listdir(st)), sorted(man["files"]))
    check("verify passes for both versions", store("verify", "--store", st) == 0)
    check("1.0.0 untouched by the 1.1.0 publish",
          {k: v for k, v in tree_hashes(st).items() if k.startswith("1.0.0")} ==
          {k: v for k, v in before.items() if k.startswith("1.0.0")})
    # approve records notes
    check("approve with notes", store("approve", "--store", st, "--version", "1.1.0", "--by", "test owner",
                                      "--notes", "intermediate") == 0)
    idx = json.load(open(os.path.join(st, "index.json")))
    check("approval notes recorded in the entry and the history",
          idx["versions"]["1.1.0"].get("approval_notes") == "intermediate" and idx["history"][-1].get("notes") == "intermediate"
          and idx["pointers"]["approved"] == "1.1.0", idx["pointers"])


def test_input_spec(tmp):
    """body_generic builds: spec.resolved.json holds fitted values; the input spec is recomposed and hash-checked."""
    st = os.path.join(tmp, "versions_generic")
    spec_rel = "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json"
    ovr_rel = "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.10.0.override.json"
    spec, _ = S.load(os.path.join(ROOT, spec_rel), [os.path.join(ROOT, ovr_rel)])
    cid = spec["identity"]["id"]
    fitted = json.loads(json.dumps(spec))
    fitted.setdefault("face", {})["expression_shape_keys"] = ["fitted"]
    inputs = {"spec_path": spec_rel, "overrides": [ovr_rel]}

    def build(name, resolved, buildid="charsys/1+body_generic/1", rep_spec=None):
        d = fake_build(os.path.join(tmp, name), cid=cid, spec=resolved, build=buildid, extra_report=inputs)
        rp = os.path.join(d, "build_report.json")
        rep = json.load(open(rp))
        rep["spec_sha256"] = S.sha256(rep_spec or spec)
        json.dump(rep, open(rp, "w"))
        return d

    ok = code(AS.main, "--character", cid, "publish", "--store", st, "--build", build("g1", fitted), "--version", "0.1.0",
              "--without-glb") == 0
    man = json.load(open(os.path.join(st, "0.1.0", "manifest.json"))) if ok else {}
    stored = json.load(open(os.path.join(st, "0.1.0", "spec.json"))) if ok else {}
    check("body_generic build: spec.json is the recomposed input spec, spec.resolved.json the fitted output",
          ok and S.sha256(stored) == man["spec_sha256"] == S.sha256(spec) and "spec.resolved.json" in man["files"])
    check("verify of that version passes", code(AS.main, "--character", cid, "verify", "--store", st) == 0)
    legacy = build("g2", fitted, buildid="charsys/1")
    check("legacy build with a spec that differs from its stamped hash still refused",
          code(AS.main, "--character", cid, "publish", "--store", st, "--build", legacy, "--version", "0.2.0") != 0)
    other = json.loads(json.dumps(fitted))
    other["identity"]["display_name"] = "someone else"
    check("fitted spec of another identity refused",
          code(AS.main, "--character", cid, "publish", "--store", st, "--build", build("g3", other), "--version", "0.3.0") != 0)
    wrong = json.loads(json.dumps(spec))
    wrong["metadata"]["notes"] = "inputs changed"
    check("inputs that do not match the stamped hash refused",
          code(AS.main, "--character", cid, "publish", "--store", st, "--build", build("g4", fitted, rep_spec=wrong),
               "--version", "0.4.0") != 0)


def test_run_shot_guard(tmp):
    st = os.path.join(tmp, "versions")  # the store made by test_publish_guard
    shot = os.path.join(st, "1.0.0", "shots", "s.scene.json")
    sys.path.insert(0, os.path.join(ROOT, "pipeline", "production"))
    import run_shot
    argv = sys.argv
    sys.argv = ["run_shot.py", "--shot", shot, "--blender", "unused"]
    try:
        rc = code(lambda _: run_shot.main())
    finally:
        sys.argv = argv
    check("run_shot refuses a shot build folder inside the store", rc != 0 and not os.path.exists(os.path.dirname(shot)))
    sys.argv = ["run_shot.py", "--shot", os.path.join(tmp, "shot", "s.scene.json"), "--blender", "unused",
                "--run-dir", os.path.join(st, "1.0.0", "run")]
    try:
        rc = code(lambda _: run_shot.main())
    finally:
        sys.argv = argv
    check("run_shot refuses a --run-dir inside the store", rc != 0 and not os.path.exists(os.path.join(st, "1.0.0", "run")))


def test_check_assets(tmp):
    repo = os.path.join(tmp, "repo")
    sd = os.path.join(repo, "assets", "characters", CID, "versions")
    os.makedirs(os.path.dirname(sd))
    b = fake_build(os.path.join(tmp, "ca_build"), note="ca")
    if store("publish", "--store", sd, "--build", b, "--version", "1.0.0") != 0:
        check("check_assets fixture", False)
        return
    g = lambda *a: subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True, check=True)  # noqa: E731
    g("init", "-q")
    g("-c", "user.name=t", "-c", "user.email=t@example.invalid", "add", "-A")
    g("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "base")
    g("branch", "base")
    run = lambda: code(CA.main, "--root", repo, "--base", "base")  # noqa: E731
    check("check_assets passes on an untouched store", run() == 0)
    b2 = fake_build(os.path.join(tmp, "ca_build2"), note="ca2")
    store("publish", "--store", sd, "--build", b2, "--version", "1.1.0")
    store("approve", "--store", sd, "--version", "1.1.0", "--by", "test owner")
    check("a new version folder plus approve passes", run() == 0)
    master = os.path.join(sd, "1.0.0", f"{CID}_master.blend")
    orig = open(master, "rb").read()
    os.chmod(master, 0o644)
    open(master, "wb").write(orig[:-1] + bytes([orig[-1] ^ 1]))
    check("a modified published file fails (hash and diff)", run() != 0)
    open(master, "wb").write(orig)
    check("restored file passes again", run() == 0)
    ip = os.path.join(sd, "index.json")
    idx_orig = open(ip).read()
    idx = json.loads(idx_orig)
    idx["pointers"]["approved"] = "9.9.9"
    open(ip, "w").write(json.dumps(idx))
    check("a pointer to a missing version fails", run() != 0)
    idx = json.loads(idx_orig)
    idx["history"] = idx["history"][1:]
    open(ip, "w").write(json.dumps(idx))
    check("rewritten index history fails", run() != 0)
    idx = json.loads(idx_orig)
    idx["versions"]["1.0.0"]["notes"] = "edited"
    open(ip, "w").write(json.dumps(idx))
    check("an edited entry of a published version fails", run() != 0)
    open(ip, "w").write(idx_orig)
    extra = os.path.join(sd, "1.0.0", "extra.txt")
    open(extra, "w").write("x")
    check("a file added to a published version fails", run() != 0)
    os.remove(extra)
    os.makedirs(os.path.join(sd, "2.0.0"))
    check("an unindexed version folder fails", run() != 0)
    os.rmdir(os.path.join(sd, "2.0.0"))
    check("clean again", run() == 0)


def test_generator(blender):
    """build_character.py aimed at a real published version folder: refused, nothing written."""
    for cid, sd in CA.stores(ROOT):
        idx = json.load(open(os.path.join(sd, "index.json")))
        for ver in sorted(idx["versions"]):
            vd = os.path.join(sd, ver)
            before = tree_hashes(vd)
            spec = os.path.join(vd, "spec.json")
            r = subprocess.run([blender, "-b", "--factory-startup", "-P",
                                os.path.join(ROOT, "pipeline", "charsys", "build_character.py"), "--",
                                "--spec", spec, "--out", vd, "--no-glb", "--no-compare"],
                               cwd=ROOT, capture_output=True, text=True)
            check(f"generator into published {cid} {ver} refused, files byte-identical",
                  r.returncode != 0 and tree_hashes(vd) == before, r.returncode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="ps_store_guard_")
    try:
        test_publish_guard(tmp)
        test_input_spec(tmp)
        test_run_shot_guard(tmp)
        test_check_assets(tmp)
        if a.blender:
            test_generator(a.blender)
    finally:
        for base, dirs, files in os.walk(tmp):
            for f in files:
                try:
                    os.chmod(os.path.join(base, f), 0o644)
                except OSError:
                    pass
        shutil.rmtree(tmp, ignore_errors=True)
    ok = all(r["pass"] for r in RESULTS)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump({"pass": ok, "checks": RESULTS}, open(a.out, "w"), indent=1)
    print(f"[test_asset_store_guard] {'PASS' if ok else 'FAIL'} ({sum(r['pass'] for r in RESULTS)}/{len(RESULTS)})")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
