# Reference-fit optimiser

Fit continuous character-spec parameters to annotated reference views. The first trial measures the supplied spec with its optional overrides applied in order. Each subsequent trial samples either the full bounds or a shrinking neighbourhood of the best trial, alternating with a seeded random generator. A tie retains the earlier trial.

```sh
python tools/fit/run.py --spec <current.spec.json> --bounds bounds.json \
  --views <front-id>,<threequarter-id>,<side-id> --blender <blender-executable> \
  --budget 3 --height 640 --seed 2 --out build/fit-run
```

Use Python with NumPy and Pillow, and Blender with the spec's generator dependencies. Supply an empty output directory. The budget includes the start. Three builds with three views cost at most nine Workbench frames. The review is separate.

**Inputs.** Use existing scalar paths in the composed spec. Bounds are inclusive, must contain the start, and may be equal to hold a parameter fixed. Dot-separated indices address list entries. The emitted override preserves sibling entries because charsys replaces whole lists. Repeat `--override <file>` for layered start points.

```json
{"face.eyes.lids.upper_edge_deg": [4, 24], "face.brows.inner": [0.25, 0.65]}
```

View IDs select the yaw, elevation and focal length in the spec's reference index. Use `--reference-index <file>` to select a different reference set. The adjacent fidelity index supplies the pose variant. For a set without a declared variant, supply `--variant master` or `--variant compare`. Each view needs a crop, a silhouette mask (or a crop marked for segmentation), and pixel landmarks in `annotations/<view>.json` or `landmarks.json`. Annotated eye polygons enable the eye-mask term.

**Scoring.** A single flat-colour Workbench pass supplies the figure alpha, visible eye openings and brows. The pass omits transparent glasses lenses. Fidelity registration aligns the figure in reference crop coordinates by body scale and silhouette overlap. Each view averages figure IoU, eye IoU when annotated, and the mean landmark score. Each landmark earns `max(0, 1 − distance / head_height)`. A missing candidate point earns zero. Head height runs from the reference silhouette top to the annotated chin, falling back to figure height. Views have equal weight in the final 0–100 score. Use `--landmarks name1,name2` to select projected `LM_` empties (omit the prefix), visible eye centres or inner/outer eye and brow endpoints.

**Outputs and adoption.** `proposal.json` is the winning override. `scores.csv` compares start and best by view and landmark. `scores.json` records all evaluated parameters, scores, build/render times, total elapsed time and the winning blend path. `overlay.jpg` shows the winning outline on the reference mask. Each `trial-NNN/` keeps its build, raw passes and overlay.

Use the winning override **last** in a T-087 spec-candidate recipe with the same spec, starting overrides and input SHA. Run `recipe.py preview`, inspect the first frame, then run `recipe.py sheet` with the same recipe and review directory. The standard sheet requires Cycles. After owner review, the task owning that character area can adopt the override into its candidate. [Review recipe](../../docs/process/REVIEW_RECIPE.md) · [Recorded fits](../../docs/evaluation/characters/T-090/README.md)

Run the fit tests with `python -m unittest discover -s tools/fit/tests -v`.
