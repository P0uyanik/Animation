"""T-178: the one release rule for opt-in features (pipeline/charsys/release_rule.py). No Blender.

    python3 pipeline/charsys/tests/test_release_rule.py

Proves: the repository passes the rule as it is today (every published version that uses an opt-in feature is
listed, with exactly the features it uses and a decision ref naming a decision file that mentions it); every detector
catches what the old per-feature guard caught, in the old guard's scope; negatives (an unlisted version, a base /
unversioned file, a listed version using a feature it is not listed for, a listed version without a decision ref, a
malformed manifest) fail; the manifest and the rule are guarded paths, and a change to the manifest without a
Supervisor-Approved trailer fails tools/check_all.py's guarded-paths check; version_switch's entry writer lists the
version's features and keeps the other entries."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
sys.path.insert(0, CHARSYS)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import release_rule as R  # noqa: E402

RESULTS = []
OLD_ALLOWLIST = "pipeline/charsys/tests/owner_approved_candidates.json"  # T-154, replaced by the manifest
OLD_COMMIT = "b531ab5"  # T-178 input commit, the last one with the old allowlist


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_release_rule] {'PASS' if ok else 'FAIL'} {name}{'' if ok or detail is None else ' ' + str(detail)[:300]}")


# one document per feature that the old guard's detector caught
SAMPLES = {
    "groom/2": [{"generators": {"groom": "groom/2"}}, {"hair": {"generator": "groom/2"}}],
    "groom/3": [{"generators": {"groom": "groom/3"}}],
    "groom/4": [{"generators": {"groom": "groom/4"}}, {"override": {"generators": {"groom": "groom/4"}}}],
    "groom/5": [{"generators": {"groom": "groom/5"}}, {"override": {"hair": {"generator": "groom/5"}}}],
    "face_generic/3": [{"generators": {"face": "face_generic/3"}}, {"face": {"generator": "face_generic/3"}}],
    "body.hands": [{"body": {"hands": {}}}, {"override": {"body": {"hands": {"mitten": 1}}}}],
    "lash_curve": [{"face": {"closed_fit": {"lash_curve": True}}}],
    "closed_fill": [{"face": {"lids": {"upper_yaw_deg": 2}}}, {"face": {"lids": {"lower_yaw_deg": 2}}},
                    {"face": {"closed_fit": {"sink_m": 0.001}}}, {"face": {"closed_fit": {"shell_occlusion_tint": 1}}},
                    {"face": {"socket": {"closed_fill": {}}}}],
    "t168_face": [{"face": {"lower_face": {"cheek_pad_top_fade_m": 0.01}}}, {"face": {"nose": {"type": "upturned"}}}],
    "hair_contact": [{"hair": {"ear_keepout": {}}}, {"override": {"hair": {"dynamics": {"contact": {}}}}},
                     {"dynamics": {"chains": [{"name": "lock", "contact": {"segments": True}}]}}],
}
PLAIN = {"generators": {"groom": "groom/1", "face": "face_generic/2"}, "body": {}, "face": {"nose": {"type": "button"}}}


class FakeRepo:
    """A scratch root with two characters, published versions and a decision file."""
    CID, OTHER = "char_a", "char_b"

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="t178_")
        self.decisions = "docs/process/DECISIONS.md"
        self.write(self.decisions, "## 2026-01-01\n- char_a 1.0.0 and 1.1.0 current; char_b 0.1.0 current\n")
        for cid, vers in ((self.CID, ("1.0.0", "1.1.0", "1.2.0")), (self.OTHER, ("0.1.0",))):
            self.write(f"assets/characters/{cid}/versions/index.json",
                       json.dumps({"versions": {v: {"status": "approved"} for v in vers},
                                   "pointers": {"approved": vers[-1]}}))

    def write(self, rel, text):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text if isinstance(text, str) else json.dumps(text))
        return rel

    def entry(self, cid, ver, feats, **kw):
        e = {"character": cid, "version": ver, "features": list(feats),
             "decision_ref": f"{self.decisions} 2026-01-01", "date": "2026-01-01"}
        e.update(kw)
        return e

    def manifest(self, entries):
        self.write(R.MANIFEST, {"schema": R.SCHEMA, "releases": entries})

    def violations(self):
        return R.violations(self.root)

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


def test_repository():
    listed, errs = R.load()
    check("the release manifest validates", not errs, errs[:3])
    out, errs = R.violations()
    check("the repository passes the release rule as it is today (no behaviour change)", not out and not errs,
          out[:3] or errs[:3])
    used = R.used_by_version()
    check("every version whose files use an opt-in feature is listed", set(used) <= set(listed),
          sorted(set(used) - set(listed)))
    check("each entry lists exactly the features the version's files use (no blanket or stale listing)",
          all(listed[k] == used.get(k, set()) for k in listed),
          [k for k in listed if listed[k] != used.get(k, set())])
    data = json.load(open(os.path.join(ROOT, R.MANIFEST)))
    check("every entry names a decision ref whose file mentions the version",
          all(R.decision_problem(e["decision_ref"], e["version"]) is None for e in data["releases"]))
    chars = os.path.join(ROOT, "assets", "characters")
    for cid in sorted(os.listdir(chars)):
        idx = os.path.join(chars, cid, "versions", "index.json")
        if not os.path.isfile(idx):
            continue
        cur = (json.load(open(idx)).get("pointers") or {}).get("approved")
        if (cid, cur) in used:
            check(f"current {cid} {cur} is listed with its features", listed.get((cid, cur)) == used[(cid, cur)])
    # the T-154 allowlist this manifest replaced (removed by T-178): read from the input commit when history is there
    got = subprocess.run(["git", "show", f"{OLD_COMMIT}:{OLD_ALLOWLIST}"], cwd=ROOT, capture_output=True, text=True)
    if got.returncode != 0:
        print(f"[test_release_rule] SKIP old allowlist migration check ({OLD_COMMIT} not in this clone)")
    else:
        old = json.loads(got.stdout)["entries"]
        miss = [(e["character"], e["version"], e["feature"]) for e in old
                if e["feature"] not in listed.get((e["character"], e["version"]), set())]
        check(f"every owner_approved_candidates.json entry ({len(old)}) is listed in the manifest", not miss, miss)


def test_detectors_and_scopes():
    rp = FakeRepo()
    try:
        cid = rp.CID
        for feat, docs in SAMPLES.items():
            for k, doc in enumerate(docs):
                txt = json.dumps(doc)
                base = f"assets/characters/{cid}/spec/{cid}.spec.json"
                ver = f"assets/characters/{cid}/spec/{cid}.9.9.9.spec.json"
                stored = f"assets/characters/{cid}/versions/9.9.9/spec.json"
                check(f"{feat} #{k}: detected in a versioned spec and a stored version",
                      feat in R.features_of(ver, txt) and feat in R.features_of(stored, txt))
                check(f"{feat} #{k}: detected in the base spec", feat in R.features_of(base, txt))
                check(f"{feat} #{k}: not detected in a plain spec", feat not in R.features_of(ver, json.dumps(PLAIN)))
        # scopes = the old guards' scopes
        cand = f"assets/characters/{cid}/spec/candidates/T-1/{cid}.over.json"
        other = f"assets/characters/{cid}/experiments/x.json"
        g3 = json.dumps(SAMPLES["groom/3"][0])
        check("groom/3, groom/2, face_generic/3: candidate subfolders are outside the scope (as test_hair_r4 / v3_r2 / "
              "face_v3)", R.features_of(cand, g3) == [] and R.features_of(cand, json.dumps(SAMPLES["groom/2"][0])) == []
              and "face_generic/3" not in R.features_of(cand, json.dumps(SAMPLES["face_generic/3"][0])))
        check("groom/4, groom/5, body.hands: every file under assets/characters (as test_hair_r5 / r6 / hands_r2)",
              all(f in R.features_of(p, json.dumps(SAMPLES[f][0])) for f in ("groom/4", "groom/5", "body.hands")
                  for p in (cand, other)))
        check("lash_curve, closed_fill: spec folders (as test_face_r5) and stored versions (added)",
              all(f in R.features_of(cand, json.dumps(SAMPLES[f][0])) and not R.features_of(other, json.dumps(
                  SAMPLES[f][0])) for f in ("lash_curve", "closed_fill")))
        t = json.dumps(SAMPLES["t168_face"][0])
        check("t168_face: every file under assets/ except references (as test_face_t168)",
              "t168_face" in R.features_of("assets/props/x.json", t) and "t168_face" in R.features_of(other, t)
              and not R.features_of(f"assets/characters/{cid}/references/x.json", t))
        check("path -> version: versioned spec and stored version read; base spec, -dev and overrides do not",
              R.candidate_of(f"assets/characters/{cid}/spec/{cid}.1.2.3.spec.json") == (cid, "1.2.3")
              and R.candidate_of(f"assets/characters/{cid}/versions/1.2.3/build_report.json") == (cid, "1.2.3")
              and R.candidate_of(f"assets/characters/{cid}/spec/{cid}.spec.json") is None
              and R.candidate_of(f"assets/characters/{cid}/spec/{cid}.1.2.3-dev.spec.json") is None
              and R.candidate_of(f"assets/characters/{cid}/spec/{cid}.1.2.3.override.json") is None)
        check("every registered feature has a sample here", set(SAMPLES) == set(R.FEATURES), set(R.FEATURES) ^ set(SAMPLES))
    finally:
        rp.close()


def test_negatives():
    rp = FakeRepo()
    try:
        cid, oth = rp.CID, rp.OTHER
        rp.manifest([rp.entry(cid, "1.1.0", ["groom/5"]), rp.entry(oth, "0.1.0", ["body.hands"])])
        out, errs = rp.violations()
        check("scratch repo: empty assets pass", not out and not errs, out or errs)
        ok = rp.write(f"assets/characters/{cid}/versions/1.1.0/spec.json", SAMPLES["groom/5"][0])
        rp.write(f"assets/characters/{oth}/spec/{oth}.0.1.0.spec.json", SAMPLES["body.hands"][1])
        out, errs = rp.violations()
        check("listed versions using their listed features pass", not out and not errs, out or errs)
        for feat, docs in SAMPLES.items():
            # an unlisted version using the opt-in fails (like the 9.9.9-test case of test_versions.py)
            p = rp.write(f"assets/characters/{cid}/spec/{cid}.9.9.9.spec.json", docs[0])
            out, _ = rp.violations()
            check(f"{feat}: an unlisted version using it fails", any(r == p and f == feat for r, f, _ in out), out)
            os.remove(os.path.join(rp.root, p))
            p = rp.write(f"assets/characters/{cid}/spec/{cid}.spec.json", docs[0])
            out, _ = rp.violations()
            check(f"{feat}: the base spec using it fails (no version, never exempt)",
                  any(r == p and f == feat for r, f, _ in out), out)
            os.remove(os.path.join(rp.root, p))
            if feat != "groom/5":
                p = rp.write(f"assets/characters/{cid}/versions/1.1.0/extra.json", docs[0])
                out, _ = rp.violations()
                check(f"{feat}: a listed version using it while not listed for it fails",
                      any(r == p and f == feat and "not listed for" in why for r, f, why in out), out)
                os.remove(os.path.join(rp.root, p))
        p = rp.write("assets/characters/char_c/spec/char_c.1.1.0.spec.json", SAMPLES["groom/5"][0])
        out, _ = rp.violations()
        check("an unlisted character's versioned spec using an opt-in fails", any(r == p for r, _, _ in out), out)
        os.remove(os.path.join(rp.root, p))
        p = rp.write(f"assets/characters/{oth}/versions/0.1.0/spec.json", SAMPLES["groom/5"][0])
        out, _ = rp.violations()
        check("a feature listed for another character's version does not cover this one",
              any(r == p for r, _, _ in out), out)
        os.remove(os.path.join(rp.root, p))
        # a listed version without a decision ref fails, and then nothing is listed: every user fails
        for bad, why in ((dict(decision_ref=""), "missing"), (dict(decision_ref=None), "missing"),
                         (dict(decision_ref=f"{rp.decisions}"), "names no date"),
                         (dict(decision_ref="docs/process/NOPE.md 2026-01-01"), "not found"),
                         (dict(version="1.2.0"), "does not mention"),
                         (dict(date="today"), "bad date"), (dict(features=["groom/*"]), "unknown feature"),
                         (dict(features=[]), "missing"), (dict(version="*"), "bad version"),
                         (dict(character="nobody"), "unknown character"), (dict(version="3.0.0"), "not a published")):
            e = rp.entry(cid, "1.1.0", ["groom/5"])
            e.update(bad)
            rp.manifest([e, rp.entry(oth, "0.1.0", ["body.hands"])])
            out, errs = rp.violations()
            check(f"manifest entry {sorted(bad)} -> refused ({why}) and nothing is exempt",
                  any(why in x for x in errs) and {r for r, _, _ in out} >= {ok}, errs)
        e = rp.entry(cid, "1.1.0", ["groom/5"])
        for doc, why in (({"schema": R.SCHEMA, "releases": [e, e]}, "listed twice"),
                         ({"schema": R.SCHEMA, "releases": "all"}, "releases list"),
                         ({"releases": [e]}, "schema")):
            rp.write(R.MANIFEST, doc)
            out, errs = rp.violations()
            check(f"malformed manifest ({why}) refused, nothing exempt", any(why in x for x in errs)
                  and any(r == ok for r, _, _ in out), errs)
        os.remove(os.path.join(rp.root, R.MANIFEST))
        out, errs = rp.violations()
        check("a missing manifest exempts nothing", errs and any(r == ok for r, _, _ in out), errs)
        rp.write(R.MANIFEST, "{not json")
        out, errs = rp.violations()
        check("an unreadable manifest exempts nothing", errs and any(r == ok for r, _, _ in out), errs)
    finally:
        rp.close()


def test_writer():
    rp = FakeRepo()
    try:
        cid, oth = rp.CID, rp.OTHER
        keep = rp.entry(oth, "0.1.0", ["body.hands"])
        rp.manifest([keep, rp.entry(cid, "1.1.0", ["groom/5"], decision_ref=f"{rp.decisions} old")])
        rp.write(f"assets/characters/{oth}/versions/0.1.0/spec.json", SAMPLES["body.hands"][0])
        rp.write(f"assets/characters/{cid}/versions/1.1.0/spec.json", dict(SAMPLES["groom/5"][0],
                                                                         face=SAMPLES["lash_curve"][0]["face"]))
        e = R.release_entry(cid, "1.1.0", f"{rp.decisions} 2026-01-01", "2026-01-01", "T-1", "make it current",
                            root=rp.root)
        check("release_entry lists the features the version's files use",
              e is not None and e["features"] == ["groom/5", "lash_curve"], e)
        R.write_entry(e, root=rp.root)
        data = json.load(open(os.path.join(rp.root, R.MANIFEST)))
        mine = [x for x in data["releases"] if x["character"] == cid]
        check("write_entry replaces the version's entry and keeps the others",
              len(mine) == 1 and mine[0] == e and keep in data["releases"], data["releases"])
        out, errs = rp.violations()
        check("after the write the scratch repo passes", not out and not errs, out or errs)
        check("a version that uses no opt-in feature gets no entry",
              R.release_entry(cid, "1.0.0", f"{rp.decisions} 2026-01-01", "2026-01-01", "T-1", root=rp.root) is None)
    finally:
        rp.close()


def test_guarded():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import check_all as CA
    pats = CA.guarded_patterns()
    for p in (R.MANIFEST, "pipeline/charsys/release_rule.py"):
        check(f"{p} is a guarded path", any(CA.matches(p, x) for x in pats))
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if not head:
        check("git HEAD available for the guarded-paths check", False)
        return
    res = CA.check_guarded(head, {R.MANIFEST})
    check("a manifest change without a Supervisor-Approved trailer fails the guarded-paths check",
          not res.ok and R.MANIFEST in res.detail, res.detail)


def test_version_switch():
    """tools/version_switch.py writes the entry in the switch run (fixture of tools/tests/test_version_switch.py)."""
    sys.path.insert(0, os.path.join(ROOT, "tools", "tests"))
    from pathlib import Path
    import test_version_switch as TVS
    A, TASK = TVS.A, TVS.TASK
    ID = {"--identity-change-approved-by": "owner (fixture)"}  # the face section changes vs the fixture's 1.0.0
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        root = TVS.fixture(tmp)
        spec = TVS.make_spec(A, "1.1.0", face={"eyes": "brown", "nose": {"type": "upturned"}})
        TVS.set_spec(root, spec)
        claim = (root / f"docs/tasks/{TASK}.md").read_text()
        TVS.write(root / f"docs/tasks/{TASK}.md", claim.rstrip("\n") + f", `{R.MANIFEST}`\n")
        code, out = TVS.run_main(TVS.argv(root, tmp / "dry", **{"--dry-run": [], **ID}))
        check("switch dry run predicts the manifest write and its trailer", code == 0 and R.MANIFEST in out
              and f"Supervisor-Approved: {R.MANIFEST}" in out, out[-600:])
        runner = TVS.FakeRunner()
        runner.root = root
        code, out = TVS.run_main(TVS.argv(root, tmp / "work", **ID), runner)
        data = json.load(open(root / R.MANIFEST)) if (root / R.MANIFEST).is_file() else {}
        e = [x for x in data.get("releases", []) if (x["character"], x["version"]) == (A, "1.1.0")]
        check("switch writes the version's entry (features, decision ref, decision, task) in the same run",
              code == 0 and len(e) == 1 and e[0]["features"] == ["t168_face"]
              and e[0]["decision_ref"] == TVS.DECISION_REF and e[0]["task"] == TASK and e[0]["decision"], out[-600:])
        check("switch prints the manifest's Supervisor-Approved trailer", f"Supervisor-Approved: {R.MANIFEST}" in out)
        out2, errs = R.violations(str(root))
        check("after the switch the fixture passes the release rule", not out2 and not errs, out2 or errs)
        # the claim must cover the manifest: refused before anything is written
        root2 = TVS.fixture(tmp / "narrow")
        TVS.set_spec(root2, spec)
        code, out = TVS.run_main(TVS.argv(root2, tmp / "narrow" / "work", **ID), TVS.FakeRunner())
        check("a switch whose claim does not cover the manifest is refused before anything is written",
              code == 1 and f"does not cover: {R.MANIFEST}" in out and not (root2 / R.MANIFEST).exists(), out[-400:])


def main():
    test_repository()
    test_detectors_and_scopes()
    test_negatives()
    test_writer()
    test_version_switch()
    test_guarded()
    print(f"[test_release_rule] {sum(RESULTS)}/{len(RESULTS)} passed")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
