"""Review recipe: one JSON per visual task that locks what is compared and how (T-087, round 2 plan A3).

    python3 tools/review/recipe.py validate <recipe.json>
    python3 tools/review/recipe.py preview  <recipe.json> --blender <exe> [--out <dir>]
    python3 tools/review/recipe.py sheet    <recipe.json> --blender <exe> [--out <dir>] [--skip-preview "<reason>"]

The recipe declares the input SHAs, the published baseline version, the candidate (published version, spec +
overrides + SHA, or a built .blend), the compare variant (pose and master), the cameras (rows with their reference
yaws), the light rig, samples and resolution. See docs/process/REVIEW_RECIPE.md and tools/review/recipes/.

validate  checks the recipe and every input; refuses A-pose or wrong-variant inputs unless the recipe explicitly asks
          for them (compare.allow_apose / compare.allow_variant_mismatch).
preview   renders ONE cheap frame of every view of every column (recipe "preview" settings: low-sample Cycles or
          Workbench) in one Blender run, checks the arm pose of every column and writes <out>/preview/preview.jpg and
          <out>/preview/preview.json (the record that the sheet requires).
sheet     the long render: refuses to start without a passing preview of the same recipe (--skip-preview "<reason>"
          overrides it and is logged in sheet.json and log.txt), renders every column in one run with identical cameras
          and lights, and writes the standard strict sheet <out>/sheet.jpg (columns: original reference | previous
          approved | candidate [| AI target]; rows: front, 3/4, side, back, face front, face 3/4).
Every command records the recipe next to its outputs: <out>/recipe.json (as given) and <out>/recipe.resolved.json."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RENDER_SIDE = os.path.join(HERE, "blender_render.py")
BUILDER = os.path.join(ROOT, "pipeline", "charsys", "build_character.py")
CALIBRATION = os.path.join(ROOT, "pipeline", "charsys", "render_calibration.json")

SCHEMA = "plush-studio.review-recipe/1"
ROWS = [("front", "front", "body"), ("threequarter", "3/4", "body"), ("side", "side", "body"), ("back", "back", "body"),
        ("face_front", "face front", "face"), ("face_threequarter", "face 3/4", "face")]
VARIANT_POSE = {"compare": "arms_down", "master": "apose"}
ARMS_DOWN_MAX_DEG = 20.0  # upper arm from straight down: compare variants measure ~12 deg, A-pose masters 30-45 deg
APOSE_MIN_DEG = 25.0
PREVIEW_MAX_SAMPLES = 8
PREVIEW_MAX_PX = 240
SHEET_MAX_PX = 2048
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


class RecipeError(Exception):
    """The recipe or one of its inputs is not acceptable; .problems lists every reason."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("review recipe refused:\n  - " + "\n  - ".join(self.problems))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def recipe_hash(recipe):
    return hashlib.sha256(json.dumps(recipe, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def repo_file(root, value, problems, what):
    """Repository-relative path that must exist inside the repository."""
    if not isinstance(value, str) or not value:
        problems.append(f"{what}: missing path")
        return None
    p = os.path.abspath(os.path.join(root, value))
    if not (p == root or p.startswith(root + os.sep)):
        problems.append(f"{what}: path escapes the repository: {value}")
        return None
    if not os.path.exists(p):
        problems.append(f"{what}: not found: {value}")
        return None
    return p


def git_commit_exists(root, sha):
    try:
        r = subprocess.run(["git", "-C", root, "cat-file", "-e", f"{sha}^{{commit}}"], capture_output=True)
    except OSError:
        return False
    return r.returncode == 0


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def comparison_pose_of(spec_paths):
    """rig.comparison_pose from the last of the given spec/override files that has one (overrides merge last)."""
    pose = None
    for p in spec_paths:
        try:
            d = load_json(p)
        except (OSError, ValueError):
            continue
        cp = (d.get("rig") or {}).get("comparison_pose") if isinstance(d, dict) else None
        if cp:
            pose = cp
    return pose


def resolve_column(root, cid, role, col, variant, allow_apose, problems):
    """-> resolved column dict: tag, label, kind, blend (or build), comparison_pose, provenance."""
    what = f"{role}"
    if not isinstance(col, dict):
        problems.append(f"{what}: must be an object")
        return None
    kinds = [k for k in ("version", "spec", "blend") if k in col]
    if len(kinds) != 1:
        problems.append(f"{what}: give exactly one of version, spec, blend (got {kinds or 'none'})")
        return None
    kind = kinds[0]
    out = {"role": role, "tag": role, "label": col.get("label") or "", "kind": kind}
    cdir = os.path.join(root, "assets", "characters", cid)
    if kind == "version":
        ver = str(col["version"])
        index_path = os.path.join(cdir, "versions", "index.json")
        try:
            index = load_json(index_path)
        except (OSError, ValueError):
            problems.append(f"{what}: no version store for {cid}")
            return None
        if ver not in index.get("versions", {}):
            problems.append(f"{what}: version {ver} is not published for {cid}")
            return None
        vdir = os.path.join(cdir, "versions", ver)
        master = os.path.join(vdir, f"{cid}_master.blend")
        if not os.path.exists(master):
            problems.append(f"{what}: published version {ver} has no {cid}_master.blend")
            return None
        out.update({"version": ver, "status": index["versions"][ver].get("status"),
                    "approved_pointer": index.get("pointers", {}).get("approved"),
                    "spec_sha256": index["versions"][ver].get("spec_sha256"),
                    "blend": os.path.relpath(master, root), "source_variant": "master"})
        out["label"] = out["label"] or ver
        if variant == "compare":
            spec_files = [p for p in (os.path.join(vdir, "spec.json"), os.path.join(vdir, "spec.resolved.json"))
                          if os.path.exists(p)]
            pose = comparison_pose_of(spec_files)
            if not pose:
                problems.append(f"{what}: version {ver} has no rig.comparison_pose, so it cannot be shown in the "
                                "compare variant (arms down); refusing to render its A-pose master instead")
            out["comparison_pose"] = pose
        else:
            out["comparison_pose"] = None
    elif kind == "spec":
        spec = repo_file(root, col["spec"], problems, f"{what}.spec")
        overrides = [repo_file(root, o, problems, f"{what}.overrides") for o in col.get("overrides", [])]
        sha = col.get("sha")
        if not isinstance(sha, str) or not SHA_RE.match(sha):
            problems.append(f"{what}: a spec candidate needs its commit SHA (sha, 7-40 hex digits)")
        out.update({"spec": col["spec"], "overrides": list(col.get("overrides", [])), "sha": sha,
                    "comparison_pose": None, "source_variant": variant})
        if spec and all(overrides):
            out["spec_sha256"] = sha256_file(spec)
            if variant == "compare" and not comparison_pose_of([spec] + overrides):
                problems.append(f"{what}: the spec has no rig.comparison_pose, so its build has no compare variant "
                                "(arms down); refusing an A-pose fallback")
        out["label"] = out["label"] or os.path.basename(col["spec"]).replace(".spec.json", "")
    else:
        blend = repo_file(root, col["blend"], problems, f"{what}.blend")
        name = os.path.basename(col["blend"])
        if variant == "compare" and name.endswith("_master.blend"):
            problems.append(f"{what}: {name} is an A-pose master but the compare variant (arms down) is required; "
                            "give the <id>_compare.blend (no A-pose fallback)")
        elif variant == "compare" and not name.endswith("_compare.blend"):
            problems.append(f"{what}: {name} is not named <id>_compare.blend, so its variant is unknown")
        elif variant == "master" and not name.endswith("_master.blend"):
            problems.append(f"{what}: {name} is not an <id>_master.blend (wrong variant for compare.variant master)")
        out.update({"blend": col["blend"], "comparison_pose": None, "source_variant": variant})
        if blend:
            out["blend_sha256"] = sha256_file(blend)
        out["label"] = out["label"] or name
    return out


def resolve_reference_image(root, cid, ref, ref_index, problems, what):
    rdir = os.path.join(root, "assets", "characters", cid, "references")
    if "file" not in ref:
        problems.append(f"{what}: reference needs a file")
        return None
    p = repo_file(rdir, ref["file"], problems, what)
    crop = ref.get("crop")
    if crop is not None and (not isinstance(crop, list) or len(crop) != 4 or not all(isinstance(c, int) for c in crop)
                             or crop[0] >= crop[2] or crop[1] >= crop[3]):
        problems.append(f"{what}: crop must be [x0, y0, x1, y1] integers with x0 < x1, y0 < y1")
    return {"file": os.path.relpath(p, root) if p else ref["file"], "crop": crop, "label": ref.get("label", "")}


def validate(recipe, root=ROOT, check_git=True):
    """-> resolved recipe (dict). Raises RecipeError listing every problem."""
    problems = []
    if not isinstance(recipe, dict) or recipe.get("schema") != SCHEMA:
        raise RecipeError([f"schema must be {SCHEMA}"])
    cid = recipe.get("character")
    cdir = os.path.join(root, "assets", "characters", str(cid))
    if not isinstance(cid, str) or not os.path.isdir(cdir):
        raise RecipeError([f"unknown character: {cid}"])
    res = {"schema": SCHEMA, "character": cid, "task": recipe.get("task", ""), "recipe_sha256": recipe_hash(recipe)}

    # input SHAs
    shas = recipe.get("inputs")
    if not isinstance(shas, dict) or not shas:
        problems.append("inputs: give the input SHAs, e.g. {\"main\": \"ab9fd4c\"}")
        shas = {}
    for k, v in shas.items():
        if not isinstance(v, str) or not SHA_RE.match(v):
            problems.append(f"inputs.{k}: not a commit SHA: {v!r}")
        elif check_git and not git_commit_exists(root, v):
            problems.append(f"inputs.{k}: commit {v} not found in this repository")
    res["inputs"] = dict(shas)

    # compare variant
    cmp_ = recipe.get("compare") or {}
    variant, pose = cmp_.get("variant"), cmp_.get("pose")
    if variant not in VARIANT_POSE:
        problems.append(f"compare.variant must be one of {sorted(VARIANT_POSE)}")
    elif pose != VARIANT_POSE[variant]:
        problems.append(f"compare.pose {pose!r} does not match compare.variant {variant!r} "
                        f"(expected {VARIANT_POSE[variant]!r})")
    allow_apose = cmp_.get("allow_apose") is True
    if variant == "master" and not allow_apose:
        problems.append("compare.variant master renders the A-pose master: refused unless compare.allow_apose is true "
                        "(only for characters whose reference views are A-pose)")
    fidx_path = os.path.join(cdir, "references", "annotations", "fidelity_index.json")
    ref_variant = load_json(fidx_path).get("render_variant", "master") if os.path.exists(fidx_path) else None
    if ref_variant and variant in VARIANT_POSE and variant != ref_variant and cmp_.get("allow_variant_mismatch") is not True:
        problems.append(f"compare.variant {variant!r} differs from the variant the references match "
                        f"({ref_variant!r}, fidelity_index.json): refused unless compare.allow_variant_mismatch is true")
    res["compare"] = {"variant": variant, "pose": pose, "allow_apose": allow_apose,
                      "allow_variant_mismatch": cmp_.get("allow_variant_mismatch") is True,
                      "reference_variant": ref_variant}

    # baseline (published) and candidate
    base = recipe.get("baseline") or {}
    if "version" not in base:
        problems.append("baseline: give the published baseline version (baseline.version)")
        bcol = None
    else:
        bcol = resolve_column(root, cid, "baseline", {"version": base["version"], "label": base.get("label")},
                              variant, allow_apose, problems)
        if bcol and bcol.get("approved_pointer") != bcol.get("version") and base.get("allow_not_current") is not True:
            problems.append(f"baseline: {bcol['version']} is not the current approved version "
                            f"({bcol.get('approved_pointer')}); set baseline.allow_not_current to compare against it")
    ccol = resolve_column(root, cid, "candidate", recipe.get("candidate"), variant, allow_apose, problems)
    res["columns"] = [c for c in (bcol, ccol) if c]

    # cameras and rows
    cams = recipe.get("cameras") or {}
    ri_path = os.path.join(cdir, "references", "reference_index.json")
    ref_index = load_json(ri_path) if os.path.exists(ri_path) else {"views": []}
    ref_views = {v["id"]: v for v in ref_index.get("views", [])}
    framing = cams.get("framing") or {}
    for f in ("body", "face"):
        fr = framing.get(f)
        if not (isinstance(fr, dict) and isinstance(fr.get("target"), list) and len(fr["target"]) == 3
                and float(fr.get("frame_height_m", 0)) > 0 and float(fr.get("aspect", 0)) > 0):
            problems.append(f"cameras.framing.{f}: needs target [x, y, z], frame_height_m > 0 and aspect > 0")
    lens, elev = cams.get("lens_mm", 70.0), cams.get("elevation_deg")
    if not isinstance(elev, (int, float)):
        problems.append("cameras.elevation_deg: required (one elevation for every view: identical cameras)")
    rows = cams.get("rows") or {}
    views, refs = [], {}
    missing_rows = [r for r, _, _ in ROWS if r not in rows]
    if missing_rows:
        problems.append("cameras.rows: missing " + ", ".join(missing_rows))
    for r, label, kind in ROWS:
        row = rows.get(r)
        if not isinstance(row, dict):
            continue
        yaw = row.get("yaw_deg")
        ref = None
        if "reference_view" in row:
            rv = ref_views.get(row["reference_view"])
            if rv is None:
                problems.append(f"cameras.rows.{r}: reference view {row['reference_view']} not in reference_index.json")
            else:
                if yaw is None:
                    yaw = rv.get("yaw_deg")
                elif abs(float(yaw) - float(rv.get("yaw_deg", yaw))) > 1e-6:
                    problems.append(f"cameras.rows.{r}: yaw_deg {yaw} differs from the reference yaw "
                                    f"{rv.get('yaw_deg')} of {row['reference_view']}")
                ref = resolve_reference_image(root, cid, {"file": f"views/{row['reference_view']}.png",
                                                          "crop": row.get("crop"), "label": row["reference_view"]},
                                              ref_index, problems, f"cameras.rows.{r}")
        elif "reference" in row:
            ref = resolve_reference_image(root, cid, row["reference"], ref_index, problems, f"cameras.rows.{r}")
        else:
            problems.append(f"cameras.rows.{r}: give reference_view (a reference_index.json id) or reference")
        if not isinstance(yaw, (int, float)):
            problems.append(f"cameras.rows.{r}: no yaw (give yaw_deg or a reference_view)")
            continue
        fr = framing.get(kind) or {}
        views.append({"name": r, "label": label, "framing": kind, "yaw_deg": float(yaw),
                      "elevation_deg": float(elev) if isinstance(elev, (int, float)) else 0.0,
                      "target": fr.get("target"), "frame_height_m": fr.get("frame_height_m"),
                      "aspect": fr.get("aspect")})
        refs[r] = ref
    res["cameras"] = {"lens_mm": float(lens), "sensor_mm": float(cams.get("sensor_mm", 36.0)), "views": views}
    res["references"] = refs

    # light, render, preview
    light = (recipe.get("light") or {}).get("calibration")
    try:
        names = list(load_json(os.path.join(root, os.path.relpath(CALIBRATION, ROOT)))["profiles"])
    except (OSError, ValueError, KeyError, TypeError):
        names = None
    if not light or (names is not None and light not in names):
        problems.append(f"light.calibration: unknown light rig {light!r} (pipeline/charsys/render_calibration.json)")
    res["light"] = {"calibration": light}
    rnd, pre = recipe.get("render") or {}, recipe.get("preview") or {}
    if rnd.get("engine", "cycles") != "cycles":
        problems.append("render.engine must be cycles (the strict sheet is a Cycles render)")
    if not (isinstance(rnd.get("samples"), int) and 1 <= rnd["samples"] <= 1024):
        problems.append("render.samples: integer 1..1024")
    if not (isinstance(rnd.get("px"), int) and 64 <= rnd["px"] <= 1024):
        problems.append("render.px: integer 64..1024 (image width)")
    if pre.get("engine", "cycles") not in ("cycles", "workbench"):
        problems.append("preview.engine must be cycles (low samples) or workbench")
    if not (isinstance(pre.get("samples", 1), int) and 1 <= pre.get("samples", 1) <= PREVIEW_MAX_SAMPLES):
        problems.append(f"preview.samples: integer 1..{PREVIEW_MAX_SAMPLES} (the preview must stay cheap)")
    if not (isinstance(pre.get("px", 120), int) and 32 <= pre.get("px", 120) <= PREVIEW_MAX_PX):
        problems.append(f"preview.px: integer 32..{PREVIEW_MAX_PX} (the preview must stay cheap)")
    res["render"] = {"engine": "cycles", "samples": rnd.get("samples"), "px": rnd.get("px")}
    res["preview"] = {"engine": pre.get("engine", "cycles"), "samples": pre.get("samples", 1), "px": pre.get("px", 120)}

    # optional AI target column
    ai = recipe.get("ai_target")
    if ai is not None:
        imgs = {}
        for r, ref in (ai.get("images") or {}).items():
            if r not in rows:
                problems.append(f"ai_target.images.{r}: unknown row")
                continue
            imgs[r] = resolve_reference_image(root, cid, ref, ref_index, problems, f"ai_target.images.{r}")
        res["ai_target"] = {"label": "AI target", "images": imgs}
    if problems:
        raise RecipeError(problems)
    return res


# ---------------------------------------------------------------- running


def default_out(recipe_path):
    return os.path.join(ROOT, "review_out", os.path.splitext(os.path.basename(recipe_path))[0])


def record(out, recipe, resolved, extra_name=None, extra=None):
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "recipe.json"), "w") as f:
        json.dump(recipe, f, indent=1)
    with open(os.path.join(out, "recipe.resolved.json"), "w") as f:
        json.dump(resolved, f, indent=1)
    if extra_name:
        with open(os.path.join(out, extra_name), "w") as f:
            json.dump(extra, f, indent=1)


