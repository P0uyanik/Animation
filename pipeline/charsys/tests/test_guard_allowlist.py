"""Owner-approved candidate allowlist for the guard checks in test_hair_r5 / test_hands_r2 (T-154). No Blender.

    python3 pipeline/charsys/tests/test_guard_allowlist.py

The guards ("no file under assets/characters pins groom/4", "no spec sets body.hands") stay as they were; a file is
exempt only when its (character, version) is read from its path and that exact (character, version, feature) is listed
in owner_approved_candidates.json with an owner decision and a date. A malformed allowlist, an entry for a current
(approved) version, or a file whose version cannot be read is never exempt. The checks below prove it."""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ALLOWLIST = os.path.join(HERE, "owner_approved_candidates.json")
FEATURES = ("groom/4", "body.hands")
FIELDS = ("character", "version", "feature", "owner_decision", "date")
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def current_version(character, root=ROOT):
    p = os.path.join(root, "assets", "characters", character, "versions", "index.json")
    if not os.path.exists(p):
        return None
    return (json.load(open(p)).get("pointers") or {}).get("approved")


def errors(data, root=ROOT):
    """Problems of an allowlist document; any problem makes the whole list unusable."""
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        return ["allowlist: no entries list"]
    errs = []
    for k, e in enumerate(data["entries"]):
        if not isinstance(e, dict):
            errs.append(f"entry {k}: not an object")
            continue
        miss = [f for f in FIELDS if not isinstance(e.get(f), str) or not e[f].strip()]
        if miss:
            errs.append(f"entry {k}: missing {miss}")
            continue
        if e["feature"] not in FEATURES:
            errs.append(f"entry {k}: unknown feature {e['feature']}")
        if not VERSION.match(e["version"]):
            errs.append(f"entry {k}: bad version {e['version']}")
        if not DATE.match(e["date"]):
            errs.append(f"entry {k}: bad date {e['date']}")
        if not os.path.isdir(os.path.join(root, "assets", "characters", e["character"])):
            errs.append(f"entry {k}: unknown character {e['character']}")
        elif e["version"] == current_version(e["character"], root):
            errs.append(f"entry {k}: {e['character']} {e['version']} is the current version (never exemptable)")
    return errs


def load(path=ALLOWLIST, root=ROOT):
    """(entries, errors). With errors the entries are empty: nothing is exempt."""
    if not os.path.exists(path):
        return [], ["allowlist missing"]
    try:
        data = json.load(open(path))
    except ValueError as ex:
        return [], [f"allowlist: {ex}"]
    errs = errors(data, root)
    return ([] if errs else data["entries"]), errs


def candidate_of(relpath):
    """(character, version) of a file under assets/characters, or None when the version cannot be read."""
    parts = relpath.replace(os.sep, "/").split("/")
    if len(parts) < 4 or parts[:2] != ["assets", "characters"]:
        return None
    cid = parts[2]
    if parts[3] == "versions" and len(parts) >= 6 and VERSION.match(parts[4]):
        return cid, parts[4]
    m = re.match(re.escape(cid) + r"\.(\d+\.\d+\.\d+)\.spec\.json$", parts[-1])
    return (cid, m.group(1)) if m else None


def exempt(relpath, feature, entries, root=ROOT):
    c = candidate_of(relpath)
    if c is None or c[1] == current_version(c[0], root):
        return False
    return any((e["character"], e["version"], e["feature"]) == (c[0], c[1], feature) for e in entries)


def split(relpaths, feature, path=ALLOWLIST, root=ROOT):
    """(not exempt, exempt, allowlist errors). An allowlist error leaves every path not exempt."""
    entries, errs = load(path, root)
    keep = [p for p in relpaths if not exempt(p, feature, entries, root)]
    return keep, [p for p in relpaths if p not in keep], errs


RESULTS = []


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_guard_allowlist] {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}")


