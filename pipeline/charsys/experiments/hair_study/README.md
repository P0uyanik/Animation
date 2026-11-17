# T-049 hair approach study (experiment code)

Study only. Report and evidence: [docs/evaluation/characters/T-049/README.md](../../../../docs/evaluation/characters/T-049/README.md).
Nothing here is used by the production build. The shared groom code is called as a library, and the study primitives
are registered at runtime (`primitives.register()`).

| file | purpose |
|---|---|
| `primitives.py` | `study_clumps` (felt clumps along a flow map, face keep-out), `study_curtain` (sculpted ringlet curtain), `fuse()` (voxel union, approach B) |
| `study_build.py` | swap a built master's hair for a study spec (shared `groom.build` / `groom.bind`, shared GN fibres) |
| `specs/make_boy_specs.py`, `specs/make_girl_specs.py` | write `specs/<boy,girl>_<A,B,C>.json` |
| `preview.py` | cheap iteration previews (Cycles 4 spp, 300 px; not evidence) |
| `render_evidence.sh` | 3 fidelity views (`tools/fidelity/run.py`) + 1 face close-up per study build |
| `measure.py` | face visibility, collision, 2 s head turn (spring proxy) and its frames |
| `make_sheets.py`, `scorecard.py` | contact sheets, head-turn strips/GIFs, scorecard |

```sh
B=<blender>   # e.g. a wrapper around tools/bpy_blender.py
$B -b --factory-startup -P pipeline/charsys/build_character.py -- --spec <character spec> --out base/<c> --no-glb --no-compare
python3 pipeline/charsys/experiments/hair_study/specs/make_boy_specs.py
python3 pipeline/charsys/experiments/hair_study/specs/make_girl_specs.py
$B -b --factory-startup -P pipeline/charsys/experiments/hair_study/study_build.py -- --base base/<c>/<id>_master.blend --study pipeline/charsys/experiments/hair_study/specs/<c>_<A|B|C>.json --out st/<c>_<A|B|C>
pipeline/charsys/experiments/hair_study/render_evidence.sh $B <c> <A|B|C> st fid
$B -b --factory-startup -P pipeline/charsys/experiments/hair_study/measure.py -- st/<c>_<ap>/<id>_study.blend ms/<c>_<ap> --render   # or --render-range a-b
python3 pipeline/charsys/experiments/hair_study/make_sheets.py fid ms sheets
python3 pipeline/charsys/experiments/hair_study/scorecard.py st fid ms score
```
