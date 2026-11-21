# T-178: one release rule in place of per-feature guards (T-176 proposal 5)

Status: **partial**. Rule, manifest, version_switch step, new tests and this coverage table are done. Removing the
old "no spec uses X" checks waits for the owner's approval typed in the implementer session (brief, step 3). No
existing test has been changed yet.

## What
- `pipeline/charsys/release_rule.py`: the rule. `FEATURES` = detector + scope for each opt-in feature, copied from the
  old guards. A file that uses a feature passes only if its `(character, version)`, read from its path, is listed for
  that feature in the manifest with a decision ref. The decision ref must name a file that mentions the version.
  Nothing is exempt for a base spec or unversioned file, an unlisted version, a feature the entry does not list, or
  when the manifest has any problem.
- `pipeline/charsys/release_manifest.json`: 9 entries, one per published version that uses opt-in features today:
  boy 2.0.0–2.3.0, girl 0.11.0–0.14.0, third 0.1.0. The decision refs come from each version's store approval. It
  covers all 14 `owner_approved_candidates.json` triples. Behaviour is unchanged: `release_rule.py` → 0 violations.
- `tools/version_switch.py` step 6b writes or replaces the entry in the switch run (publish, approve and
  approve-published modes). It runs only when the version uses an opt-in feature, and then the manifest is a
  predicted write, so the claim must cover it and the trailer is printed. `test_release_rule.py` is in
  `AFFECTED_TESTS`.
- `tools/guarded_paths.txt`: `pipeline/charsys/release_manifest*` and `pipeline/charsys/release_rule*.py` are now
  guarded.