def log_line(out, text):
    os.makedirs(out, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(os.path.join(out, "log.txt"), "a") as f:
        f.write(f"{stamp} {text}\n")
    print(text)


def run_blender(exe, script, args, log):
    cmd = [exe, "-b", "--factory-startup", "-P", script, "--"] + [str(a) for a in args]
    with open(log, "a") as f:
        f.write("$ " + " ".join(cmd) + "\n")
        f.flush()
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=ROOT)
    if r.returncode != 0:
        raise SystemExit(f"Blender step failed ({os.path.basename(script)}), see {log}")


def blends_for(resolved, out, exe, log):
    """Render inputs per column; spec candidates are built once into <out>/build/<tag> (reused when present)."""
    cols = []
    for c in resolved["columns"]:
        if c["kind"] == "spec":
            bdir = os.path.join(out, "build", c["tag"])
            variant = resolved["compare"]["variant"]
            want = os.path.join(bdir, f"{resolved['character']}_{variant}.blend")
            if not os.path.exists(want):
                args = ["--spec", os.path.join(ROOT, c["spec"]), "--out", bdir, "--no-glb"]
                if variant == "master":
                    args.append("--no-compare")
                for o in c["overrides"]:
                    args += ["--override", os.path.join(ROOT, o)]
                run_blender(exe, BUILDER, args, log)
            if not os.path.exists(want):
                raise SystemExit(f"build of {c['spec']} produced no {os.path.basename(want)} "
                                 "(no fallback to another variant)")
            blend = want
        else:
            blend = os.path.join(ROOT, c["blend"])
        cols.append({"tag": c["tag"], "blend": blend, "comparison_pose": c.get("comparison_pose")})
    return cols


