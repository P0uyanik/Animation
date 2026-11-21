"""One release rule for opt-in features (T-178, owner 2026-11-21 ~04:10Z, T-176 proposal 5). No Blender.

A file under assets/ that uses an opt-in feature (FEATURES below) is allowed only when its (character, version) is read
from its path and that version is listed in pipeline/charsys/release_manifest.json for that feature, with an owner
decision ref. tools/version_switch.py writes the entry in the same run that publishes / makes the version current.

The detectors and the scope each one scans are the ones the old per-feature guards used (test_hair_r4/r5/r6,
test_hair_v3_r2/r3, test_hands_r2, test_face_r5, test_face_v3/v3b, test_face_t168); the coverage table is in
docs/evaluation/process/T-178/README.md. A new opt-in feature registers one detector here; it adds no guard test.

Never exempt: a file whose version cannot be read from its path (base specs, unversioned overrides), an unlisted
version, a listed version for a feature it is not listed for, and every file when the manifest has any problem.

    python3 pipeline/charsys/release_rule.py          # prints the violations; exit 1 if any
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MANIFEST = "pipeline/charsys/release_manifest.json"
SCHEMA = "plush-studio.release-manifest/1"
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ENTRY_FIELDS = ("character", "version", "features", "decision_ref", "date")


# ----------------------------------------------------------------------------------------------- detectors

def _walk(d, fn):
    if isinstance(d, dict):
        return any(fn(k, v) or _walk(v, fn) for k, v in d.items())
    if isinstance(d, list):
        return any(_walk(v, fn) for v in d)
    return False


def _has_key(d, *keys):
    return _walk(d, lambda k, v: k in keys)


def _groom_pin(d):  # test_hair_r5: generators.groom, else override.generators.groom
    if not isinstance(d, dict):
        return None
    g = (d.get("generators") or {}).get("groom")
    return g or ((d.get("override") or {}).get("generators") or {}).get("groom")


def _groom2(d, _t):  # test_hair_v3_r2/r3
    return isinstance(d, dict) and ((d.get("generators") or {}).get("groom") == "groom/2"
                                    or (isinstance(d.get("hair"), dict) and d["hair"].get("generator") == "groom/2"))


def _hands(d, _t):  # test_hands_r2
    d = d.get("override", d) if isinstance(d, dict) else {}
    return isinstance(d, dict) and isinstance(d.get("body"), dict) and "hands" in d["body"]


def _t168(d, _t):  # test_face_t168
    return _walk(d, lambda k, v: k == "cheek_pad_top_fade_m"
                 or (k == "nose" and isinstance(v, dict) and v.get("type") == "upturned"))


def _garment_field(d, field):  # T-184: a clothing item that switches a garment/3 item field on
    return _walk(d, lambda k, v: k == "garments" and isinstance(v, list)
                 and any(isinstance(g, dict) and g.get(field) not in (None, False) for g in v))


# Scopes (repository-relative paths of .json files), as the old guards scanned them:
#   characters  every file under assets/characters/ (test_hair_r5, test_hair_r6, test_hands_r2)
#   spec_dirs   files under assets/characters/ whose folder path contains "/spec" (test_face_r5), plus the stored
#               published versions (assets/characters/<id>/versions/<v>/), which test_face_r5 did not scan
#   assets      every file under assets/ outside folders whose path contains "references" (test_face_t168)
#   spec_top    files directly in assets/characters/<id>/spec/ and in assets/characters/<id>/versions/<v>/: the base
#               spec, unversioned overrides and published specs (test_hair_r4, test_hair_v3_r2/r3, test_face_v3/v3b;
#               the old guards checked the base/unversioned files there, and the release rule adds the versioned ones)
FEATURES = {
    "groom/2": {"scope": "spec_top", "detect": _groom2, "old": "test_hair_v3_r2/r3"},
    "groom/3": {"scope": "spec_top", "detect": lambda d, t: "groom/3" in t, "old": "test_hair_r4"},
    "groom/4": {"scope": "characters", "detect": lambda d, t: _groom_pin(d) == "groom/4", "old": "test_hair_r5"},
    "groom/5": {"scope": "characters", "detect": lambda d, t: '"groom/5"' in t, "old": "test_hair_r6"},
    "face_generic/3": {"scope": "spec_top", "detect": lambda d, t: '"face_generic/3"' in t,
                       "old": "test_face_v3/v3b"},
    "body.hands": {"scope": "characters", "detect": _hands, "old": "test_hands_r2"},
    "lash_curve": {"scope": "spec_dirs", "detect": lambda d, t: _has_key(d, "lash_curve"), "old": "test_face_r5"},
    "closed_fill": {"scope": "spec_dirs", "old": "test_face_r5 (T-156)",
                    "detect": lambda d, t: _has_key(d, "upper_yaw_deg", "lower_yaw_deg", "sink_m",
                                                    "shell_occlusion_tint", "closed_fill")},
    "t168_face": {"scope": "assets", "detect": _t168, "old": "test_face_t168"},
    "seated": {"scope": "characters", "detect": lambda d, t: _garment_field(d, "seated"), "old": "T-184 (new)"},
}


def in_scope(relpath, scope):
    parts = relpath.split("/")
    folder = "/" + "/".join(parts[:-1]) + "/"
    if not relpath.endswith(".json") or parts[0] != "assets":
        return False
    chars = len(parts) >= 4 and parts[1] == "characters"
    if scope == "characters":
        return chars
    if scope == "spec_dirs":
        return chars and ("/spec" in folder or (len(parts) == 6 and parts[3] == "versions"
                                                 and bool(VERSION.match(parts[4]))))
    if scope == "assets":
        return "references" not in folder
    if scope == "spec_top":
        return chars and ((len(parts) == 5 and parts[3] == "spec")
                          or (len(parts) == 6 and parts[3] == "versions" and bool(VERSION.match(parts[4]))))
    raise ValueError(f"unknown scope {scope}")


def candidate_of(relpath):
    """(character, version) of a file under assets/characters, or None when the version cannot be read
    (the same reading as the old test_guard_allowlist.candidate_of)."""
    parts = relpath.replace(os.sep, "/").split("/")
    if len(parts) < 4 or parts[:2] != ["assets", "characters"]:
        return None
    cid = parts[2]
    if parts[3] == "versions" and len(parts) >= 6 and VERSION.match(parts[4]):
        return cid, parts[4]
    m = re.match(re.escape(cid) + r"\.(\d+\.\d+\.\d+)\.spec\.json$", parts[-1])
    return (cid, m.group(1)) if m else None


def features_of(relpath, text):
    """Opt-in features a file uses (only the features whose scope covers the path)."""
    try:
        doc = json.loads(text)
    except ValueError:
        doc = None
    out = []
    for name, f in FEATURES.items():
        if not in_scope(relpath, f["scope"]):
            continue
        if f["detect"](doc, text) if doc is not None else (f["detect"]({}, text)):
            out.append(name)
    return out


def scan(root=ROOT):
    """{relpath: [features]} for every file under assets/ that uses an opt-in feature."""
    hits = {}
    base = os.path.join(root, "assets")
    for d, _, files in os.walk(base):
        for f in sorted(files):
            if not f.endswith(".json"):
                continue
            p = os.path.join(d, f)
            r = os.path.relpath(p, root).replace(os.sep, "/")
            try:
                text = open(p, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            used = features_of(r, text)
            if used:
                hits[r] = used
    return hits


def used_by_version(root=ROOT, hits=None):
    """{(character, version): set(features)} from scan()."""
    out = {}
    for r, used in (scan(root) if hits is None else hits).items():
        c = candidate_of(r)
        if c is not None:
            out.setdefault(c, set()).update(used)
    return out


# ----------------------------------------------------------------------------------------------- manifest

def published(character, version, root=ROOT):
    p = os.path.join(root, "assets", "characters", character, "versions", "index.json")
    if not os.path.isfile(p):
        return False
    return version in (json.load(open(p)).get("versions") or {})


def decision_problem(ref, version, root=ROOT):
    """A decision ref is "<file> <date/time ...>": the file exists in the repository and mentions the version."""
    if not isinstance(ref, str) or not ref.strip():
        return "no decision_ref"
    f = ref.split()[0]
    if len(ref.split()) < 2:
        return f"decision_ref {ref!r} names no date"
    p = os.path.join(root, f)
    if not os.path.isfile(p):
        return f"decision file {f} not found"
    if version not in open(p, encoding="utf-8").read():
        return f"{f} does not mention {version}"
    return None


def errors(data, root=ROOT):
    """Problems of a manifest document; any problem makes the whole manifest unusable."""
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or not isinstance(data.get("releases"), list):
        return [f"manifest: schema {SCHEMA} with a releases list required"]
    errs, seen = [], set()
    for k, e in enumerate(data["releases"]):
        if not isinstance(e, dict):
            errs.append(f"entry {k}: not an object")
            continue
        miss = [f for f in ENTRY_FIELDS if f not in e or e[f] in (None, "", [])]
        if miss:
            errs.append(f"entry {k}: missing {miss}")
            continue
        cid, ver, feats = e["character"], e["version"], e["features"]
        if not isinstance(ver, str) or not VERSION.match(ver):
            errs.append(f"entry {k}: bad version {ver!r}")
            continue
        if not isinstance(cid, str) or not os.path.isdir(os.path.join(root, "assets", "characters", cid)):
            errs.append(f"entry {k}: unknown character {cid!r}")
            continue
        if not published(cid, ver, root):
            errs.append(f"entry {k}: {cid} {ver} is not a published version")
        if (cid, ver) in seen:
            errs.append(f"entry {k}: {cid} {ver} listed twice")
        seen.add((cid, ver))
        if not isinstance(feats, list) or not all(isinstance(f, str) for f in feats):
            errs.append(f"entry {k}: features must be a list of names")
        else:
            bad = [f for f in feats if f not in FEATURES]
            if bad:
                errs.append(f"entry {k}: unknown feature(s) {bad}")
            if len(set(feats)) != len(feats):
                errs.append(f"entry {k}: duplicate features")
        if not isinstance(e["date"], str) or not DATE.match(e["date"]):
            errs.append(f"entry {k}: bad date {e['date']!r}")
        prob = decision_problem(e["decision_ref"], ver, root)
        if prob:
            errs.append(f"entry {k}: {cid} {ver}: {prob}")
    return errs


def load(path=None, root=ROOT):
    """(listed {(character, version): set(features)}, errors). With errors nothing is listed."""
    path = path or os.path.join(root, MANIFEST)
    if not os.path.isfile(path):
        return {}, [f"{MANIFEST} missing"]
    try:
        data = json.load(open(path, encoding="utf-8"))
    except ValueError as ex:
        return {}, [f"manifest: {ex}"]
    errs = errors(data, root)
    if errs:
        return {}, errs
    return {(e["character"], e["version"]): set(e["features"]) for e in data["releases"]}, []


def violations(root=ROOT, manifest=None, hits=None):
    """(violations [(relpath, feature, reason)], manifest errors). The release rule holds when both are empty."""
    listed, errs = load(manifest, root)
    hits = scan(root) if hits is None else hits
    out = []
    for r in sorted(hits):
        c = candidate_of(r)
        for f in hits[r]:
            if c is None:
                out.append((r, f, "version cannot be read from the path (base spec or unversioned file)"))
            elif c not in listed:
                out.append((r, f, f"{c[0]} {c[1]} is not listed in {MANIFEST}"))
            elif f not in listed[c]:
                out.append((r, f, f"{c[0]} {c[1]} is not listed for {f}"))
    return out, errs


def release_entry(character, version, decision_ref, date, task, decision="", root=ROOT):
    """The manifest entry version_switch writes: the features the version's files use (None when it uses none)."""
    feats = sorted(used_by_version(root).get((character, version), set()))
    if not feats:
        return None
    e = {"character": character, "version": version, "features": feats, "decision_ref": decision_ref,
         "date": date, "task": task}
    if decision:
        e["decision"] = decision
    return e


def write_entry(entry, root=ROOT):
    """Add or replace the (character, version) entry; other entries stay as they are. Returns the manifest path."""
    path = os.path.join(root, MANIFEST)
    data = json.load(open(path, encoding="utf-8")) if os.path.isfile(path) else {"schema": SCHEMA, "releases": []}
    rel = [e for e in data.get("releases", [])
           if not (isinstance(e, dict) and (e.get("character"), e.get("version")) == (entry["character"],
                                                                                        entry["version"]))]
    data["releases"] = rel + [entry]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return path


def main():
    out, errs = violations()
    for e in errs:
        print(f"[release_rule] MANIFEST {e}")
    for r, f, why in out:
        print(f"[release_rule] VIOLATION {r}: {f}: {why}")
    print(f"[release_rule] {'OK' if not out and not errs else 'FAILED'} ({len(out)} violations, {len(errs)} "
          "manifest problems)")
    return 0 if not out and not errs else 1


if __name__ == "__main__":
    sys.exit(main())
