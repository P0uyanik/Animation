# Generator pin map (T-179)

Documentation only. Source of truth for pins: `pipeline/charsys/versions.py`; for versions: the `spec.json` of every
published version under `assets/characters/*/versions/` (read 2026-11-21 at `b531ab5`). Round names come from
`docs/process/TASK_LOG.md` / `OWNER_DECISIONS.md`; "—" = no owner-facing round name recorded (not guessed).
Pin numbers do not equal round numbers: read the round column, not the number.

## Registered pins

`*` = no pin in the spec: the pin is the frozen legacy default (`LEGACY_FIELDS`). Retired pins cannot be built.
`B` boy_yellow_hoodie, `G` girl_auburn_bun_glasses, `T` girl_white_hair_blue_dress.

| Feature | Pin | Module (`pipeline/charsys/`) | Round name (task) | Published versions using it |
|---|---|---|---|---|
| body | body_v6/1 | body_v6.py | legacy v6 builder — | B 1.0.0*, 1.1.0* |
| body | body_generic/1 | body_generic.py | — | G 0.10.0 |
| body | body_generic/2 | body_generic.py | fitted head (T-065) | B 2.0.0–2.3.0; G 0.11.0–0.14.0; T 0.1.0 |
| face | body_v6/1 | body_v6.py | legacy v6 face — | B 1.0.0*, 1.1.0* |
| face | face_generic/1 | face_generic.py | — | G 0.10.0 |
| face | face_generic/2 | face_generic.py | face v2 (T-065) | B 2.0.0; G 0.11.0 |
| face | face_generic/3 | face_generic_v3.py | face/eyes round 3 (T-089) | B 2.1.0, 2.2.0, 2.3.0; G 0.12.0, 0.13.0, 0.14.0; T 0.1.0 |
| groom | hair_clumps/1 | hair.py | legacy clump hair — | B 1.0.0*, 1.1.0* |
| groom | hair_clumps/2 | hair.py | lock-family experiments — (retired) | none |
| groom | groom/1 | groom.py | — (V3 batch T-016) | G 0.10.0 |
| groom | groom/2 | groom_hybrid.py | hair v3 / round 2 (T-044, T-070); round 3 data (T-079) | B 2.0.0; G 0.11.0 |
| groom | groom/3 | groom_r4.py | hair round 4 (T-091) | B 2.1.0, 2.2.0; G 0.12.0, 0.13.0 |
| groom | groom/4 | groom_r5.py | hair round 5 (T-118) | none (candidate overrides only) |
| groom | groom/5 | groom_r6.py | hair round 6 (T-160); round 7 (T-167) also builds here | B 2.3.0; G 0.14.0; T 0.1.0 |
| garment | body_v6/1 | body_v6.py | legacy v6 clothing — | B 1.0.0*, 1.1.0* |
| garment | garment/1 | garments.py | — | B 2.0.0; G 0.10.0, 0.11.0 |
| garment | garment/2 | garments_v2.py | garment outlines + accessories (T-093, T-093b) | B 2.1.0, 2.2.0; G 0.12.0, 0.13.0 |
| garment | garment/3 | garments_v3.py | garments round 3 (T-119) | B 2.3.0; G 0.14.0; T 0.1.0 |
| accessories | body_v6/1 | body_v6.py | legacy v6 backpack — | B 1.0.0*, 1.1.0* |
| accessories | accessories/1 | accessories.py | — | G 0.10.0–0.14.0; T 0.1.0 |
| rig | rigify_human/1 | (body_v6 / body_generic rig functions) | — | all versions (B 1.0.0*, 1.1.0* default) |
| materials | body_v6/1 | body_v6.py | legacy albedo — | B 1.0.0*, 1.1.0* |
| materials | albedo/1 | geom.py | — | none |
| materials | presets/1 | materials/builder | — | G 0.10.0 |
| materials | presets/2 | materials/builder | skin family (T-066) | B 2.0.0; G 0.11.0 |
| materials | presets/3 | materials/builder | materials round 2 (T-092) | B 2.1.0–2.3.0; G 0.12.0–0.14.0; T 0.1.0 |
| exporter | export/1, /2, /3 | — | — (retired) | none |
| exporter | export/4 | export_engine.py | — | all versions (B 1.0.0*, 1.1.0* default) |
| exporter | export/5 | export_engine.py | byte-reproducible export (T-056) | none |

Naming: TASK_LOG is authoritative (liaison confirmed 2026-11-21): groom/4 = groom_r5.py = hair round 5 (T-118); groom/5 = groom_r6.py = hair round 6 (T-160), and round 7 (T-167) uses groom/5 with overrides.

Not in the registry: `body.hands = "hands_r2/1"` is a spec field checked in `build_character.py`
(module `hands_r2.py`, T-121); see below.

## Opt-in flags inside released modules

Spec keys that change output only when set. Absent = the pinned module builds exactly as before.

| Flag (spec key) | Module | Task |
|---|---|---|
| `body.hands = "hands_r2/1"` (separated fingers) | hands_r2.py, `build_character.py` | T-121 |
| `face.shape.lower_face` (cheek pads, jaw) | face_v3/lower_face.py via face_generic_v3.py | T-109 |
| `face.eyes.lids.lower_fit` (lower lid follows the eyeball) | face_v3/lids.py via face_generic_v3.py | T-109 |
| `face.eyes.lids.closed_fit` (closed lids follow the eyeball) | face_v3/lids.py via face_generic_v3.py | T-113 |
| `closed_fit.lash_curve` (dark lash curve on closed eye) | face_v3/lids.py | T-137 |
| `socket.closed_fill` (skin closes the opening on full-closure lid keys) | face_v3/socket.py, lids.py | T-156 |
| `face.ears.tint`, `face.ears.seat_offset_m` | face_generic.py | T-159 |
| `temples.rest_on_ear` (glasses) | accessories.py | T-159 |
| `face.shape.outline_smooth_m`, `front_fade_m` | face_features.py | T-159 |
| `cheek_pad_top_fade_m` | face_v3/lower_face.py | T-168 |
| `face.nose.type = "upturned"` | face_features.py | T-168 |
| `leg_split` (crotch arch) | garments_v2/ (core.py, outlines.py) | T-093b |
| `hair.ear_keepout` (hair surface moved out of the ear meshes) | groom_contact.py via groom_r6.py (groom/5) | T-183 |
| `hair.dynamics.contact` (body colliders for hair chains; engine chain key `contact`) | groom_contact.py via groom_r6.py (groom/5); engine/anim/secondary.cpp | T-183 |
| `seated` on a `shorts` / `trousers` item (weights and collision weights for a deep hip bend) | garments_v3/seated.py via garments_v3/core.py | T-184 |

Flags above were taken from module docstrings and task commits; the list is not an exhaustive scan of every key.

## Rule: opt-in to default

An opt-in becomes a default only at the next real look round, by registering a new pin in the existing registry
(`versions.py`) whose module sets those defaults. No renames, no new mechanism. Released pins and their output never
change; characters move to the new pin only by a new character version (owner approval as usual).