def pose_problems(resolved, result):
    """Refuse renders whose arm pose does not match the compare variant (the A-pose evidence failure of T-080)."""
    want = resolved["compare"]["pose"]
    bad = []
    for tag, info in result.get("columns", {}).items():
        angles = list((info.get("arm_angle_from_down_deg") or {}).values())
        if not angles:
            bad.append(f"{tag}: no DEF-upper_arm bones, pose cannot be checked")
            continue
        worst = max(angles)
        if want == "arms_down" and worst > ARMS_DOWN_MAX_DEG:
            bad.append(f"{tag}: upper arms {worst:.0f} deg from down, an A-pose (compare variant needs <= "
                       f"{ARMS_DOWN_MAX_DEG:.0f})")
        if want == "apose" and min(angles) < APOSE_MIN_DEG:
            bad.append(f"{tag}: upper arms {min(angles):.0f} deg from down, not the A-pose master")
    return bad


def render_job(resolved, cols, out, settings):
    return {"out": out, "engine": settings["engine"], "samples": settings["samples"], "px": settings["px"],
            "lens_mm": resolved["cameras"]["lens_mm"], "sensor_mm": resolved["cameras"]["sensor_mm"],
            "calibration": resolved["light"]["calibration"], "columns": cols,
            "views": [{k: v[k] for k in ("name", "yaw_deg", "elevation_deg", "target", "frame_height_m", "aspect")}
                      for v in resolved["cameras"]["views"]]}


