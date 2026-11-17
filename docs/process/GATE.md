# Quality gate, claims, regression and backups (T-041)

How the delivery plan's safety rules ([DELIVERY_PLAN.md](DELIVERY_PLAN.md) §3, §5, §8.1) are enforced. Everything
here runs in `tools/check_all.py` (locally) and in `.github/workflows/checks.yml` / `backup.yml` (GitHub).

## 1. The gate (`tools/check_all.py`)

```
python tools/check_all.py --base origin/staging [--blender <blender>] [--task T-NNN] [--full]
```

At most ten summary lines; details in `build/check-all/check_all.json` and `build/check-all/logs/`.

| Line | What it checks |
| --- | --- |
| Frozen assets | `tools/frozen_manifest.txt` blob IDs and frozen scopes |
| Guarded paths | changes to `tools/guarded_paths.txt` entries need a `Supervisor-Approved: <path>` trailer |
| Write-set | a task branch (`t-NNN-…`) changes only files inside its claim in [OWNERSHIP.md](OWNERSHIP.md) (diff vs the merge base with `origin/staging`); other branches: not applicable |
| Shared-systems lint | no new character names in shared code |
| C++ build | CMake + Ninja (OIDN 2.3.3 prebuilt via `PLUSH_OIDN_ROOT`) |
| C++ tests | CTest (incl. the frozen image regressions) and `plush_tests` |
| Python tests and links | Python unit tests (incl. `tools/regression/tests/test_gate_tools.py`, `tools/cleanup/run_tests.py` once present) and Markdown links |
| Blender tier | fast tier: reported as "not required: fast tier"; full tier: verify_charsys, determinism, export, face, hair/groom, garment, material presets **and the all-character regression** (§3) |
| Merge status | CI trial merge |

The Blender tier is never skipped silently: on the fast tier it says so; on the full tier a missing Blender is a
FAIL; on Windows CI it states that it runs on the linux job.

## 2. Tiers (`tools/regression_paths.txt`, guarded)

`<fast|full> <glob>` rules, first match wins, **unknown paths are full**, one full path makes the change set full.
Full: `pipeline/**`, `assets/**`, `content/**`, `engine/**`, `apps/render-cli/**`, `tests/regression/**`,
`tests/data/**`, the regression machinery itself, fidelity tools, references. Fast: isolated C++ tests, studio UI,
build configuration, `tools/**`, `.github/**`, `docs/**`, root Markdown. A new shared module is added once, as
`full`, above any broader `fast` rule. `python tools/regression/tiers.py --base <ref>` prints the decision.
`--full` raises the tier; nothing lowers it.

## 3. Full regression and unchanged-character guard (`tools/regression/`)

```
python tools/regression/run.py --blender <blender> --out <dir> [--character <id>] [--base origin/main]
```

For **every** character folder in `assets/characters`, in parallel. A folder with a spec but no regression config
(an entry in `fidelity_baseline.json`) is a FAIL. A folder with references but no spec yet (reference intake, e.g.
`girl_white_hair_blue_dress`) is reported as "references only, not buildable yet". The steps per character: build (spec + the overrides of its current version, from `fidelity_baseline.json`), format-2 fingerprint
(0.01 mm), engine export, fixed-camera renders (`views.json`: four turnaround views + face close-up at the head
bone, 320 px, 16 samples, OIDN, seed 0, the shared render calibration), fidelity (drop > 2 points = FAIL).

Comparison ref (`--against origin/main`, CI and `check_all.py`): every character is also built from `origin/main`
(a temporary git worktree) **on the same machine** with the same measuring tools (fingerprint tool, cameras).
Builds are bit-reproducible on one machine but not across CPU families (T-041 finding: the boy's legacy
`hair_clumps` mesh differs between GitHub runners), so identity is checked against `main` built here, not against
files made elsewhere.

Approved baselines: `docs/evaluation/regression/baselines/<id>/<spec version>/` (`golden.json`,
`fingerprint.json`, `images/*.png`), guarded. With a comparison ref they are compared for information (and must not
be stale); without one (`run.py` without `--against`) the comparison against them is strict.

