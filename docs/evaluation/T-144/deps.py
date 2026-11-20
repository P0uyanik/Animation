"""T-144 round 2 (option b, report step): generator-version dependency list.

    python3 docs/evaluation/T-144/deps.py --out docs/evaluation/T-144/deps.json

Read-only. For each git ref (origin/main and the task branches named in the brief), extracts the ref's
pipeline/charsys, character specs, stored version specs and override files into a temporary folder (git archive; the
work tree is never touched), then in a fresh Python process per ref:
  * loads that ref's versions.REGISTRY (so versions a branch registers, e.g. groom/5 on T-167, are seen);
  * resolves the generator pins of every relevant spec with that ref's spec.load (+ each override file, one at a time
    and all of the ref's new overrides of a character together), exactly as build_character does;
  * follows each pinned module's static imports inside pipeline/charsys (AST; transitive) to get the module closure.
No Blender is needed: spec.py and versions.py are plain Python.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
REFS = ["origin/main", "origin/t-155-claude-candidates-r2", "origin/t-156-claude-eye-targets", "origin/t-159-claude-ears",
        "origin/t-167-claude-hair-r7", "origin/t-168-claude-boy-face"]
CANDIDATE_REF = "origin/t-155-claude-candidates-r2"
CANDIDATES = {"boy_yellow_hoodie": "2.3.0", "girl_auburn_bun_glasses": "0.14.0", "girl_white_hair_blue_dress": "0.1.0"}
CHARS = ["boy_yellow_hoodie", "girl_auburn_bun_glasses", "girl_white_hair_blue_dress"]

WORKER = r'''
import ast, copy, glob, json, os, sys
tree, ref, new_overrides, current = sys.argv[1], sys.argv[2], json.loads(sys.argv[3]), json.loads(sys.argv[4])
CS = os.path.join(tree, "pipeline", "charsys")
sys.path.insert(0, CS)
import versions as V
import spec as S
CHARS = %r

def char_of(path):
    b = os.path.basename(path)
    for c in CHARS:
        if b.startswith(c):
            return c
    if b.startswith(("third", "girl_white")): return "girl_white_hair_blue_dress"
    if b.startswith("girl"): return "girl_auburn_bun_glasses"
    if b.startswith("boy"): return "boy_yellow_hoodie"
    return None

def local(name):
    p = name.replace(".", "/")
    for cand in (os.path.join(CS, p + ".py"), os.path.join(CS, p, "__init__.py")):
        if os.path.exists(cand):
            return cand
    return None

def mod_name(path):
    rel = os.path.relpath(path, CS)[:-3].replace(os.sep, ".")
    return rel[:-9] if rel.endswith(".__init__") else rel

def imports(path):
    out, t = set(), ast.parse(open(path, encoding="utf-8").read())
    pkg = mod_name(path).rsplit(".", 1)[0] if "." in mod_name(path) else ""
    if path.endswith("__init__.py"): pkg = mod_name(path)
    for n in ast.walk(t):
        names = []
        if isinstance(n, ast.Import):
            names = [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            base = n.module or ""
            if n.level:
                parts = pkg.split(".") if pkg else []
                parts = parts[:len(parts) - (n.level - 1)] if n.level > 1 else parts
                base = ".".join([*parts, base] if base else parts)
            names = [base] + [base + "." + a.name if base else a.name for a in n.names]
        for nm in names:
            while nm:
                f = local(nm)
                if f and f != path:
                    out.add(f)
                    break
                nm = nm.rsplit(".", 1)[0] if "." in nm else ""
    return out

def closure(module):
    f = local(module)
    if not f: return []
    seen, todo = set(), [f]
    while todo:
        x = todo.pop()
        if x in seen: continue
        seen.add(x)
        todo.extend(imports(x) - seen)
    return sorted(mod_name(x) for x in seen)

reg = []
for feat, names in V.REGISTRY._entries.items():
    for name, vs in names.items():
        for num, e in vs.items():
            reg.append({"feature": feat, "pin": e["pin"], "module": e.get("module"), "status": e["status"],
                        "closure": closure(e["module"]) if e.get("module") else []})

def resolve(label, spec_path, overrides=()):
    try:
        spec, info = S.load(spec_path, list(overrides))
        return {"label": label, "spec": os.path.relpath(spec_path, tree),
                "overrides": [os.path.relpath(o, tree) for o in overrides], "pins": info["versions"]["generators"],
                "defaulted": info["versions"]["defaulted"]}
    except Exception as ex:
        return {"label": label, "spec": os.path.relpath(spec_path, tree),
                "overrides": [os.path.relpath(o, tree) for o in overrides], "error": f"{type(ex).__name__}: {ex}"}

rows = []
bases = {}
for c in CHARS:
    vd = os.path.join(tree, "assets", "characters", c, "versions")
    if c in current and os.path.exists(os.path.join(vd, current[c], "spec.json")):
        p = os.path.join(vd, current[c], "spec.json")
        bases.setdefault(c, []).append(("current " + current[c], p))
    for cand in [{"boy_yellow_hoodie": "2.3.0", "girl_auburn_bun_glasses": "0.14.0", "girl_white_hair_blue_dress": "0.1.0"}[c]]:
        for fn in ("spec.resolved.json", "spec.json"):
            p = os.path.join(vd, cand, fn)
            if os.path.exists(p):
                bases.setdefault(c, []).append(("candidate " + cand + " " + fn, p))
                break
for c, bl in bases.items():
    for label, p in bl:
        rows.append(resolve(f"{c} {label}", p))
        mine = [os.path.join(tree, o) for o in new_overrides if char_of(o) == c]
        for o in mine:
            rows.append(resolve(f"{c} {label} + {os.path.basename(o)}", p, [o]))
        if len(mine) > 1:
            rows.append(resolve(f"{c} {label} + all {len(mine)} new overrides of this ref", p, mine))
# every other spec file on the ref (informational: tests and legacy builds use these)
other = []
for p in sorted(glob.glob(os.path.join(tree, "assets", "characters", "*", "spec", "**", "*.spec.json"), recursive=True)):
    other.append(resolve("spec file", p))
print(json.dumps({"ref": ref, "registry": reg, "resolved": rows, "spec_files": other}))
''' % (CHARS,)


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    main_sha = git("rev-parse", "origin/main").strip()
    current = {c: json.load(open(os.path.join(ROOT, "assets/characters", c, "versions/index.json")))["pointers"]
               .get("approved") for c in CHARS if os.path.exists(os.path.join(ROOT, "assets/characters", c,
                                                                                  "versions/index.json"))}
    result = {"schema": "plush-studio.t144-deps/1", "origin_main": main_sha, "current_approved": current, "refs": []}
    for ref in REFS:
        sha = git("rev-parse", ref).strip()
        base = git("merge-base", "origin/main", ref).strip()
        changed = git("diff", "--name-only", f"{base}...{ref}").split() if ref != "origin/main" else []
        new_ov = sorted(p for p in changed if p.endswith(".json") and "override" in os.path.basename(p) or
                        (p.endswith(".json") and "/overrides/" in p))
        with tempfile.TemporaryDirectory() as td:
            paths = ["pipeline/charsys", ":(glob)assets/characters/**/*.json"]
            ar = subprocess.run(["git", "archive", ref, "--", *paths, *new_ov], cwd=ROOT, check=True, capture_output=True)
            subprocess.run(["tar", "-x", "-C", td, "--exclude=*.blend", "--exclude=*.glb", "--exclude=*.png",
                            "--exclude=*.jpg"], input=ar.stdout, check=True)
            # Refs branched before T-155 have no candidate version folders: overlay T-155's candidate specs so each
            # ref's overrides are also resolved on top of boy 2.3.0 / girl 0.14.0 / third 0.1.0 (marked below).
            overlaid = []
            for c, v in CANDIDATES.items():
                rel = f"assets/characters/{c}/versions/{v}/spec.resolved.json"
                if not os.path.exists(os.path.join(td, rel)):
                    os.makedirs(os.path.dirname(os.path.join(td, rel)), exist_ok=True)
                    open(os.path.join(td, rel), "w").write(git("show", f"{CANDIDATE_REF}:{rel}"))
                    overlaid.append(rel)
            out = subprocess.run([sys.executable, "-I", "-c", WORKER, td, ref, json.dumps(new_ov), json.dumps(current)],
                                 capture_output=True, text=True, cwd=td)
            if out.returncode:
                raise SystemExit(f"{ref}: {out.stderr}")
            data = json.loads(out.stdout.strip().splitlines()[-1])
        data.update({"candidate_specs_overlaid_from_t155": overlaid, "sha": sha, "merge_base_with_main": base, "new_override_files": new_ov,
                     "changed_charsys_files": sorted(p for p in changed if p.startswith("pipeline/charsys/"))})
        result["refs"].append(data)
        print(f"{ref} {sha[:7]}: {len(data['resolved'])} resolved, {len(data['spec_files'])} spec files", file=sys.stderr)
    json.dump(result, open(a.out, "w"), indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
