# T-062: animation evaluations use the current approved character versions

Branch `t-062-claude-current-cast` (from `origin/staging`; `origin/staging` merged before the gate). Implementer report.

## 1. Task and objective
Owner, 2026-11-17: "ensure future animation evaluations also use the latest approved character versions so we can
assess the actual combined quality." Make `run_shot` resolve a cast reference `"current"`, provide shared evaluation
shots that use it, and stop new evidence from pinning old versions (fast-tier gate check).

## 2. Result: complete (AC1–AC4), with the open points in §8

## 3. Files changed
| File | Purpose |
| --- | --- |
| `pipeline/production/run_shot.py` | `current_source()` / `cast_source()`: cast entry `{"character_id": "<id>", "version": "current"}` resolves from `docs/evaluation/characters/fidelity_baseline.json`; resolved version and inputs recorded in `run_shot.json`, `prepare.json`, `cast.json` |
| `pipeline/production/tests/test_run_shot_current.py` (new) | 36 fast checks (no Blender): resolver = regression config, resolution rules, `prepare()` reports (fake Blender), cast-check rules, repository cast check |
| `tools/check_cast.py` (new) | The cast check (rules in §4) |
| `tools/check_all.py` | One hook line: runs `test_run_shot_current.py` (incl. the repository cast check) in the "Python tests" step (no new summary line, so T-061's line still fits in the 10-line summary) |
| `content/scenes/eval/make_eval_shots.py` (new) | Generates the evaluation shots from reviewed source shots, cast replaced by `"current"`; `--check` reports stale files |
| `content/scenes/eval/{idle,walk,reach_touch_wave,wave,handover,emotions}/shot.scene.json` (new) | The six shared evaluation shots |

Documentation: `docs/process/GATE.md` (§1.1 cast check, exemptions), this folder (`README.md`,
`old_vs_current_f90.png`, `current_f90.png`, `run_shot.json` of the proof run).

## 4. What was implemented
**Cast `"current"` (AC1).** `{"character_id": "<id>", "version": "current"}` → the fidelity baseline's entry for that
id (`build` spec + `overrides`), the same list and the same version rule as the all-character regression
(`tools/regression/tiers.py character_config`: last `metadata.spec_version` of spec and overrides). If
`assets/characters/<id>/versions/<version>/manifest.json` exists the published master is used (manifest-checked as
before); otherwise the master is built from spec + overrides with the same cache key as an explicit spec cast (so
caches are shared). Refused: unknown id, missing build input, a baseline spec whose identity is another character,
`"version"` values other than `"current"` without an explicit source. `run_shot.json` per cast entry gets `version`
and `resolved` (`from`, `character_id`, `version`, `spec`, `overrides`, `version_dir` if published, `baseline`), and
`status` reads e.g. `current 1.1.0 (unpublished build from spec …)`. Explicit casts are unchanged byte for byte
(same keys in `run_shot.json`, same `cast.json`), so existing shots and their caches are not touched.

Today the baseline resolves to **boy_yellow_hoodie 1.1.0** (spec + `boy_yellow_hoodie.1.1.0.override.json`,
unpublished → built) and **girl_auburn_bun_glasses 0.9.0** (spec, unpublished → built). The task brief says girl
0.10.0; staging's fidelity baseline and spec say 0.9.0, so 0.9.0 is what "current" gives. When 0.10.0 lands in the
baseline, every evaluation shot uses it without an edit.

**Evaluation shots (AC2)** in `content/scenes/eval/`, each derived from a reviewed shot (staging, camera, actions kept):
idle (from e906, look actions only, auto idle + blinks, 60 frames), walk (e000), reach_touch_wave (T-045 "after",
body mechanics on), wave (e906), handover (e905), emotions (e902, full emotion sequence). Every cast entry is
`"current"` for both built characters. The third character (`girl_white_hair_blue_dress`) has references only and no
fidelity-baseline entry; the check requires every baseline character to appear in an evaluation shot, so the task
that makes it buildable must add it (rerun `make_eval_shots.py` after adding it to a source shot or to the generator).

**Cast check (AC3)** `tools/check_cast.py`: evaluation shots must use `"current"` literally; new
`docs/evaluation/**/shot*.scene.json` (added since the merge base with `origin/staging`, plus untracked) may use
`"current"` or an explicit source of the current version; any other pinned version fails unless the cast entry has a
non-empty `"legacy_reason"`. Exempt and documented in GATE.md §1.1: frozen `tests/data` engine packages, and shots that
existed before T-062 (`episodes/**`, earlier evidence). It runs in the fast tier via the one `check_all.py` hook line.

## 5. Tests executed
- `python3 pipeline/production/tests/test_run_shot_current.py`: 36 PASS, 0 FAIL.
- `python3 tools/check_cast.py`: PASS, 6 shots checked (base origin/staging).
- `python3 content/scenes/eval/make_eval_shots.py --check`: up to date.
- `python3 tools/check_doc_links.py`: exit 0.
- Proof run: `python3 pipeline/production/run_shot.py --shot content/scenes/eval/reach_touch_wave/shot.scene.json
  --blender <bpy 5.3.0 wrapper> --frames 90-90` → ok (build boy 8.9 s, girl 101.9 s, exports, bake 1.3 s, render 11.6 s).
- Gate: see §5.1.

### 5.1 Gate
Local: `python3 tools/check_all.py --base origin/main --task T-062 --blender <bpy wrapper>` on the branch with
`origin/staging` merged (full tier, 27 min):
```
PASS Frozen assets
FAIL Guarded paths: REQUIRES SUPERVISOR APPROVAL: pipeline/production/tests/test_run_shot_current.py, tools/check_all.py
FAIL Write-set: T-062 changes files outside its claim: tools/check_all.py
PASS Shared-systems lint
PASS C++ build
PASS C++ tests
PASS Python tests and links
PASS Blender tier: full tier; regression boy_yellow_hoodie PASS (fidelity 64.07), girl_auburn_bun_glasses PASS (fidelity 65.49), girl_white_hair_blue_dress PASS
```
GitHub "Quality gate" run 44162440805 (commit 5e19d01, trial merge into staging): the same: every line PASS (full
regression: boy PASS 64.08, girl PASS 65.46, third character PASS) except Guarded paths and Write-set (same files), and
therefore "Merge status: clean, tests FAIL after merge". **"Gate verdict" is red** for those two reasons only; it
turns green with `Supervisor-Approved:` trailers for the two guarded files and `tools/check_all.py` added to the T-062
write-set in OWNERSHIP.md (both Supervisor actions, §8.1).

Blender that ran: bpy 5.3.0 module (Python 3.13) through `tools/bpy_blender.py` (no Blender binary here). C++ build
with OIDN 2.3.3 prebuilt.

Not tested: a full multi-frame render of the evaluation shots (render budget ≤ 1); `prepare` of the other five
evaluation shots with real Blender (they resolve the same two masters as the proof shot; their cast is checked by the
cast check).

## 6. Baselines
No frozen file, spec, override, asset, engine file or existing shot changed (`git diff --stat origin/staging` lists
only the files in §3). Explicit casts produce the same `run_shot.json` keys and `cast.json` bytes as before (tested).
Frozen-assets line of the gate: PASS (locally and in CI). Unchanged-character guard: all characters PASS.

## 7. Visual result (AC4)
`old_vs_current_f90.png`: frame 90 (wave) of the reach/touch/wave shot, Cycles 16 samples + denoiser (OIDN), 640×360.
Left: the T-045 "after" render (boy **1.0.0** published, girl spec 0.9.0), cut from `../T-045/t045_before_after.mp4`.
Right: `content/scenes/eval/reach_touch_wave` with cast `"current"` (boy **1.1.0**, girl 0.9.0), one new render.
The two are almost identical: boy 1.1.0 differs from 1.0.0 only in eyelid tracking (lids follow the gaze, T-014),
and the girl was already on her current spec in T-045. This is expected; the point of the change is that future evaluations
pick up new approved versions (boy 2.0, girl 0.10.0, hair v3) automatically.

## 8. Problems, limitations, questions
1. **Guarded paths:** `tools/check_all.py` (hook line) and `pipeline/production/tests/test_run_shot_current.py` (a
   `tests/` file) are guarded and need `Supervisor-Approved:` trailers. The **Write-set** check also flags
   `tools/check_all.py`: OWNERSHIP lists it under T-062's *depends on (stable)*, not its write-set, while the task asks
   for the hook line. I did not edit OWNERSHIP.md (Supervisor file). Please add it to the T-062 claim or approve.
2. Girl version: brief says 0.10.0, the baseline on staging says 0.9.0 (§4).
3. "Current" = the fidelity baseline's version, which is not necessarily *owner-approved* in the asset store (both
   current versions are unpublished). This is how the task defines it; `status` in `run_shot.json` says so.
4. The rule "every baseline character appears in an evaluation shot" will make the task that adds a third character
   to the fidelity baseline also update `content/scenes/eval/` (intended; say if you prefer a warning).
5. Existing episodes still pin old versions (exempt by design); they are not migrated.

## 9. Commits
Branch `t-062-claude-current-cast`; commits listed in the READY line in `RELAY_LOG.md`.

## 10. Resource use
Token usage: not available. One render (1 frame). One full local gate run.