- **Unchanged character** (its spec/override files are not in the diff vs `--base`): must be identical to `main`
  built on this machine: fingerprint byte-equal, engine export equal (order-independent summary, see below), every
  render within the noise threshold. Any difference is a FAIL, even if it looks better. A missing or stale approved
  baseline (made from other spec inputs) is a FAIL too.
- **Changed character** (pin bump / look task, path B): differences from `main` and from the baseline are listed for
  the owner; only fidelity can fail. New baseline files come with the task (new files only) and need Supervisor
  approval.

Noise threshold (`tools/regression/render_noise_threshold.json`, guarded): measured with `run.py --noise` (every
character built and rendered twice from one commit): boy max rmse 1.7e-5, girl max rmse 0.0028 / 0.37 % changed
pixels (hair fibres). Threshold: rmse 0.006, changed pixels 0.8 % (about 2× the measured noise).

Engine export: two identical builds export the same geometry with a different triangle/vertex order and float noise
of about 1 ulp (≤ 1.1e-6), so neither `geometry.bin` bytes nor hashes of quantized positions are stable (a vertex
can land on either side of a rounding boundary; measured on the boy's `ear.L`). Against `main` built on the same
machine the two packages are compared directly: `character.json` exactly (without byte hashes), per mesh every
vertex matched within 0.01 mm, triangles equal as index sets, joints equal, weights and normals within 1e-4, other
buffers (morph targets) by count/mean/rms/min/max within 1e-5. Against a stored baseline (no package stored) only
that statistics summary is compared, for information.

## 4. File claims and integration (`tools/integrate.py`)

| Command | Effect |
| --- | --- |
| `claims --check T-NNN` | may T-NNN start? Glob-aware write-set overlap, dependency on a file another running task changes, same version bump → exit 1. `(stable)` dependencies are warnings. `claims --list` prints the table. |
| `writeset --task T-NNN` | the Write-set gate check on its own |
| `stage <branch> [--dry-run]` | trial merge into `origin/staging` in a temporary worktree, gate on the result, then a `--no-ff` merge pushed to `staging` |
| `promote [--dry-run]` | backup request for `main` (branch `archive/backup-<UTC>-main`), then fast-forward `main` to `staging` |
| `backup <branch>…` | backup request branches `archive/backup-<UTC>-<branch>` |

## 5. CI (`.github/workflows/checks.yml`)

Push to `t-*`, `integration/*`, `staging`, `main`. Jobs: **plan** (comparison base and trial-merge target: task
branches use `origin/staging`, `staging`/`integration/*` use `origin/main`; tier), **linux gate** (apt libraries,
pinned OIDN prebuilt, pinned bpy, ccache; gate on the trial merge), **regression \<character\>** (full tier only, one
job per character, in parallel; also uploads baseline candidates), **windows gate** (on `staging`/`main` pushes or
`[ci windows]` in the head commit message; vcpkg with a binary cache; C++ and Python tiers), **Gate verdict**
(combines all reports into ≤ 10 lines, fails on any FAIL, a missing report or a failed required job). Required check
for the rulesets: **Gate verdict**.

## 6. Backups (`.github/workflows/backup.yml`, plan §8.1 layers 1–2)

- **Tags:** every push to `main`/`staging` and every pushed backup request `archive/backup-<UTC>-<branch>` creates
  `backup/<UTC yyyymmddTHHMMSSZ>/<branch>` (`.github/scripts/backup_tags.py`; Actions token with `contents: write`, because
  cloud sessions cannot push tags). A tip already tagged for that branch is not tagged again. Tags are never deleted.
- **Bundle:** on every push to `main`, nightly (02:17 UTC) and on demand: bare snapshot of all remote branches and
  tags → `git bundle create --all` → `git bundle verify` → `.sha256` → restore test (mirror-clone the bundle,
  `git fsck --full`, every branch/tag SHA equal to the snapshot, then the fast tier on the restored `main`) →
  artifact for 90 days (`tools/backup_repository.py`). A failed restore test fails the workflow.
- **Release:** Sunday's nightly run (or on demand) publishes `backup-<YYYY-MM-DD>` with the bundle; the 8 newest and
  the first of every month are kept, older weekly releases lose the release entry, never the tag.
- Restore: `git clone --mirror <bundle> restored.git`, or from a tag: `git push origin backup/<…>/<branch>:refs/heads/<branch>`.
