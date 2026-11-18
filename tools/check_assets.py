#!/usr/bin/env python3
"""Integrity check of the published character versions (T-075). Plain Python, no Blender.

    python3 tools/check_assets.py [--base origin/staging] [--root <repo>] [--json <report.json>]

For every store assets/characters/<id>/versions/:
  1. index.json is valid; every indexed version has a folder with manifest.json and every version folder is indexed
     (no leftover hidden ".<ver>.partial" staging folders);
  2. the "approved" and "reference" pointers name existing versions (or are null), and the approved version's status
     is "approved";
  3. every file matches its manifest sha256 and size, spec.json matches spec_sha256, no unexpected files
     (asset_store.verify_version, without the file-mode test: git checkouts do not keep read-only modes);
  4. read-only intent: the manifest lists every payload file of the version (nothing is mutable state), and no file
     exceeds 95 MB (GitHub limit);
  5. against --base (default origin/staging when it exists, else origin/main): no file of a version that exists in
     --base is modified, deleted or added (new versions are new folders only); index.json keeps every existing
     version entry (only its "status" / "approval_notes" may change through `approve`) and its history is append-only.
Exit code 0 = all checks pass."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import asset_store as AS  # noqa: E402

MUTABLE_VERSION_KEYS = {"status", "approval_notes"}  # changed only by asset_store.py approve


def git(root, *args, check=False):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=check)


def choose_base(root, explicit):
    if explicit:
        return explicit
    for ref in ("origin/staging", "origin/main"):
        if git(root, "rev-parse", "--verify", "--quiet", ref + "^{commit}").returncode == 0:
            return ref
    return ""


def stores(root):
    chars = os.path.join(root, "assets", "characters")
    out = []
    for cid in sorted(os.listdir(chars)) if os.path.isdir(chars) else []:
        sd = os.path.join(chars, cid, "versions")
        if os.path.isdir(sd):
            out.append((cid, sd))
    return out


def check_store(cid, sd):
    problems, sizes = [], {}
    ip = os.path.join(sd, "index.json")
    if not os.path.isfile(ip):
        return [f"{cid}: versions/ has no index.json"], sizes
    try:
        idx = json.load(open(ip, encoding="utf-8"))
    except ValueError as e:
        return [f"{cid}: index.json is not valid JSON ({e})"], sizes
    if idx.get("character_id") != cid:
        problems.append(f"{cid}: index.json character_id is {idx.get('character_id')!r}")
    versions = idx.get("versions", {})
    folders = sorted(d for d in os.listdir(sd) if os.path.isdir(os.path.join(sd, d)))
    for d in folders:
        if d.startswith("."):
            problems.append(f"{cid}: leftover staging folder {d} (an interrupted publish)")
        elif d not in versions:
            problems.append(f"{cid}: version folder {d} is not in index.json")
    for ver in sorted(versions):
        if not AS.VERSION_RE.match(ver):
            problems.append(f"{cid}: bad version string {ver!r}")
        if not os.path.isfile(os.path.join(sd, ver, "manifest.json")):
            problems.append(f"{cid} {ver}: indexed but has no folder/manifest.json")
            continue
        man = json.load(open(os.path.join(sd, ver, "manifest.json"), encoding="utf-8"))
        if man.get("character_id") != cid or man.get("version") != ver:
            problems.append(f"{cid} {ver}: manifest names {man.get('character_id')} {man.get('version')}")
        if man.get("spec_sha256") != versions[ver].get("spec_sha256"):
            problems.append(f"{cid} {ver}: index spec_sha256 differs from the manifest")
        res = AS.verify_version(sd, ver, require_readonly=False)
        problems += [f"{cid} {ver}: {p}" for p in res["problems"]]
        listed = set(man.get("files", {})) | set(man.get("not_stored", {}))
        missing = [f for f in AS.payload(cid) if f not in listed]
        if missing:
            problems.append(f"{cid} {ver}: payload files neither stored nor recorded as not stored: {missing}")
        total = 0
        for f in os.listdir(os.path.join(sd, ver)):
            n = os.path.getsize(os.path.join(sd, ver, f))
            total += n
            if n > AS.MAX_FILE_BYTES:
                problems.append(f"{cid} {ver}: {f} is {n} bytes (> {AS.MAX_FILE_BYTES})")
        sizes[ver] = total
    pointers = idx.get("pointers", {})
    for name in ("approved", "reference"):
        v = pointers.get(name)
        if v is not None and v not in versions:
            problems.append(f"{cid}: pointer {name} -> {v}, which is not a published version")
    if pointers.get("approved") in versions and versions[pointers["approved"]].get("status") != "approved":
        problems.append(f"{cid}: approved pointer {pointers['approved']} has status "
                        f"{versions[pointers['approved']].get('status')!r}")
    return problems, sizes


def base_json(root, base, rel):
    r = git(root, "show", f"{base}:{rel}")
    return json.loads(r.stdout) if r.returncode == 0 else None


def check_diff(root, base):
    """Published files (versions present in base) are never changed; index.json is append-only."""
    problems = []
    r = git(root, "diff", "--name-status", "--no-renames", base, "--", "assets/characters")
    changed = [line.split("\t", 1) for line in r.stdout.splitlines() if "\t" in line]
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "--", "assets/characters").stdout.split()
    changed += [["A", p] for p in untracked]
    for status, path in changed:
        parts = path.split("/")
        if len(parts) < 5 or parts[3] != "versions":
            continue
        cid, item = parts[2], parts[4]
        if len(parts) == 5 and item == "index.json":
            continue
        if git(root, "cat-file", "-e", f"{base}:assets/characters/{cid}/versions/{item}/manifest.json").returncode == 0:
            problems.append(f"published file changed vs {base}: {status} {path}")
    for cid, sd in stores(root):
        rel = f"assets/characters/{cid}/versions/index.json"
        old = base_json(root, base, rel)
        if old is None:
            continue
        new = json.load(open(os.path.join(sd, "index.json"), encoding="utf-8"))
        for ver, entry in old.get("versions", {}).items():
            cur = new.get("versions", {}).get(ver)
            if cur is None:
                problems.append(f"{cid}: version {ver} removed from index.json (vs {base})")
                continue
            for k in set(entry) | set(cur):
                if k not in MUTABLE_VERSION_KEYS and entry.get(k) != cur.get(k):
                    problems.append(f"{cid} {ver}: index entry field {k!r} changed (vs {base})")
        oh, nh = old.get("history", []), new.get("history", [])
        if nh[:len(oh)] != oh:
            problems.append(f"{cid}: index.json history is not append-only (vs {base})")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default="", help="git ref for the diff check (default origin/staging, else origin/main)")
    ap.add_argument("--root", default=ROOT, help="repository root (tests use a temporary repository)")
    ap.add_argument("--json", default="")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.root)
    report = {"stores": {}, "problems": []}
    for cid, sd in stores(root):
        probs, sizes = check_store(cid, sd)
        idx = AS._safe_json(os.path.join(sd, "index.json"))
        report["stores"][cid] = {"versions": sorted(idx.get("versions", {})), "pointers": idx.get("pointers", {}),
                                 "bytes": sizes, "ok": not probs}
        report["problems"] += probs
    base = choose_base(root, a.base)
    if base:
        report["base"] = base
        report["problems"] += check_diff(root, base)
    else:
        report["base"] = None
        report["problems"].append("no base ref (origin/staging or origin/main) for the published-files diff check")
    report["pass"] = not report["problems"]
    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
        json.dump(report, open(a.json, "w", encoding="utf-8"), indent=1, sort_keys=True)
    for cid, st in report["stores"].items():
        sizes = ", ".join(f"{v} {b / 1e6:.1f} MB" for v, b in st["bytes"].items())
        print(f"[check_assets] {cid}: {sizes or 'no versions'}; pointers {st['pointers']}")
    for p in report["problems"]:
        print(f"[check_assets] FAIL {p}")
    print(f"[check_assets] {'PASS' if report['pass'] else 'FAIL'} ({len(report['stores'])} stores, base {base or '-'})")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