def main():
    import tempfile
    entries, errs = load()
    check("the allowlist validates", not errs, errs[:3])
    check("every entry names an owner decision and a date", entries and all(e["owner_decision"] and e["date"]
                                                                            for e in entries))
    data = json.load(open(ALLOWLIST))
    E = data["entries"][0]
    cid, ver, feat = E["character"], E["version"], E["feature"]
    other = next(f for f in FEATURES if f != feat)
    spec = f"assets/characters/{cid}/spec/{cid}.{ver}.spec.json"
    stored = f"assets/characters/{cid}/versions/{ver}/spec.json"
    check("path -> candidate: spec file and stored version",
          candidate_of(spec) == (cid, ver) and candidate_of(stored) == (cid, ver))
    check("path without a readable version is never exempt",
          candidate_of(f"assets/characters/{cid}/spec/{cid}.spec.json") is None
          and not exempt(f"assets/characters/{cid}/spec/{cid}.spec.json", feat, entries))
    check("a listed candidate is exempt for its feature", exempt(spec, feat, entries) and exempt(stored, feat, entries))
    only = [e for e in entries if not (e["character"] == cid and e["version"] == ver and e["feature"] == other)]
    check("a listed id with a different feature is rejected", not exempt(spec, other, only))
    check("an unlisted candidate is still rejected",
          not exempt(f"assets/characters/{cid}/spec/{cid}.99.0.0.spec.json", feat, entries)
          and not exempt(f"assets/characters/{cid}/versions/99.0.0/spec.json", feat, entries))
    check("an unlisted character is still rejected",
          not exempt(f"assets/characters/nobody/spec/nobody.{ver}.spec.json", feat, entries))
    keep, ex, errs = split([spec, f"assets/characters/{cid}/versions/99.0.0/spec.json"], feat)
    check("split keeps the unlisted path in the failure list", keep == [f"assets/characters/{cid}/versions/99.0.0/spec.json"]
          and ex == [spec] and not errs)

    def with_doc(doc):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(doc, f)
        try:
            return split([spec], feat, path=f.name)
        finally:
            os.unlink(f.name)
    for drop in ("owner_decision", "date"):
        bad = {"entries": [{k: v for k, v in E.items() if k != drop}]}
        keep, ex, errs = with_doc(bad)
        check(f"malformed entry (missing {drop}) fails and exempts nothing", errs and keep == [spec] and not ex, errs)
    keep, ex, errs = with_doc({"entries": [dict(E, date="today")]})
    check("malformed entry (bad date) fails", errs and keep == [spec])
    keep, ex, errs = with_doc({"entries": [dict(E, feature="groom/*")]})
    check("an unknown or wildcard feature fails", errs and keep == [spec])
    keep, ex, errs = with_doc({"entries": [dict(E, version="*")]})
    check("a wildcard version fails", errs and keep == [spec])
    keep, ex, errs = with_doc({"entries": "all"})
    check("an allowlist without an entries list fails", errs and keep == [spec])
    for c in sorted(os.listdir(os.path.join(ROOT, "assets", "characters"))):
        cur = current_version(c)
        if cur is None:
            continue
        keep, ex, errs = with_doc({"entries": [dict(E, character=c, version=cur, feature=f) for f in FEATURES]})
        check(f"{c}: the current version {cur} is never exemptable (entry refused)",
              errs and any("current version" in x for x in errs))
        cspec = f"assets/characters/{c}/spec/{c}.{cur}.spec.json"
        forged = [dict(E, character=c, version=cur, feature=f) for f in FEATURES]
        check(f"{c}: a current-version file is not exempt even if listed",
              not any(exempt(cspec, f, forged) for f in FEATURES))
        check(f"{c}: no allowlist entry names the current version",
              not any(e["character"] == c and e["version"] == cur for e in entries))
    print(f"[test_guard_allowlist] {sum(RESULTS)}/{len(RESULTS)} passed")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