def render(resolved, exe, out, settings, log):
    cols = blends_for(resolved, out, exe, log)
    rdir = os.path.join(out, "renders")
    if os.path.isdir(rdir):
        shutil.rmtree(rdir)
    job = render_job(resolved, cols, rdir, settings)
    os.makedirs(out, exist_ok=True)
    jpath = os.path.join(out, "render_job.json")
    with open(jpath, "w") as f:
        json.dump(job, f, indent=1)
    run_blender(exe, RENDER_SIDE, [jpath], log)
    return rdir, load_json(os.path.join(rdir, "render_result.json"))


def preview_record_ok(out, resolved):
    """-> (ok, reason) for the preview record of this exact recipe."""
    p = os.path.join(out, "preview", "preview.json")
    if not os.path.exists(p):
        return False, f"no preview recorded ({os.path.relpath(p, ROOT) if p.startswith(ROOT) else p})"
    try:
        rec = load_json(p)
    except (OSError, ValueError):
        return False, "preview record unreadable"
    if rec.get("recipe_sha256") != resolved["recipe_sha256"]:
        return False, "the preview was made for a different recipe (recipe changed since); run preview again"
    if rec.get("status") != "pass":
        return False, "the preview did not pass: " + "; ".join(rec.get("problems", []))
    return True, "preview " + rec.get("at", "")


