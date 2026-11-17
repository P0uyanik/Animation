# T-038 character-build determinism

Date: 2026-11-16. Blender: 5.3.0 (`02f0899d78e3`), CPU build. All scratch output is under `build/t038_*`.

## Outcome

Two clean builds of each character now produce byte-identical geometry fingerprint JSON and byte-identical generated JSON reports. The boy also matches at the former 0.01 mm diagnostic grid: zero changed objects, including `hair_mass`. The girl's remaining difference is only the opaque `.blend` container bytes; its geometry and generated JSON are identical.

The legacy hair layout seeds are unchanged: boy `hair_clumps/1` seed 11 and girl `groom/1` seed 30. `hair_mass` is baked and snapped to 0.1 mm after the same 8 mm Clouds displacement; the maximum possible movement is 0.05 mm, below visible modelling tolerance.

## Reproduction and evidence

Baseline commands used `build_character.py --no-glb --no-compare`, followed by `fingerprint.py`. Baseline pairs happened to match geometrically in this run, but reports differed in elapsed times and raw `.blend` SHA-256 differed. A 0.01 mm diagnostic after the first fix reproduced the intermittent boy failure as exactly one changed object: `hair_mass`.

Final CI-sized command:

```text
blender.exe -b --factory-startup -P pipeline/charsys/tests/test_determinism.py -- \
  --blender D:/Animation/tools/blender-5.3/blender.exe --out build/t038_final_boy --character boy
```

Use `--character all` for boy and girl. The driver compares both the production 0.1 mm fingerprint and a strict 0.01 mm regression fingerprint, exits nonzero on either mismatch, writes `determinism.json`, launches Blender with `-t 1`, and supplies deterministic process environment variables. This is directly callable by `check_all`.

Evidence:

- Boy final default fingerprint SHA-256, both runs: `050E06B881904F5B60619F274A935F93A8BA9B7E9310FA79BEEFE7FDC2AB012D`.
- Boy final build report SHA-256, both runs: `13427C0BBE523431DA35E772BF15F237FB9AEFE854B13BD8D0747570F5F5AF92`.
- Boy final 0.01 mm diagnostic: 0 changed objects.
- Girl default fingerprint SHA-256, both runs: `A6807392536BEE6582F0F08D0CFB69A8F5E45ABACE233586702E912800AC1A79`.
- Girl 0.01 mm fingerprint SHA-256, both runs: `915A233A55F4C5417C47CCF855D13C23C45DE3741CF368465B03C4DBE2F53558`.
- Girl build report SHA-256, both runs: `DCE5ED50B800DDF2BDAD5F7E1938276A2F9DE5A4C4CF0C7DFF91140BB4DECBFD`.
- `hair_generic_test.py`: PASS, 0.0 mm root error and 96.9% upper-scalp coverage.

## Audit

### Fixed in the allowed files

| Source | Location | Fix |
| --- | --- | --- |
| Unseeded shared RNG state | `pipeline/charsys/determinism.py:30`, `build_character.py:191,341` | Seed Python, NumPy legacy RNG and `mathutils.noise` after every factory reset. Character-local `random.Random(seed)` streams remain unchanged. |
| Process hash/math-library state | `determinism.py:13-28`, `tests/test_determinism.py:42` | Set `PYTHONHASHSEED=0` before Blender starts and pin OMP/OpenBLAS/MKL/NumExpr worker counts to one. |
| Blender exposed thread default | `determinism.py:41-42` | Set fixed render workers to one; test invocations also use Blender `-t 1`. |
| Collection/object traversal | `build_character.py:77-90,119,141,167,274,313,365,411` | Sort collection, object, modifier-application, face-driver and export traversal by stable names. |
| Legacy family dict order | `hair.py:440-442` | Preserve historical built-in family order (and seeded draws); sort only spec-added family names. |
| Threaded Subdivision + Clouds float drift | `hair.py:28-43,74-75,338-346` | Bake the legacy `hair_mass` modifier and canonicalize its coordinates to 0.1 mm. No layout seed or noise amplitude changed. |
| Fingerprint rounding-boundary noise | `fingerprint.py:16-39` | Versioned fingerprint format, canonical little-endian integer hashing, explicit half-away-from-zero quantization, default 0.1 mm grid; `--grid-m` retains fine diagnostics. |
| Runtime timestamps/durations | `determinism.py:20,46-57`, `build_character.py:322,446` | Remove wall-clock build fields by default. `--timings` opts back in. |

No unseeded `random.random`/`np.random` call remains on the two build paths. Seeded sources are `hair.py` (11 plus fixed offsets), `groom.py:641` (30-derived per-structure seeds), and `geom.py:449` (explicit NumPy generator for fur).

### Required follow-up in prohibited files (not edited)

