# T-041 (+T-042) report: gate on GitHub, file claims, full regression, unchanged-character guard, durable backups

1. **Task / objective:** make the delivery plan's safety rules (§3, §5, §8.1) executable in `tools/check_all.py`
   and in GitHub CI.
2. **Result:** complete for AC1–AC7, with these limits (details in §8):
   - The GitHub gate passes every check except **Guarded paths**, which waits for the Supervisor's
     `Supervisor-Approved:` trailers (list in §6).
   - Windows CI is reported but not required until it has passed once on `staging`.
   - The backup workflow and the `stage`/`promote` pushes only run for real after merge.
3. **Branch / commits:** `t-041-claude-gate-claims`; final commit in the RELAY_LOG line.

## 3. Files changed

| Path | Purpose |
| --- | --- |
| `tools/integrate.py` (new) | `claims --check/--list` (glob-aware overlap, dependencies, version bumps), `writeset`, `stage [--dry-run]`, `promote [--dry-run]`, `backup` (backup request branches) |
| `docs/process/OWNERSHIP.md` | Claims table in a machine-readable format (Task, Lane, Branch, Write-set, Depends on, Versions bumped); rows for T-041, T-043, T-046, T-040r1, T-048 |
| `tools/regression_paths.txt` (new, guarded) | Path → fast/full rules; first match wins; unknown paths are full |
| `tools/regression/tiers.py` (new) | Tier selection, character list, build inputs and spec-input hash per character, changed-character detection |
| `tools/regression/run.py` (new) | Per character, in parallel: build, fingerprint, engine export, fixed-camera renders, fidelity. Also the comparison against approved baselines (unchanged-character guard), `--write-baseline`, `--noise` and `--gate-report` |
| `tools/regression/probe_head.py`, `views.json` (new) | Head point for the face close-up (from the spec's head bone); fixed regression cameras and render settings |
| `tools/regression/render_noise_threshold.json` (new, guarded) | Measured render noise and the recorded threshold |
| `tools/regression/tests/test_gate_tools.py` (new) | Unit tests: glob overlap, claims, write-set, tiers, the comparison rules, backup tag and release retention logic |
| `tools/check_all.py` | New checks and options (see below) |
| `tools/simulate_quality_gate.py` | Each simulation now asserts the check it targets. New simulations: claim overlap, write-set, unknown path → full, changed fingerprint → FAIL. New `--only` and `--task` options |
| `tools/backup_repository.py` | Bare snapshot of all remote branches and tags → bundle, verify, `.sha256`, restore test (all ref SHAs vs the snapshot, fsck, checkout of `main`), JSON report |
| `tools/guarded_paths.txt` | Additions only: `tools/integrate.py`, `tools/regression_paths.txt`, `tools/regression/`, `docs/evaluation/regression/baselines/` |
| `.github/workflows/checks.yml` | Jobs: plan, linux gate, regression per character, windows, Gate verdict. Pushes to `staging` added |
| `.github/workflows/backup.yml` | Backup tags; verified bundle with a restore test and the fast tier; weekly release |
| `.github/scripts/*` | `select_base.sh`, `trial_merge.sh`, `install_ci_dependencies.ps1` (`-Cpp`/`-Bpy`, cached verified downloads), `combine_check_reports.py` (verdict), `backup_tags.py`, `backup_release.py`, `show_failed_logs.py` |
| `.github/ci-dependencies.json` | Pinned OIDN 2.3.3 prebuilt binaries (linux, windows; SHA-256) and the Ubuntu package list |
| `docs/evaluation/regression/baselines/**` (new) | Baselines: boy 1.1.0, girl 0.9.0 (`golden.json`, `fingerprint.json`, `images/*.png`) |

`tools/check_all.py` changes:
- New **Write-set** check.
- The tier now comes from `tools/regression_paths.txt`; `blender_paths_changed` is gone.
- CTest and plush_tests are reported as one line, **C++ tests**.
- Python tests and doc links are reported as one line, **Python tests and links**, so the summary stays at 10 lines
  or fewer.
- Full tier: the all-character regression runs inside the Blender tier, and the fidelity run for affected
  characters is not repeated.
- New options: `--task`, `--full`, `--regression-results`, `--regression-external`, `--blender-on-other-runner`.
- `tools/cleanup/run_tests.py` (T-048) runs when it is present. This is the single line T-048 asked for.

Documentation: `docs/process/GATE.md` (new: how the gate, tiers, regression, claims, CI and backups work),
`docs/evaluation/regression/baselines/README.md`, this report.

## 4. Implementation and decisions

- **CI on Linux:** the C++ tier no longer uses vcpkg on Linux. vcpkg's glew build failed on ubuntu-24.04, so CI
  never got past it. It now uses Ubuntu packages instead: embree 4.3.0, glfw 3.3.10, glew, glm, nlohmann-json, stb
  and doctest. It also uses the pinned **OIDN 2.3.3 prebuilt**. Without OIDN, the frozen image regressions fail
  (m01 rmse 0.046 > 0.03); this is reproduced here and was already known from T-001. The build uses ccache. Pinned
  downloads (the bpy wheel and OIDN) are cached and their checksums are re-verified on every run.
- **CI structure:**
  - **plan:** chooses the base and the trial-merge target. Task branches use `origin/staging`; `staging` and
    `integration/*` use `origin/main`.
  - **linux gate**, the **regression** jobs (one per character) and **windows** run in parallel.
  - **Gate verdict:** the single required check. It fails on any FAIL line, a missing report or a failed required
    job.
  - Artifacts cannot be downloaded from cloud sessions (the proxy blocks the blob host). So failing logs are also
    printed into the job log (`show_failed_logs.py`).
- **Blender tier is never silently skipped:**
  - fast tier: "not required: fast tier";
  - full tier without Blender: FAIL ("this tier is never skipped");
  - on Windows CI: "runs on the linux gate".
- **Unchanged-character guard against stored baselines, not a rebuild of `main` on every run.** Rebuilding `main`
  would double the Blender time. The baselines are equal to `main`:
  - they are made from `main`'s spec inputs;
  - each one records the spec-input hash, so a stale baseline is a FAIL;
  - they are guarded, so changing one needs Supervisor approval.

  A character is "unchanged" when none of its spec or override files is in the diff against `--base`. CI uses
  `origin/main`.
- **Engine export comparison is order-independent.** Measured: two identical builds give the same master
  (byte-equal fingerprints). But `export_engine.py` writes a different triangle and vertex order, with float noise
  of 1.1e-6 or less (56k index values differ). So `geometry.bin` bytes cannot be compared. The summary compares:
  - `character.json` exactly (without the byte hashes);
  - per mesh, a hash of the sorted triangle set (positions at 0.01 mm) and of the sorted per-vertex joint tuples;
  - per buffer, count and mean/rms/min/max within 1e-5.

  Fixing the exporter's ordering is outside this write-set (open issue).
- **Fidelity in the regression** builds the `compare` variant (arms lowered, fur) when the character's
  `fidelity_index.json` asks for it (the boy). The first CI run without it scored the boy's A-pose master 56.61,
  a false 7.9-point drop.
- **Baseline images are stored under `images/`**: the repository `.gitignore` excludes every `renders/` folder.
- **Claims table:** a `(stable)` dependency is a warning, not a conflict. This applies to T-041 reading
  build_character's CLI while T-043 keeps it stable, and to T-048 reading backup.yml. A task branch without a row
  falls back to its task file's Write-set section.
- **Write-set check:** compares the diff against the merge base with `origin/staging`. During a trial merge it
  compares the merge result with staging. Branches that are not task branches report "not applicable".
- **Tier rules:** these are full:
  - `pipeline/**`, `assets/**`, `content/**`, `engine/**`, `apps/render-cli/**`, `tests/regression/**`,
    `tests/data/**`;
  - the regression machinery itself;
  - fidelity tools and references.

  These are fast: isolated C++ tests, studio UI, build configuration, other `tools/**`, `.github/**`, `docs/**`,
  root Markdown.
- **Backups:**
  - Tags `backup/<UTC yyyymmddTHHMMSSZ>/<branch>` are created by the workflow (`contents: write`) on every push to
    `main`/`staging`. They are also created for each backup request branch `archive/backup-<stamp>-<branch>`, which
    `integrate.py promote/backup` pushes; cloud sessions can push branches but not tags. The timestamp format
    matches the one T-048 uses.
  - The bundle job runs on every push to `main`, nightly and on demand.
  - Weekly release: Sundays. The 8 newest releases and the first release of each month are kept; old release
    entries are deleted, but tags never are (the rulesets protect `backup-*`).
- **Windows:** runs on `staging`/`main` pushes (or `[ci windows]` in the commit message), with a vcpkg binary cache
  and the OIDN prebuilt. It is reported as INFO and is not required yet, because it has never passed on GitHub
  (before this task it timed out after 120 min).

## 5. Tests executed

| What | Command | Result |
| --- | --- | --- |
| Unit tests | `python3 tools/regression/tests/test_gate_tools.py` | PASS (0 failures) |
| Claims | `python3 tools/integrate.py claims --check T-041/T-043/T-046/T-040r1/T-048` | all PASS (warnings only for `(stable)` reads) |
| Noise measurement | `python3 tools/regression/run.py --noise --blender <bpy 5.3 shim>` | fingerprints byte-equal for both characters; export summary equal; renders: boy max rmse 1.7e-5, girl max rmse 0.0028, changed pixels 0.37 % |
| Baselines + fidelity | `run.py --write-baseline --base origin/main` | boy fidelity 64.08 (baseline 64.49, drop 0.41), girl 65.48 (+0.07) |
| Cross-machine (GitHub runner vs local baselines) | CI run 44111207498 (4d3295b), regression jobs | fingerprint, engine export and fidelity PASS for both characters (renders failed only because the images were not yet committed, see §4) |
| Simulations (T-023 + T-041) | `python3 tools/simulate_quality_gate.py --task T-041`, then `--only changed_fingerprint --blender …` | all PASS: baseline, frozen file, shared character name, threshold unapproved/approved, broken C++ test, textual conflict, hidden conflict (alone / after merge), claim overlap (FAIL) / disjoint (PASS), write-set inside (PASS) / violation (FAIL), docs-only → fast, unknown path → full, changed unchanged-character fingerprint → FAIL (fingerprint and export both flag `backpack_body` after a 1 mm shift) |
| Backup | `python3 tools/backup_repository.py --remote <origin> --restore-test` | 58 branches, 349 MB bundle verified, 58 refs compared, 0 mismatches |
| Backup tags | `backup_tags.py` against a scratch bare clone | tag for push and for a backup request created and pushed; a second run on the same tip creates nothing |
| integrate dry runs | `promote --dry-run`, `backup staging --dry-run`, `writeset --task T-041` | as expected |
| Full local gate | see §5.1 | see §5.1 |
| GitHub CI | see §5.2 | see §5.2 |

Not tested:
- `stage` without `--dry-run`, `promote` without `--dry-run`, and `backup.yml` on GitHub. Each of these pushes to
  `staging`/`main` or needs a `main` push, so none can run before merge.
- The weekly release.
- Windows CI.

### 5.1 Full local gate
(filled in below)

### 5.2 GitHub CI
(filled in below)

## 6. Baselines and guarded paths

- Frozen assets unchanged: the "Frozen assets" check passes locally and on CI. CTest 4/4, including the three
  frozen image regressions, passes with OIDN.
- **Guarded paths changed: Supervisor approval needed.**
  - **Workflows and CI scripts:**
    - `.github/ci-dependencies.json`
    - `.github/workflows/checks.yml`
    - `.github/workflows/backup.yml`
    - `.github/scripts/backup_release.py`
    - `.github/scripts/backup_tags.py`
    - `.github/scripts/combine_check_reports.py`
    - `.github/scripts/install_ci_dependencies.ps1`
    - `.github/scripts/select_base.sh`
    - `.github/scripts/show_failed_logs.py`
    - `.github/scripts/trial_merge.sh`
  - **Gate tools:**
    - `tools/check_all.py`
    - `tools/simulate_quality_gate.py`
    - `tools/backup_repository.py`
    - `tools/guarded_paths.txt`
    - `tools/integrate.py`
    - `tools/regression_paths.txt`
  - **Regression tools:**
    - `tools/regression/probe_head.py`
    - `tools/regression/render_noise_threshold.json`
    - `tools/regression/run.py`
    - `tools/regression/tests/test_gate_tools.py`
    - `tools/regression/tiers.py`
    - `tools/regression/views.json`
  - **Baselines:** every file under `docs/evaluation/regression/baselines/`.
- No pipeline, engine, spec or asset file changed.

## 7. Visual results

The regression renders are not review material. They are low-sample guard images: four turnaround views and a
face close-up per character, in `docs/evaluation/regression/baselines/*/*/images/`. No character's look changed.

## 8. Problems, limitations, open questions

1. **Guarded-path trailers:** CI and the local gate show FAIL for Guarded paths until the Supervisor adds
   `Supervisor-Approved:` trailers for the list in §6.
2. **Windows CI is not proven:** it is wired up (vcpkg binary cache, OIDN prebuilt) but reported as INFO. To make
   it required once it has passed on `staging`, change `WINDOWS:` in the verdict step to
   `${{ needs.plan.outputs.windows }}`.
3. **Exporter non-determinism:** `export_engine.py` writes a non-reproducible triangle and vertex order. The guard
   works around it with an order-independent summary. A follow-up task could make the export order canonical
   (lane B).
4. **Girl render noise:** the girl's renders differ between two identical builds (rmse up to 0.0028, hair-fibre
   area), even though her geometry fingerprint is byte-equal. The noise threshold absorbs this. A follow-up could
   make it bit-identical, as T-038b did for the boy's hair.
5. **Animation regression shots** (idle, walk, wave, hand-over; plan §5.1 last column) are not part of the T-041
   acceptance criteria and are not implemented.
6. **Required status check:** once this is merged, the rulesets should require the check "Gate verdict". This is
   an owner step, because the cloud proxy blocks settings APIs.
7. **CI cost:**
   - fast tier: about 6 min on linux;
   - full tier: about 21 min wall time (linux gate about 20 min, girl regression about 11 min, boy about 2.5 min,
     all in parallel).

   The linux gate's Blender tier (garment test, verify_charsys, determinism) dominates. Per-character jobs scale
   with the number of characters at no extra wall time.
8. **Unreachable artifacts:** cloud sessions cannot download Actions artifacts (blob host blocked). Baselines were
   therefore made locally and verified on the runner, not downloaded from it.

## 10. Resource use

Token usage: not available. Repeated work:
- CI ran 4 times. The first run found the staging conflict, the second found the fidelity variant problem, the
  third found the ignored images.
- One local gate attempt hit the 10-minute foreground limit.