def cmd_validate(a):
    recipe = load_json(a.recipe)
    resolved = validate(recipe)
    print(json.dumps({"ok": True, "recipe_sha256": resolved["recipe_sha256"],
                      "columns": [c["label"] for c in resolved["columns"]],
                      "variant": resolved["compare"]["variant"]}, indent=1))


def cmd_preview(a):
    import strict_sheet as SH  # noqa: E402 (PIL only when images are made)
    recipe = load_json(a.recipe)
    resolved = validate(recipe)
    out = os.path.abspath(a.out or default_out(a.recipe))
    pdir = os.path.join(out, "preview")
    os.makedirs(pdir, exist_ok=True)
    log = os.path.join(pdir, "blender.log")
    open(log, "w").close()
    log_line(out, f"preview start: recipe {resolved['recipe_sha256'][:12]} {resolved['preview']}")
    rdir, result = render(resolved, a.blender, pdir, resolved["preview"], log)
    problems = pose_problems(resolved, result)
    SH.make_sheet(resolved, rdir, os.path.join(pdir, "preview.jpg"), title_note="PREVIEW (cheap first frame)",
                  max_px=1024)
    rec = {"recipe_sha256": resolved["recipe_sha256"], "status": "fail" if problems else "pass",
           "problems": problems, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "settings": resolved["preview"], "render_result": result}
    record(pdir, recipe, resolved, "preview.json", rec)
    log_line(out, f"preview {rec['status']}: {pdir}/preview.jpg" + (" | " + "; ".join(problems) if problems else ""))
    if problems:
        raise SystemExit("preview refused:\n  - " + "\n  - ".join(problems))


