"""Asset-store tests (plain Python; works on a temporary copy, never on the real store).

    python3 pipeline/charsys/tests/test_store.py [--build <charsys build dir>] [--out <result.json>]

Needs a charsys build folder (default renders/charsys/ref_1.0.0, made by build_character.py)."""
import argparse
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import asset_store as AS  # noqa: E402
import spec as S  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RESULTS = []


def store(*args):
    try:
        AS.main(list(args))
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1


def check(name, ok, detail=None):
    RESULTS.append({"check": name, "pass": bool(ok), "detail": detail})
    print(f"[test_store] {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default=os.path.join(ROOT, "renders", "charsys", "ref_1.0.0"))
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="ps_store_test_")
    st = os.path.join(tmp, "versions")
    try:
        check("publish 1.0.0", store("publish", "--store", st, "--build", a.build, "--version", "1.0.0", "--status", "reference",
                                     "--notes", "test") == 0)
        check("verify 1.0.0", store("verify", "--store", st) == 0)
        check("re-publishing an existing version is refused (immutable)",
              store("publish", "--store", st, "--build", a.build, "--version", "1.0.0") != 0)
        check("bad version string refused", store("publish", "--store", st, "--build", a.build, "--version", "v7") != 0)
        # an identity change (proportions) without owner approval is refused; with an approval record it is accepted
        b2 = os.path.join(tmp, "build_identity_change")
        shutil.copytree(a.build, b2)
        sp = json.load(open(os.path.join(b2, "spec.resolved.json")))
        sp["proportions"]["eye_x_m"] = 0.066
        json.dump(sp, open(os.path.join(b2, "spec.resolved.json"), "w"), indent=1)
        rep = json.load(open(os.path.join(b2, "build_report.json")))
        rep["spec_sha256"] = S.sha256(sp)
        json.dump(rep, open(os.path.join(b2, "build_report.json"), "w"), indent=1)
        check("identity change without owner approval refused",
              store("publish", "--store", st, "--build", b2, "--version", "1.1.0") != 0)
        check("identity change with recorded owner approval accepted",
              store("publish", "--store", st, "--build", b2, "--version", "1.1.0",
                    "--identity-change-approved-by", "test owner, test run") == 0)
        man = json.load(open(os.path.join(st, "1.1.0", "manifest.json")))
        check("manifest records parent and identity change", man["parent"] == "1.0.0" and man["identity_changes"] == ["proportions"],
              {"parent": man["parent"], "identity_changes": man["identity_changes"]})
        # spec / report mismatch is refused (a build whose spec was edited afterwards)
        b3 = os.path.join(tmp, "build_tampered")
        shutil.copytree(a.build, b3)
        sp3 = json.load(open(os.path.join(b3, "spec.resolved.json")))
        sp3["metadata"]["notes"] = "edited after build"
        json.dump(sp3, open(os.path.join(b3, "spec.resolved.json"), "w"))
        check("spec edited after build refused", store("publish", "--store", st, "--build", b3, "--version", "1.2.0") != 0)
        # approval
        check("approve without --by refused", store("approve", "--store", st, "--version", "1.0.0") != 0)
        check("approve 1.0.0", store("approve", "--store", st, "--version", "1.0.0", "--by", "test owner") == 0)
        idx = json.load(open(os.path.join(st, "index.json")))
        check("approved pointer set, history kept", idx["pointers"]["approved"] == "1.0.0" and
              [h["action"] for h in idx["history"]] == ["publish", "publish", "approve"], idx["pointers"])
        # restore
        r1 = os.path.join(tmp, "restore_approved")
        check("restore approved", store("restore", "--store", st, "--version", "approved", "--to", r1) == 0)
        same = all(AS.sha256_file(os.path.join(r1, f)) == AS.sha256_file(os.path.join(st, "1.0.0", f))
                   for f in os.listdir(os.path.join(st, "1.0.0")))
        check("restored files identical to the stored version", same)
        check("restore into the store refused",
              store("restore", "--store", st, "--version", "1.0.0", "--to", os.path.join(st, "x")) != 0)
        check("restore into a non-empty folder refused", store("restore", "--store", st, "--version", "1.0.0", "--to", r1) != 0)
        # tampering is detected; restore and approve refuse a tampered version
        mf = os.path.join(st, "1.1.0", "boy_yellow_hoodie_master.blend")
        os.chmod(mf, 0o644)
        with open(mf, "ab") as f:
            f.write(b"x")
        check("tampered master detected by verify", store("verify", "--store", st, "--version", "1.1.0") != 0)
        check("tampered version cannot be approved", store("approve", "--store", st, "--version", "1.1.0", "--by", "x") != 0)
        check("tampered version cannot be restored",
              store("restore", "--store", st, "--version", "1.1.0", "--to", os.path.join(tmp, "r2")) != 0)
        check("untouched version still verifies", store("verify", "--store", st, "--version", "1.0.0") == 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    ok = all(r["pass"] for r in RESULTS)
    print(f"[test_store] {'ALL PASS' if ok else 'FAILURES'} ({sum(r['pass'] for r in RESULTS)}/{len(RESULTS)})")
    if a.out:
        json.dump({"pass": ok, "checks": RESULTS}, open(a.out, "w"), indent=1)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
