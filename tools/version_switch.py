#!/usr/bin/env python3
"""Make a new character version current in one command (T-088).

    python3 tools/version_switch.py --character <id> --version <x.y.z> --spec <path> [--overrides <file> ...] \
        --task T-NNN --decision "<owner wording>" --decision-ref "docs/process/OWNER_DECISIONS.md <date>" \
        --blender <exe> [--notes "..."] [--identity-change-approved-by "..."] [--fidelity-json <fidelity.json>] \
        [--work <dir>] [--dry-run] [--publish-only | --approve-published]

Steps, in this order (each one only after the previous one succeeded):
  1. validate   everything below is checked before anything is written, and every problem is reported at once:
                version x.y.z, never used in the store, no golden baseline for it yet; the spec loads (spec.load with
                the overrides), identity.id is the character, metadata.spec_version is the version; every generator
                pin resolves (versions.resolve_pins); the materials pin covers the preset families the assignments
                use (a presets/2 id such as skin-felt/2 needs generators.materials = presets/2); the gate's
                regression accepts the build inputs (tools/regression/tiers.py character_config on a scratch copy);
                identity changes vs the approved parent carry --identity-change-approved-by; the owner decision is
                given and recorded in the decision file; the task's claim covers every path this run writes.
  2. build      pipeline/charsys/build_character.py (determinism.subprocess_env, one thread, fixed seed) into
     publish    <work>/build, then asset_store publish --without-glb (refuses an existing or reused version).
  3. approve    asset_store approve --by "owner (<decision-ref>)" --notes "<decision>".
  4. baseline   fidelity score (tools/fidelity/run.py on the build at the baseline's render settings, or
                --fidelity-json from an earlier run of the same build), copied to
                docs/evaluation/characters/<task>/fidelity/; the character's entry in
                docs/evaluation/characters/fidelity_baseline.json gets build, overrides, score, source and a
                rebaseline note (previous version, score and source). Other entries are not touched.
  5. golden     tools/regression/run.py --character <id> --changed <id> --no-fidelity --write-baseline, then the
                candidate is copied to docs/evaluation/regression/baselines/<id>/<version>/ (refuses to overwrite).
  6. checks     tools/check_cast.py, tools/check_assets.py and the plain-Python tests that read current versions,
                plus every other plain-Python test that names the character (tests that need Blender are listed,
                not run). Then: nothing outside the expected files changed (other characters, other versions,
                other baseline entries and goldens are hashed before and after).
  7. trailers   prints the exact "Supervisor-Approved: <path>" block for every guarded path (tools/guarded_paths.txt)
                this run wrote; the Supervisor adds it to the approval commit.

--publish-only (T-094) runs steps 1, 2, the fidelity score of step 4 and step 6 only: the new version is validated,
built and published (its status stays "candidate"), and the score is copied to
docs/evaluation/characters/<task>/fidelity/<id>/ for the owner's review. It does NOT approve (no pointer moves), does
NOT touch docs/evaluation/characters/fidelity_baseline.json and does NOT write a golden baseline; step 6 checks that
(the whole baseline file, the store pointers and the golden root are compared before and after). Making the version
current later is a normal run without --publish-only on a new number, or by hand (asset_store approve + baseline +
golden), after the owner's decision.

--approve-published (T-094 step 2) makes an already-published candidate current: steps 3 to 7 on the version in the
store (no build, no publish). The spec given must be the version's own (its hash is the manifest's spec_sha256); the
score is reused from docs/evaluation/characters/<task>/fidelity/<id>/fidelity.json (written by --publish-only) or
--fidelity-json. Refused when the version is not published, is already approved, fails verification or has no
fidelity report. The published version folder is checked to be byte-identical afterwards.

The fidelity evidence is copied with its side-by-side sheets: sheets/*.png become JPEG and report.md links them.

--dry-run runs step 1 and prints every step, command and file without writing anything (exit 1 when step 1 finds a
problem). The frozen-manifest and immutability checks are not changed: this tool only calls asset_store.py, which
never writes into a published version."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CHARSYS = ROOT / "pipeline" / "charsys"
sys.path.insert(0, str(CHARSYS))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "regression"))
import asset_store as AS  # noqa: E402
import spec as S  # noqa: E402
import versions as V  # noqa: E402
from materials import builder as MATERIALS  # noqa: E402
import integrate  # noqa: E402
import tiers  # noqa: E402

FIDELITY_BASELINE = "docs/evaluation/characters/fidelity_baseline.json"
GOLDEN_ROOT = "docs/evaluation/regression/baselines"
GUARDED_PATHS = "tools/guarded_paths.txt"
VIEWS = ROOT / "tools" / "regression" / "views.json"
VERSION_FILES = ["{cid}_master.blend", "spec.json", "components.json", "animation_compat.json", "build_report.json",
                 "manifest.json"]
# Plain-Python checks that read the current / approved versions (run after every switch).
AFFECTED_TESTS = [
    "tools/check_cast.py",
    "tools/check_assets.py",
    "pipeline/production/tests/test_run_shot_current.py",
    "pipeline/charsys/tests/test_versions.py",
    "pipeline/charsys/tests/test_skin_presets.py",
    "pipeline/charsys/tests/test_asset_store_guard.py",
    "tools/regression/tests/test_gate_tools.py",
]
TEST_DIRS = ("pipeline", "tools", "tests")


class SwitchFailed(Exception):
    pass


class Runner:
    """Runs the external tools. Tests replace it with a fake that writes the expected outputs (no Blender)."""

    def run(self, command: list[str], log: Path, cwd: Path, env: dict | None = None) -> int:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8", errors="replace") as out:
            out.write("$ " + " ".join(str(c) for c in command) + "\n")
            out.flush()
            return subprocess.run([str(c) for c in command], cwd=cwd, stdout=out, stderr=subprocess.STDOUT,
                                  env=env).returncode

    def build_env(self) -> dict:
        import determinism
        return determinism.subprocess_env()


# --------------------------------------------------------------------------- helpers

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(root: Path, path: Path) -> str:
    return Path(os.path.abspath(path)).relative_to(root).as_posix()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def guarded_patterns(root: Path) -> list[str]:
    path = root / GUARDED_PATHS if (root / GUARDED_PATHS).is_file() else ROOT / GUARDED_PATHS
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")]


def trailer_block(paths, root: Path) -> list[str]:
    patterns = guarded_patterns(root)
    return [f"Supervisor-Approved: {p}" for p in sorted(set(paths))
            if any(integrate.path_matches(p, pat) for pat in patterns)]


def golden_files() -> list[str]:
    views = read_json(VIEWS)
    ids = [v["id"] for v in views["views"]] + ([views["closeup"]["id"]] if views.get("closeup") else [])
    return ["golden.json", "fingerprint.json"] + [f"images/{i}.png" for i in ids]


def preset_family(preset_id):
    """(name, number) of the material preset family an id resolves from (presets/1, the presets/2 skin family, the
    T-092 presets/3 library), or None when unknown. materials.builder decides, so the build and this check agree."""
    family = MATERIALS.preset_family(preset_id)
    return V.parse(family) if family else None


def presets_problems(spec: dict) -> list[str]:
    """The materials pin must cover every preset family the assignments use (2026-11-18: skin-felt/2 is a presets/2
    id; with the presets/1 default pin the build and the skin-preset test disagree)."""
    assignments = (spec.get("materials") or {}).get("assignments") or {}
    if not assignments:
        return []
    try:
        pin = V.resolve_pins(spec)[0]["materials"]
    except V.VersionError:
        return []  # reported by the pin check
    need = {}
    for slot, cfg in sorted(assignments.items()):
        fam = preset_family((cfg or {}).get("preset"))
        if fam is None:
            return [f"materials.assignments.{slot}: unknown preset {(cfg or {}).get('preset')!r}"]
        need.setdefault(fam, []).append(f"{slot}={cfg.get('preset')}")
    name, number = V.parse(pin) if pin != V.NONE else ("none", 0)
    problems = []
    for (fname, fnum), slots in sorted(need.items()):
        if fname != name or fnum > number:
            problems.append(f"presets pin inconsistent: {', '.join(slots)} belong(s) to {fname}/{fnum}, but the "
                            f"materials pin is {pin} (set generators.materials = \"{fname}/{fnum}\" in the spec)")
    return problems


def load_claim(root: Path, task: str):
    ownership = root / "docs" / "process" / "OWNERSHIP.md"
    claims = integrate.load_claims(ownership) if ownership.is_file() else []
    return integrate.find_claim(task, claims, root / "docs" / "tasks")


# --------------------------------------------------------------------------- plan (step 1)

class Plan:
    def __init__(self, a, root: Path):
        self.a, self.root = a, root
        self.cid, self.version, self.task = a.character, a.version, a.task
        self.store = root / "assets" / "characters" / self.cid / "versions"
        self.version_dir = self.store / self.version
        self.golden_dir = root / GOLDEN_ROOT / self.cid / self.version
        self.publish_only = bool(getattr(a, "publish_only", False))
        self.approve_published = bool(getattr(a, "approve_published", False))
        # publish-only / approve-published: one task may handle several characters, so the evidence goes into a
        # folder per character
        self.evidence_dir = (root / "docs" / "evaluation" / "characters" / self.task / "fidelity"
                             / (self.cid if (self.publish_only or self.approve_published) else ""))
        self.fidelity_src: Path | None = None  # approve-published: the fidelity.json the score comes from
        self.work = Path(os.path.abspath(a.work)) if a.work else root / "build" / "version_switch" / f"{self.cid}-{self.version}"
        self.spec_rel = self.overrides_rel = None
        self.spec = None
        self.parent = None
        self.previous = {}
        self.fitted = False
        self.problems: list[str] = []
        self.written: list[str] = []

    def fail(self, msg):
        self.problems.append(msg)

    def inside(self, path: str) -> str | None:
        p = Path(os.path.abspath(self.root / path))
        try:
            return p.relative_to(self.root).as_posix()
        except ValueError:
            return None

    def validate(self) -> None:
        a, cid, root = self.a, self.cid, self.root
        if not AS.VERSION_RE.match(self.version or ""):
            self.fail(f"--version must be x.y.z, got {self.version!r}")
            return
        if not re.fullmatch(r"T-\d+[a-z0-9]*", self.task or ""):
            self.fail("--task must be the task id (T-NNN) whose claim covers this switch")
        # store: refuse an existing or reused version number (asset_store would refuse it after the build)
        idx = AS.load_index(str(self.store), cid)
        if self.approve_published:
            entry = idx["versions"].get(self.version)
            if entry is None or not (self.version_dir / "manifest.json").is_file():
                self.fail(f"{cid} {self.version} is not published: --approve-published only makes an already "
                          "published version current (publish it first, e.g. with --publish-only)")
            elif idx["pointers"].get("approved") == self.version or entry.get("status") == "approved":
                self.fail(f"{cid} {self.version} is already approved")
            elif AS.verify_version(str(self.store), self.version)["ok"] is not True:
                self.fail(f"{cid} {self.version} fails asset_store verification; not approved")
        elif os.path.lexists(self.version_dir) or self.version in AS.used_versions(idx):
            self.fail(f"{cid} {self.version} is already published (or the number was used before): published "
                      "versions are immutable and numbers are never reused; choose a new version")
        self.parent = idx["pointers"].get("approved") or idx["pointers"].get("reference")
        # spec + overrides: inside the character's spec folder, load and validate
        spec_folder = f"assets/characters/{cid}/spec/"
        self.spec_rel = self.inside(a.spec)
        self.overrides_rel = [self.inside(o) for o in a.overrides]
        missing = False
        for given, r in [(a.spec, self.spec_rel)] + list(zip(a.overrides, self.overrides_rel)):
            if r is None or not r.startswith(spec_folder):
                self.fail(f"{given}: build inputs must be in {spec_folder} (never another character's files)")
                missing = True
            elif not (root / r).is_file():
                self.fail(f"{given}: file not found")
                missing = True
        if missing:
            return
        try:
            self.spec, _info = S.load(str(root / self.spec_rel), [str(root / o) for o in self.overrides_rel])
        except (ValueError, OSError, V.VersionError) as exc:
            self.fail(f"spec does not load: {exc}")
            return
        if self.spec.get("identity", {}).get("id") != cid:
            self.fail(f"spec identity.id is {self.spec.get('identity', {}).get('id')!r}, not {cid!r}")
        sv = self.spec.get("metadata", {}).get("spec_version")
        if sv != self.version:
            self.fail(f"spec metadata.spec_version is {sv!r} but --version is {self.version!r}: the golden baseline "
                      f"is stored per spec_version, so they must match")
        try:
            pins, _src = V.resolve_pins(self.spec)
            self.fitted = str(pins.get("body", "")).startswith("body_generic")
        except V.VersionError as exc:
            self.fail(f"generator pins do not resolve: {exc}")
        self.problems.extend(presets_problems(self.spec))
        if self.approve_published and (self.version_dir / "manifest.json").is_file():
            man = read_json(self.version_dir / "manifest.json")
            if S.sha256(self.spec) != man.get("spec_sha256"):
                self.fail(f"the spec (+ overrides) is not the one {cid} {self.version} was built from (hash differs "
                          "from its manifest's spec_sha256); the baseline entry must name the published build inputs")
        # the gate's regression must accept the inputs (2026-11-18: version specs were refused by tiers.py)
        self.problems.extend(self.tiers_problems())
        # golden baseline and evidence: never overwritten
        if self.golden_dir.exists():
            self.fail(f"{rel(root, self.golden_dir)} already exists: a golden baseline is never overwritten")
        if self.approve_published:
            own = self.evidence_dir / "fidelity.json"
            if a.fidelity_json:
                src = Path(os.path.abspath(a.fidelity_json))
                if not src.is_file():
                    self.fail(f"--fidelity-json {a.fidelity_json}: file not found")
                elif own.exists() and src != own:
                    self.fail(f"{rel(root, self.evidence_dir)}/fidelity.json already exists; not overwritten")
                else:
                    self.fidelity_src = src
            elif own.is_file():
                self.fidelity_src = own
            else:
                self.fail(f"no fidelity report for {cid} {self.version}: expected {rel(root, own)} (from "
                          "--publish-only) or --fidelity-json")
        else:
            if (self.evidence_dir / "fidelity.json").exists():
                self.fail(f"{rel(root, self.evidence_dir)}/fidelity.json already exists; not overwritten")
            if a.fidelity_json and not Path(a.fidelity_json).is_file():
                self.fail(f"--fidelity-json {a.fidelity_json}: file not found")
        # identity changes need the owner's approval (asset_store publish would refuse after the build)
        if self.parent and self.spec is not None and not self.approve_published:  # checked when it was published
            pspec = self.store / self.parent / "spec.json"
            changed = S.identity_changes(read_json(pspec), self.spec) if pspec.is_file() else []
            if changed and not a.identity_change_approved_by:
                self.fail(f"identity sections changed vs {self.parent}: {changed}; pass "
                          "--identity-change-approved-by \"<who, when>\" (owner approval)")
        # owner decision: given and recorded before anything is published
        if not (a.decision or "").strip():
            self.fail("--decision is required: the owner's wording that makes this version current")
        ref_file = (a.decision_ref or "").split(" ")[0]
        if not ref_file:
            self.fail("--decision-ref is required (e.g. \"docs/process/OWNER_DECISIONS.md 2026-11-18\")")
        elif not (root / ref_file).is_file():
            self.fail(f"decision file {ref_file} not found")
        elif self.version not in (root / ref_file).read_text(encoding="utf-8"):
            self.fail(f"{ref_file} does not mention {self.version}: record the owner decision before the switch")
        # previous baseline entry
        baseline_path = root / FIDELITY_BASELINE
        if not baseline_path.is_file():
            self.fail(f"{FIDELITY_BASELINE} not found")
        else:
            self.previous = read_json(baseline_path).get("characters", {}).get(cid) or {}
        # work folder: outside every store, new or empty
        if AS.store_of(str(self.work)):
            self.fail(f"--work {self.work} lies inside an asset store")
        elif self.work.exists() and any(self.work.iterdir()):
            self.fail(f"--work {self.work} must be new or empty")
        # claim: every path this run writes is inside the task's write-set (2026-11-18: the claim was widened only
        # after the publish, so the write-set check failed)
        claim = load_claim(root, self.task) if self.task else None
        if claim is None or not claim.write_set:
            self.fail(f"no claim for {self.task} (docs/process/OWNERSHIP.md or docs/tasks/{self.task}.md)")
        else:
            outside = integrate.write_set_violations(self.predicted_writes(), claim)
            if outside:
                self.fail(f"the {self.task} claim does not cover: {', '.join(self.folders(outside))} (the "
                          "Supervisor widens the claim before the switch)")

    def folders(self, paths) -> list[str]:
        """Paths with the new version, golden and evidence folders shortened to '<folder>/**'."""
        dirs = [rel(self.root, d) + "/" for d in (self.version_dir, self.golden_dir, self.evidence_dir)]
        return sorted({next((d + "**" for d in dirs if p.startswith(d)), p) for p in paths})

    def tiers_problems(self) -> list[str]:
        """character_config of the would-be baseline entry, on a scratch copy of the inputs."""
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            folder = f"assets/characters/{self.cid}/spec"
            shutil.copytree(self.root / folder, t / folder)  # tiers also needs the character's main spec
            entry = {"score": 0.0, "build": self.spec_rel, "overrides": self.overrides_rel}
            (t / FIDELITY_BASELINE).parent.mkdir(parents=True, exist_ok=True)
            write_json(t / FIDELITY_BASELINE, {"characters": {self.cid: entry}})
            try:
                cfg = tiers.character_config(self.cid, t)
            except ValueError as exc:
                return [f"the regression gate would refuse these build inputs: {exc}"]
        if cfg["spec_version"] != self.version:
            return [f"the regression gate reads spec_version {cfg['spec_version']!r} (spec + overrides), not "
                    f"{self.version!r}: the golden baseline would land in the wrong folder"]
        return []

    def version_files(self) -> list[str]:
        names = [n.format(cid=self.cid) for n in VERSION_FILES] + (["spec.resolved.json"] if self.fitted else [])
        return [f"{rel(self.root, self.version_dir)}/{n}" for n in names]

    def predicted_writes(self) -> list[str]:
        evidence = [f"{rel(self.root, self.evidence_dir)}/{n}" for n in ("fidelity.json", "report.md")]
        if self.approve_published:  # the version folder exists; the evidence is copied only when it lives elsewhere
            copied = [] if self.fidelity_src is None or self.fidelity_src.parent == self.evidence_dir else evidence
            return ([rel(self.root, self.store / "index.json"), FIDELITY_BASELINE] + copied
                    + [f"{rel(self.root, self.golden_dir)}/{n}" for n in golden_files()])
        if self.publish_only:  # no baseline entry, no golden baseline
            return self.version_files() + [rel(self.root, self.store / "index.json")] + evidence
        return (self.version_files() + [rel(self.root, self.store / "index.json"), FIDELITY_BASELINE] + evidence
                + [f"{rel(self.root, self.golden_dir)}/{n}" for n in golden_files()])

    # ----------------------------------------------------------------------- commands
    def build_command(self):
        cmd = [self.a.blender or "<blender>", "-b", "--factory-startup", "-t", "1", "-P",
               str(CHARSYS / "build_character.py"), "--", "--spec", str(self.root / self.spec_rel)]
        for o in self.overrides_rel:
            cmd += ["--override", str(self.root / o)]
        return cmd + ["--out", str(self.work / "build"), "--no-glb"]

    def fidelity_command(self):
        render = read_json(self.root / FIDELITY_BASELINE).get("render", {})
        return [sys.executable, str(ROOT / "tools" / "fidelity" / "run.py"), "--character", self.cid, "--build",
                str(self.work / "build" / f"{self.cid}_master.blend"), "--blender", self.a.blender or "<blender>",
                "--out", str(self.work / "fidelity"), "--height", str(render.get("height", 640)),
                "--samples", str(render.get("samples", 32))]

    def regression_command(self):
        return [sys.executable, str(ROOT / "tools" / "regression" / "run.py"), "--blender",
                self.a.blender or "<blender>", "--out", str(self.work / "regression"), "--character", self.cid,
                "--changed", self.cid, "--no-fidelity", "--write-baseline"]

    def by(self):
        return f"owner ({self.a.decision_ref})"

    def notes(self):
        return self.a.notes or (f"{self.cid} {self.version} ({self.task}): spec {self.spec_rel}"
                                + (f" + {', '.join(self.overrides_rel)}" if self.overrides_rel else ""))

    def publish_argv(self):
        argv = ["publish", "--character", self.cid, "--store", str(self.store), "--build", str(self.work / "build"),
                "--version", self.version, "--notes", self.notes(), "--without-glb"]
        if self.a.identity_change_approved_by:
            argv += ["--identity-change-approved-by", self.a.identity_change_approved_by]
        return argv

    def approve_argv(self):
        return ["approve", "--character", self.cid, "--store", str(self.store), "--version", self.version,
                "--by", self.by(), "--notes", f"new current version: \"{self.a.decision}\" Recorded by {self.task} "
                                              f"(tools/version_switch.py)."]

    def new_entry(self, score: float) -> dict:
        prev = self.previous
        entry = {"score": round(float(score), 4), "build": self.spec_rel, "overrides": list(self.overrides_rel),
                 "source": f"{rel(self.root, self.evidence_dir)}/fidelity.json",
                 "rebaseline": {"task": self.task,
                                "reason": f"owner decision ({self.a.decision_ref}): {self.a.decision}",
                                "previous_version": self.parent,
                                "previous_score": prev.get("score"),
                                "previous_source": prev.get("source")}}
        return entry

    def tests(self) -> tuple[list[str], list[str]]:
        """(plain-Python tests to run, tests naming the character that need Blender: listed, not run). A test needs
        Blender when it imports bpy or takes --blender (they build or render; run them separately)."""
        run, blender = list(AFFECTED_TESTS), []
        for top in TEST_DIRS:
            base = self.root / top
            if not base.is_dir():
                continue
            for p in sorted(base.rglob("test_*.py")):
                r = rel(self.root, p)
                if r in run or "/tests/" not in f"/{r}" or r.startswith("tests/data/"):
                    continue
                text = p.read_text(encoding="utf-8", errors="replace")
                if self.cid not in text:
                    continue
                needs = re.search(r"^\s*(import|from) bpy\b|--blender", text, re.M)  # Blender or a Blender build
                (blender if needs else run).append(r)
        return run, blender


# --------------------------------------------------------------------------- execution

def snapshot(plan: Plan) -> dict[str, str]:
    """Hashes of everything this run must leave alone: every published version folder and index of other
    characters, every existing version of this character, every existing golden baseline, the other baseline
    entries."""
    root, out = plan.root, {}
    chars = root / "assets" / "characters"
    for p in sorted(chars.glob("*/versions/**/*")) if chars.is_dir() else []:
        if p.is_file() and p != plan.store / "index.json":
            out[rel(root, p)] = sha256_file(p)
    golden = root / GOLDEN_ROOT
    for p in sorted(golden.rglob("*")) if golden.is_dir() else []:
        if p.is_file():
            out[rel(root, p)] = sha256_file(p)
    data = read_json(root / FIDELITY_BASELINE)
    if plan.publish_only:  # the whole baseline file and the store pointers of this character stay as they are
        out[FIDELITY_BASELINE] = sha256_file(root / FIDELITY_BASELINE)
        idx = AS.load_index(str(plan.store), plan.cid)
        kept = {"pointers": idx.get("pointers"), "versions": {k: v for k, v in idx.get("versions", {}).items()
                                                              if k != plan.version}}
        out["<store pointers and existing versions>"] = hashlib.sha256(
            json.dumps(kept, sort_keys=True).encode()).hexdigest()
        return out
    others = {k: v for k, v in data.items() if k != "characters"}
    others["characters"] = {k: v for k, v in data.get("characters", {}).items() if k != plan.cid}
    out["<fidelity_baseline other entries>"] = hashlib.sha256(json.dumps(others, sort_keys=True).encode()).hexdigest()
    return out


def copy_evidence(src_dir: Path, dest_dir: Path, root: Path) -> list[str]:
    """fidelity.json and report.md of a fidelity run, with the side-by-side sheets report.md links: sheets/*.png are
    stored as JPEG (sheets/*.jpg, quality 85) and the links rewritten, so the committed report has no broken links
    (2026-11-19: the copied report linked sheets that were never copied). Without Pillow the PNGs are copied as they
    are. Returns the repository paths written."""
    written = []
    dest_dir.mkdir(parents=True, exist_ok=True)
    report = src_dir / "report.md"
    text = report.read_text(encoding="utf-8") if report.is_file() else None
    sheets = sorted(set(re.findall(r"sheets/([\w.-]+)\.png", text or "")))
    try:
        from PIL import Image
    except ImportError:
        Image = None
    for name in sheets:
        src = src_dir / "sheets" / f"{name}.png"
        if not src.is_file():
            continue
        (dest_dir / "sheets").mkdir(parents=True, exist_ok=True)
        if Image is None:
            shutil.copyfile(src, dest_dir / "sheets" / f"{name}.png")
            written.append(rel(root, dest_dir / "sheets" / f"{name}.png"))
        else:
            with Image.open(src) as im:
                im.convert("RGB").save(dest_dir / "sheets" / f"{name}.jpg", quality=85)
            written.append(rel(root, dest_dir / "sheets" / f"{name}.jpg"))
            text = re.sub(rf"sheets/{re.escape(name)}\.png", f"sheets/{name}.jpg", text)
    if (src_dir / "fidelity.json").is_file():
        shutil.copyfile(src_dir / "fidelity.json", dest_dir / "fidelity.json")
        written.append(rel(root, dest_dir / "fidelity.json"))
    if text is not None:
        (dest_dir / "report.md").write_text(text, encoding="utf-8")
        written.append(rel(root, dest_dir / "report.md"))
    return written


def asset_store(argv: list[str]) -> str:
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            AS.main(argv)
    except SystemExit as exc:
        if exc.code not in (None, 0):
            raise SwitchFailed(f"asset_store {argv[0]}: {exc.code}")
    return buf.getvalue().strip()


def execute(plan: Plan, runner: Runner) -> int:
    root, cid, ver, logs = plan.root, plan.cid, plan.version, plan.work / "logs"
    plan.work.mkdir(parents=True, exist_ok=True)
    before = snapshot(plan)
    written = plan.written
    report = {"character": cid, "version": ver, "task": plan.task, "publish_only": plan.publish_only,
              "approve_published": plan.approve_published, "steps": []}

    def step(name, detail):
        print(f"[version_switch] {name}: {detail}", flush=True)
        report["steps"].append({"step": name, "detail": detail})

    # 2. build + publish
    if plan.approve_published:
        step("publish", f"skipped (--approve-published): {cid} {ver} is already published "
                        f"({rel(root, plan.version_dir)}, verified)")
    else:
        if runner.run(plan.build_command(), logs / "build.log", ROOT, runner.build_env()):
            raise SwitchFailed(f"build failed; see {logs / 'build.log'}")
        step("build", f"{plan.work / 'build'}")
        step("publish", asset_store(plan.publish_argv()))
        written += [rel(root, p) for p in sorted(plan.version_dir.iterdir())]
    written.append(rel(root, plan.store / "index.json"))
    # 3. approve
    if plan.publish_only:
        step("approve", "skipped (--publish-only): the approved pointer stays on "
                        f"{AS.load_index(str(plan.store), cid)['pointers'].get('approved')}")
    else:
        step("approve", asset_store(plan.approve_argv()))
    # 4. fidelity score + baseline entry
    if plan.fidelity_src is not None:
        fsrc = plan.fidelity_src
    elif plan.a.fidelity_json:
        fsrc = Path(plan.a.fidelity_json)
    else:
        if runner.run(plan.fidelity_command(), logs / "fidelity.log", ROOT):
            raise SwitchFailed(f"fidelity failed; see {logs / 'fidelity.log'}")
        fsrc = plan.work / "fidelity" / "fidelity.json"
    score = read_json(fsrc)["overall"]["score"]
    if Path(os.path.abspath(fsrc)).parent != Path(os.path.abspath(plan.evidence_dir)):
        written += copy_evidence(fsrc.parent, plan.evidence_dir, root)
    if plan.publish_only:
        prev = plan.previous.get("score")
        drop = (float(prev) - float(score)) if prev is not None else None
        limit = (read_json(root / FIDELITY_BASELINE).get("policy") or {}).get("maximum_score_drop")
        step("score", f"{cid} {ver}: {round(float(score), 4)} (current {plan.parent}: {prev})"
                      + (f"; drop {round(drop, 4)} > {limit}: owner review" if drop is not None and limit is not None
                         and drop > limit else "")
                      + f"; {FIDELITY_BASELINE} not changed (--publish-only)")
        step("golden", "skipped (--publish-only): no golden baseline written")
        return finish(plan, runner, before, report)
    data = read_json(root / FIDELITY_BASELINE)
    data.setdefault("characters", {})[cid] = plan.new_entry(score)
    write_json(root / FIDELITY_BASELINE, data)
    written.append(FIDELITY_BASELINE)
    step("baseline", f"{cid} -> {ver}, score {round(float(score), 4)} (previous {plan.parent}, "
                     f"{plan.previous.get('score')})")
    # 5. golden regression baseline
    if runner.run(plan.regression_command(), logs / "regression.log", ROOT):
        raise SwitchFailed(f"regression failed; see {logs / 'regression.log'}")
    cand = plan.work / "regression" / "baselines" / cid / ver
    if not (cand / "golden.json").is_file():
        raise SwitchFailed(f"the regression wrote no baseline candidate at {cand} (spec_version mismatch?)")
    if read_json(cand / "golden.json").get("spec_version") != ver:
        raise SwitchFailed(f"baseline candidate is not for {ver}")
    if plan.golden_dir.exists():
        raise SwitchFailed(f"{plan.golden_dir} appeared during the run; not overwritten")
    shutil.copytree(cand, plan.golden_dir)
    written += [rel(root, p) for p in sorted(plan.golden_dir.rglob("*")) if p.is_file()]
    step("golden", rel(root, plan.golden_dir))
    return finish(plan, runner, before, report)


def finish(plan: Plan, runner: Runner, before: dict, report: dict) -> int:
    """Steps 6 and 7: cast check, affected tests, nothing else touched; trailers."""
    root, logs, written = plan.root, plan.work / "logs", plan.written

    def step(name, detail):
        print(f"[version_switch] {name}: {detail}", flush=True)
        report["steps"].append({"step": name, "detail": detail})
    run, need_blender = plan.tests()
    failed = []
    for t in run:
        if not (root / t).is_file():
            failed.append(f"{t} (missing)")
            continue
        if runner.run([sys.executable, str(root / t)], logs / "checks.log", root):
            failed.append(t)
    after = snapshot(plan)
    # approve-published: the published version folder existed before the run and must stay byte-identical
    new = ((() if plan.approve_published else (rel(root, plan.version_dir) + "/",))
           + (() if plan.publish_only else (rel(root, plan.golden_dir) + "/",)))
    touched = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k) and not k.startswith(new))
    if touched:
        failed.append("files outside this switch changed: " + ", ".join(touched))
    report["checks"] = {"run": run, "failed": failed, "need_blender_not_run": need_blender}
    step("checks", f"{len(run) - len([f for f in failed if not f.startswith('files outside')])}/{len(run)} passed"
         + (f"; FAILED: {', '.join(failed)} (see {logs / 'checks.log'})" if failed else "")
         + (f"; need Blender, run separately: {', '.join(need_blender)}" if need_blender else ""))
    # 7. trailers
    trailers = trailer_block(written, root)
    report.update(written=sorted(written), trailers=trailers, ok=not failed)
    write_json(plan.work / "version_switch.json", report)
    print("\n[version_switch] files written:\n  " + "\n  ".join(sorted(written)))
    print("\n[version_switch] approval trailers (guarded paths written by this run):\n" + "\n".join(trailers))
    return 0 if not failed else 1


def dry_run(plan: Plan) -> int:
    a = plan.a
    run, need_blender = plan.tests() if plan.spec is not None else ([], [])
    mode = " (--publish-only)" if plan.publish_only else " (--approve-published)" if plan.approve_published else ""
    lines = ["[version_switch] DRY RUN: nothing is written" + mode,
             f"1. validate  {'OK' if not plan.problems else 'FAILED'}"]
    lines += [f"     - {p}" for p in plan.problems]
    if plan.spec is not None and not plan.problems and plan.publish_only:
        lines += [
            f"2. build     {' '.join(plan.build_command())}",
            f"   publish   asset_store {' '.join(json.dumps(x) if ' ' in x else x for x in plan.publish_argv())}",
            f"             -> {rel(plan.root, plan.version_dir)}/ (parent {plan.parent}; status candidate)",
            "3. approve   skipped (--publish-only): no pointer moves",
            "4. score     " + (f"score from {a.fidelity_json}" if a.fidelity_json else ' '.join(plan.fidelity_command())),
            f"             -> {rel(plan.root, plan.evidence_dir)}/; {FIDELITY_BASELINE} not changed (--publish-only)",
            "5. golden    skipped (--publish-only): no golden baseline",
            "6. checks    " + ", ".join(run) + "; then: no other file changed (baseline file, pointers, goldens)",
        ]
        if need_blender:
            lines.append("             need Blender (listed, not run): " + ", ".join(need_blender))
        writes = plan.predicted_writes()
        lines.append("7. files     (predicted; report.md only when the fidelity run writes one"
                     + ("; spec.resolved.json because the body generator fits the spec" if plan.fitted else "") + ")")
        lines += [f"     {w}" for w in writes]
        lines.append("   trailers  (predicted)")
        lines += [f"     {t}" for t in trailer_block(writes, plan.root)]
    elif plan.spec is not None and not plan.problems and plan.approve_published:
        lines += [
            f"2. publish   skipped (--approve-published): {rel(plan.root, plan.version_dir)}/ is published and "
            "verified; it must stay byte-identical",
            f"3. approve   asset_store {' '.join(json.dumps(x) if ' ' in x else x for x in plan.approve_argv())}",
            f"4. baseline  score from {plan.fidelity_src}",
            f"             {FIDELITY_BASELINE}: {plan.cid} -> build {plan.spec_rel}, overrides {plan.overrides_rel}, "
            f"source {rel(plan.root, plan.evidence_dir)}/fidelity.json, rebaseline from {plan.parent} "
            f"(score {plan.previous.get('score')})",
            f"5. golden    {' '.join(plan.regression_command())}",
            f"             -> {rel(plan.root, plan.golden_dir)}/",
            "6. checks    " + ", ".join(run) + "; then: no other file changed (incl. the published version folder)",
        ]
        if need_blender:
            lines.append("             need Blender (listed, not run): " + ", ".join(need_blender))
        writes = plan.predicted_writes()
        lines.append("7. files     (predicted)")
        lines += [f"     {w}" for w in writes]
        lines.append("   trailers  (predicted)")
        lines += [f"     {t}" for t in trailer_block(writes, plan.root)]
    elif plan.spec is not None and not plan.problems:
        lines += [
            f"2. build     {' '.join(plan.build_command())}",
            f"   publish   asset_store {' '.join(json.dumps(x) if ' ' in x else x for x in plan.publish_argv())}",
            f"             -> {rel(plan.root, plan.version_dir)}/ (parent {plan.parent})",
            f"3. approve   asset_store {' '.join(json.dumps(x) if ' ' in x else x for x in plan.approve_argv())}",
            "4. baseline  " + (f"score from {a.fidelity_json}" if a.fidelity_json else ' '.join(plan.fidelity_command())),
            f"             {FIDELITY_BASELINE}: {plan.cid} -> build {plan.spec_rel}, overrides {plan.overrides_rel}, "
            f"source {rel(plan.root, plan.evidence_dir)}/fidelity.json, rebaseline from {plan.parent} "
            f"(score {plan.previous.get('score')})",
            f"5. golden    {' '.join(plan.regression_command())}",
            f"             -> {rel(plan.root, plan.golden_dir)}/",
            "6. checks    " + ", ".join(run) + "; then: no other file changed",
        ]
        if need_blender:
            lines.append("             need Blender (listed, not run): " + ", ".join(need_blender))
        writes = plan.predicted_writes()
        lines.append("7. files     (predicted; report.md only when the fidelity run writes one"
                     + ("; spec.resolved.json because the body generator fits the spec" if plan.fitted else "") + ")")
        lines += [f"     {w}" for w in writes]
        lines.append("   trailers  (predicted)")
        lines += [f"     {t}" for t in trailer_block(writes, plan.root)]
    print("\n".join(lines))
    return 0 if not plan.problems else 1


def parse(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--character", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--spec", required=True, help="the version's spec (repository path)")
    ap.add_argument("--overrides", nargs="*", default=[], help="override files applied on top of --spec")
    ap.add_argument("--task", required=True, help="task id whose claim covers the switch (T-NNN)")
    ap.add_argument("--decision", default="", help="the owner's wording that makes this version current")
    ap.add_argument("--decision-ref", default="", help="decision file and date, e.g. "
                                                       "\"docs/process/OWNER_DECISIONS.md 2026-11-18\"")
    ap.add_argument("--notes", default="", help="version notes in the store (default: task, spec, overrides)")
    ap.add_argument("--identity-change-approved-by", default="")
    ap.add_argument("--blender", default="", help="Blender executable (required unless --dry-run)")
    ap.add_argument("--fidelity-json", default="", help="reuse the fidelity.json of an earlier run of this build")
    ap.add_argument("--work", default="", help="new or empty work folder (default build/version_switch/<id>-<ver>)")
    ap.add_argument("--dry-run", action="store_true")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--publish-only", action="store_true",
                      help="validate, build, publish and score only: no approve, no fidelity_baseline.json change, "
                           "no golden baseline (T-094)")
    mode.add_argument("--approve-published", action="store_true",
                      help="make an already-published candidate current: approve, baseline entry (score reused), "
                           "golden baseline, checks, trailers; no build, no publish (T-094 step 2)")
    ap.add_argument("--root", default=str(ROOT), help=argparse.SUPPRESS)  # tests: a fixture repository
    a = ap.parse_args(argv)
    a.spec = os.path.relpath(os.path.abspath(a.spec), a.root) if os.path.isabs(a.spec) else a.spec
    a.overrides = [os.path.relpath(os.path.abspath(o), a.root) if os.path.isabs(o) else o for o in a.overrides]
    return a


def main(argv=None, runner: Runner | None = None) -> int:
    a = parse(argv)
    plan = Plan(a, Path(os.path.abspath(a.root)))
    plan.validate()
    if a.dry_run:
        return dry_run(plan)
    if not a.blender:
        plan.fail("--blender is required (or use --dry-run)")
    if plan.problems:
        print("[version_switch] refused, nothing written:\n  - " + "\n  - ".join(plan.problems), file=sys.stderr)
        return 1
    try:
        return execute(plan, runner or Runner())
    except SwitchFailed as exc:
        print(f"[version_switch] FAILED: {exc}\n  written before the failure (a published version stays published; "
              "continue by hand from the failed step):\n    " + "\n    ".join(plan.written or ["(nothing)"]),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
