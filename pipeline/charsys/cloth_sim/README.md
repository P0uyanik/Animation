# cloth_sim (T-126c): baked skirt simulation, prototype

Opt-in. A character build never runs it, and a build without the `garment/3` field `cloth_sim` on a `dress` or
`skirt` item is unchanged. With the field, the build only tags the skirt piece (`ps_cloth_sim`, pin attribute
`ps_cloth_pin`); the piece stays skinned as before. The simulation is run per shot on a built master:

```
blender -b --factory-startup -P pipeline/charsys/cloth_sim/run.py -- <master.blend> <walk|sit|kneel> <out dir> \
    [--seed 126] [--set key=value ...] [--save]
```

| step | what happens | module |
|---|---|---|
| proxy | a single-layer grid (30 x 120) resampled from the skirt at rest, lightly smoothed (the knitted relief is not cloth shape), moved by a seeded jitter of 0.1 mm, skinned and pinned like the nearest skirt vertices | `skirt.make_proxy` |
| follow | the skirt and the bands that hang on it (hem rib) follow the proxy through Surface Deform, bound at rest; their fibres follow them | `skirt.bind` |
| simulate | Blender cloth on the proxy against an unmasked copy of the body (and a seat box in `sit`), stepped frame by frame | `skirt.simulate` |
| bake | every frame's proxy points go to `<motion>.pc2`; a Mesh Cache modifier replays the file with no solver | `skirt.replay` |
| measure | per evidence frame: skirt vertices inside the posed body skin (count, depth), by height third, hem rise | `skirt.penetration` |

`skirt.show(followers, False)` switches back to the build's skinned skirt at any time.

## Determinism
The solver has no random input. The seed drives the one random step (the proxy jitter, which breaks the symmetry
that would otherwise decide fold directions by rounding). Measured on the T-126c build, same machine: two runs of
`walk` with seed 126 give the same cache (sha256 equal); seed 7 gives a different one. Across machines or Blender
versions this was not tested.

## Settings (`skirt.DEFAULTS`, override with `--set`)
A doll-sized knitted skirt behaves as a stiff shell that holds its flare. With Blender's cloth-like values (bending
0.08 to 0.5) the cone collapses inwards by a third of its hem radius at rest; `bending: 40`, `tension: 40`,
`vertex_mass: 0.01` keep the hem within 8 mm of its built radius. These are solver values tuned by that one measure,
not material measurements.

## Limits of the prototype
- Colliders are the body skin and a seat box. Sleeves, hands, hair, boots and the floor are not. Lowered arms press
  into the skirt sides and drag a stiff skirt up by centimetres when they swing, so the test motions keep the arms in
  the A-pose (`motions.py`).
- The motions are FK probes without root motion or foot contact, not animation.
- No self-collision. One piece per master. The bake is tied to the proxy's vertex order (same master, seed and
  proxy settings).
- Nothing reads the bake in the engine export yet: it is a Blender-side cache for rendered shots.