- `tools/check_all.py`: registers `test_release_rule.py`. `docs/process/ASSET_STORE.md`: the rule section.
- `tools/shared_character_allowlist.txt` is not a feature allowlist (it lists character names in shared code for
  check_all's lint), so it stays as it is.

## Scope changes (all stricter, none weaker)
- groom/3, groom/2, face_generic/3 (`spec_top`): the old guards checked only base and unversioned files (r4, v3_r2/r3)
  or two fixed published specs (face_v3/v3b). The rule now also requires the versioned specs and the stored versions
  to be listed. Candidate subfolders are out of scope, as before.
- lash_curve / closed_fill: `test_face_r5` scanned only `*/spec*` folders. The rule adds `versions/<v>/`.
- groom/3 covers every character (r4 covered boy and girl only).
- Every entry now needs a decision ref whose file mentions the version. The old rule asked for this only for current
  versions (`current_decision`). Entries for unpublished versions are refused.
- Limitation: face_v3 read the *resolved* spec (`spec.load`). The rule reads files, so a version that inherits
  face_generic/3 is caught through its base or versioned file, and published files stay byte-immutable.

## Coverage: old guard → new check
New tests are all in `pipeline/charsys/tests/test_release_rule.py` (TRR). "neg" = the `test_negatives` per-feature
loop, "det" = `test_detectors_and_scopes`.

| old guard (file::check) | new check (file::test) |
|---|---|
| test_hair_r4::no base spec or override outside candidates/ pins groom/3 | release_rule `groom/3` (spec_top); TRR det "groom/3 #0: detected in the base spec"; neg "groom/3: the base spec using it fails"; "groom/3: an unlisted version using it fails" |
| test_hair_r5::owner-approved candidate allowlist is valid (T-154) | TRR "the release manifest validates"; malformed-manifest cases |
| test_hair_r5::no file under assets/characters pins groom/4 (except listed) | `groom/4` (characters scope); det groom/4 #0/#1 (generators / override.generators); det "groom/4, groom/5, body.hands: every file under assets/characters"; neg groom/4 unlisted / base / not-listed-for; "the repository passes the release rule" |
| test_hair_r6::allowlist valid; no file pins groom/5 | `groom/5` (text `"groom/5"`, characters); det groom/5 #0/#1; neg groom/5 unlisted / base |
| test_hair_r6::negative: a non-listed file pinning groom/5 still fails (98.7.6 spec, 2.2.0 stored) | neg "groom/5: an unlisted version using it fails"; "a feature listed for another character's version does not cover this one" (listed version, not for groom/5) |
| test_hair_v3_r2::T-070 published (base) spec does not pin groom/2 | `groom/2` (spec_top); det groom/2 #0/#1 (generators.groom, hair.generator); neg "groom/2: the base spec using it fails" |
| test_hair_v3_r3::T-079 published (base) spec does not pin groom/2 | same as the row above |
| test_hands_r2::allowlist valid; no spec or candidate in assets/ sets body.hands | `body.hands` (characters, root or override); det body.hands #0/#1; neg body.hands unlisted / base / not-listed-for |
| test_face_r5::allowlist valid (T-154, R3) | "the release manifest validates"; malformed cases |
| test_face_r5::no spec under assets/ opts into lash_curve | `lash_curve` (spec_dirs + versions); det lash_curve #0; det "lash_curve, closed_fill: spec folders … and stored versions"; neg lash_curve ×3 |
| test_face_r5::no spec opts into lid yaw, sink_m, shell_occlusion_tint, socket.closed_fill (the closed_fill guard) | `closed_fill`; det closed_fill #0–#4 (one sample per key); neg closed_fill ×3 |
| test_face_r5::negative: non-listed spec (98.7.6; listed version without closed_fill) still fails | neg "closed_fill: an unlisted version using it fails"; "closed_fill: a listed version using it while not listed for it fails" |
| test_face_v3::published boy 2.0.0 / girl 0.11.0 spec still pins face_generic/2 | `face_generic/3` (spec_top): 2.0.0 / 0.11.0 are listed for groom/2 only; neg "face_generic/3: a listed version using it while not listed for it fails"; "each entry lists exactly the features the version's files use" |
| test_face_v3b::same check through V3.CASES (T-089b) | same as the row above |
| test_face_t168::allowlist valid; no spec under assets/ uses cheek_pad_top_fade_m / upturned nose | `t168_face` (assets minus references); det t168 #0/#1; det "t168_face: every file under assets/ except references"; neg t168 ×3 |
| test_face_t168::negative: non-listed spec (98.7.6; girl 0.14.0 listed without t168) fails | neg "t168_face: an unlisted version using it fails"; "… a listed version using it while not listed for it fails" |
| test_guard_allowlist::the allowlist validates; every entry names a decision and a date | "the release manifest validates"; "every entry names a decision ref whose file mentions the version" |
| test_guard_allowlist::path → candidate; a path without a readable version is never exempt | det "path -> version: …"; neg "<feature>: the base spec using it fails" |
| test_guard_allowlist::a listed candidate is exempt for its feature | neg "listed versions using their listed features pass" |
| test_guard_allowlist::a listed id with a different feature is rejected (per feature) | neg "<feature>: a listed version using it while not listed for it fails"; "a feature listed for another character's version does not cover this one" |
| test_guard_allowlist::an unlisted candidate / version is rejected (per feature) | neg "<feature>: an unlisted version using it fails" (all 9 features) |
| test_guard_allowlist::an unlisted character is rejected (per feature) | neg "an unlisted character's versioned spec using an opt-in fails"; manifest "unknown character" refused |
| test_guard_allowlist::split keeps the unlisted path in the failure list | `violations()` lists every failing (path, feature); neg cases assert the exact path |
| test_guard_allowlist::malformed entry (missing owner_decision / date, bad date) fails and exempts nothing | "manifest entry ['decision_ref'] -> refused (missing)" (also `None`, no date, file not found); "['date'] bad date" |
| test_guard_allowlist::unknown or wildcard feature; wildcard version; no entries list | "['features'] unknown feature" (`groom/*`); "['version'] bad version" (`*`); "malformed manifest (releases list)"; schema; listed twice; missing / unreadable manifest |
| test_guard_allowlist::current version without / with empty current_decision refused | stricter: *every* entry needs a decision ref whose file mentions the version ("… -> refused (does not mention)", "not found", "missing"); unpublished version refused |
| test_guard_allowlist::current version WITH named decision exempt for that feature only | "current <id> <ver> is listed with its features" (real repo); neg not-listed-for |
| test_guard_allowlist::every entry naming the current version carries a current_decision | "every entry names a decision ref whose file mentions the version" |
| owner_approved_candidates.json (14 entries) | `release_manifest.json`; TRR "every owner_approved_candidates.json entry (14) is listed in the manifest" (runs while the old file exists; all 14 covered at b531ab5) |
| (new) manifest edits need the guard trailer | TRR "pipeline/charsys/release_manifest.json is a guarded path"; "a manifest change without a Supervisor-Approved trailer fails the guarded-paths check" (`check_all.check_guarded`) |
| (new) version_switch writes the entry | TRR "switch dry run predicts the manifest write and its trailer"; "switch writes the version's entry … in the same run"; "a switch whose claim does not cover the manifest is refused" |

Kept as they are: byte-immutability (`test_asset_store_guard.py`, `tools/check_assets.py`),
`tools/frozen_manifest.txt`, goldens, version_switch's decision ref check, and every build, weight and geometry
assertion in the files above. After approval, only the "nobody uses X" checks and the allowlist plumbing come out;
`test_guard_allowlist.py` and `owner_approved_candidates.json` are deleted.

## Tests (this stage)
- `python3 pipeline/charsys/tests/test_release_rule.py` → 130/130 PASS
- `python3 pipeline/charsys/release_rule.py` → OK, 0 violations, 0 manifest problems
- `python3 tools/tests/test_version_switch.py` (unchanged) → 96/96 PASS
- Not run yet: full `tools/check_all.py` and the branch gate. They run after the old-test edits.