| File and exact line | Risk/source | Exact proposed fix |
| --- | --- | --- |
| `pipeline/charsys/groom.py:652` | `result.items()` controls multi-part object/material creation order. Current builder dicts are insertion-ordered, but the contract is implicit. | Change to `for part in sorted(result): bucket = result[part]`. Keep `structures` as a list because index `i` intentionally selects the seeded stream at line 641. |
| `pipeline/charsys/face_generic.py:444-445` | Preset delta arrays are added in dict order; floating addition is non-associative. | Use `for a in sorted(w): acc += _au_shape(kb, base, a, w[a] * g, np)`. This fixes accumulation order without changing weights. |
| `pipeline/charsys/garments/generator.py:1599-1604` | Equal garment weights use insertion order as the tie-break, and their denominator is summed in that order. | Select with `sorted(accum.items(), key=lambda item: (-item[1], item[0]))`, then use `math.fsum(weight for _, weight in chosen)` and add groups in group-index order. |
| `pipeline/charsys/garments/generator.py:445-450,577-581,1020-1024,1182-1186,1281-1285` | Solidify relies on Blender defaults beyond thickness/offset and operator context can retain unrelated selection. | Before each apply: deselect all, set only `ob` active/selected, and explicitly set `use_even_offset`, `use_quality_normals`, `use_rim`, `material_offset`, and `material_offset_rim` to the values matching today's appearance. |
| `pipeline/charsys/materials/builder.py:144` | Assignment validation/creation traversal inherits JSON dict order. Similar preset traversal occurs at line 77. | Iterate `for slot in sorted(assignments)` and `for name in sorted(presets)`; fetch the value by key. Keep node link construction explicitly ordered. |

Additional out-of-scope Blender operators are `body_generic.py:240,257` and `body_v6.py:696,724` (Rigify generation and automatic heat weights), plus `geom.py:222` (modifier apply). They use Blender solvers/operators without a reproducibility contract. The follow-up is to clear selection, set active object/mode explicitly before every call, serialize solver inputs in name/index order, and keep the single-thread launch environment. Automatic-weight ties should be normalized with deterministic group-index tie-breaking after the operator.

`geom.py:249-260` accepts a `seed` for `displace_noise` but Blender's legacy Clouds texture exposes no seed and the argument is unused. The safe migration is a separately versioned deterministic noise implementation; silently changing it would change the established felt appearance. T-038 therefore canonicalizes only legacy hair-mass output after evaluating the existing texture.

## Girl remaining differences and sources

There are no remaining girl geometry fingerprint differences at either 0.1 mm or 0.01 mm, and all generated JSON files match byte-for-byte. The two master `.blend` files remain byte-different:

- run 1: `B614F9DCFD77A9212BA061B7D3739A82C6A46BABE1E9DB9A98EAF1991AB76030`
- run 2: `CA393A445ACD81B5BDF06363E93EEB4299A7238227A40A8B1C791C297C65A0DC`

The difference is outside the semantic fingerprint and comes from Blender's opaque file serialization/session metadata and the prohibited solver/operator paths above. It is not an appearance, topology, object-list, material-list, shape-key-list, or report difference. Treat the semantic fingerprint and deterministic JSON as the CI/fidelity baseline; do not use whole-file `.blend` hashes until Blender serialization itself is canonicalized.

## PASS/FAIL

| Check | Result | Evidence |
| --- | --- | --- |
| Boy: two consecutive default fingerprints | PASS | Same SHA-256; 0 changed objects |
| Boy: two consecutive 0.01 mm fingerprints | PASS | 0 changed objects, including `hair_mass` |
| Girl: two consecutive default fingerprints | PASS | Same SHA-256; 0 changed objects |
| Girl: two consecutive 0.01 mm fingerprints | PASS | Same SHA-256; 0 changed objects |
| Boy/girl generated JSON reports | PASS | Pairwise byte-identical |
| Existing hair_clumps/2 independence test | PASS | 0.0 mm / 96.9% coverage |
| Appearance-preserving seed policy | PASS | Existing spec seeds unchanged; max hair-mass snap 0.05 mm |
| Raw `.blend` byte identity | FAIL | Blender container SHA-256 differs; semantic content matches |
| Prohibited-file residual risks removed | FAIL | Documented above for owning agents; files intentionally untouched |

## Ordered commit groups

1. Deterministic runtime and common build traversal: `pipeline/charsys/determinism.py`, `pipeline/charsys/build_character.py`.
2. Legacy hair canonicalization without seed/layout changes: `pipeline/charsys/hair.py`.
3. Fingerprint v2 and check_all-compatible regression test: `pipeline/blender/boy_pilot/fingerprint.py`, `pipeline/charsys/tests/test_determinism.py`.
4. Evidence and prohibited-file handoff: `docs/evaluation/characters/T-038/README.md`.