def cmd_sheet(a):
    import strict_sheet as SH  # noqa: E402
    recipe = load_json(a.recipe)
    resolved = validate(recipe)
    out = os.path.abspath(a.out or default_out(a.recipe))
    ok, why = preview_record_ok(out, resolved)
    override = None
    if not ok:
        if not a.skip_preview:
            raise SystemExit(f"sheet refused: {why}. Run `recipe.py preview` first and look at preview.jpg "
                             "(override: --skip-preview \"<reason>\", which is logged).")
        override = {"reason": a.skip_preview, "preview_state": why}
        log_line(out, f"PREVIEW OVERRIDE: sheet started without a passing preview ({why}); reason: {a.skip_preview}")
    log = os.path.join(out, "blender.log")
    open(log, "w").close()
    log_line(out, f"sheet start: recipe {resolved['recipe_sha256'][:12]} {resolved['render']}")
    rdir, result = render(resolved, a.blender, out, resolved["render"], log)
    problems = pose_problems(resolved, result)
    if problems:
        log_line(out, "sheet refused after render: " + "; ".join(problems))
        raise SystemExit("sheet refused:\n  - " + "\n  - ".join(problems))
    path = os.path.join(out, a.name)
    size = SH.make_sheet(resolved, rdir, path, max_px=SHEET_MAX_PX)
    rec = {"recipe_sha256": resolved["recipe_sha256"], "sheet": a.name, "size": list(size),
           "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "preview": why if ok else None, "preview_override": override, "render_result": result}
    record(out, recipe, resolved, "sheet.json", rec)
    log_line(out, f"sheet written: {path} {size[0]}x{size[1]}")


def main(argv=None):
    sys.path.insert(0, HERE)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("recipe")
    for name in ("preview", "sheet"):
        p = sub.add_parser(name)
        p.add_argument("recipe")
        p.add_argument("--blender", default="blender")
        p.add_argument("--out", default="")
        if name == "sheet":
            p.add_argument("--skip-preview", default="", metavar="REASON",
                           help="start the long render without a passing preview (logged)")
            p.add_argument("--name", default="sheet.jpg")
    a = ap.parse_args(argv)
    try:
        {"validate": cmd_validate, "preview": cmd_preview, "sheet": cmd_sheet}[a.cmd](a)
    except RecipeError as e:
        raise SystemExit(str(e))


if __name__ == "__main__":
    main()
