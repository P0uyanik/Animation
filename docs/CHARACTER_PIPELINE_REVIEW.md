# Shared character pipeline review (draft, 2026-11-15)

Status: Supervisor review, no implementation. It is completed when the owner provides the third character's
reference package, which is checked against every row below.

**Goal (owner requirement):** any character, including the third, is made from specs and parameters only. New code is
allowed only for genuinely new shared capabilities, never for one character.

## Capability matrix

| System | Shared today | Character-specific today | What a new character needs today | Gap to close |
| --- | --- | --- | --- | --- |
| Body generation | `body_generic/1` (girl, G02) | boy's legacy `body_v6` | spec parameters only | boy convergence (needs owner approval) |
| Rig, skinning, retarget | Rigify profile, role weights, generated retarget data (T-002) | — | nothing | hip/shoulder deformation quality |
| Face, expressions | `face_generic/1`, 13 action units, 14 + 2 presets | boy's legacy face (4 expressions only) | spec values only | boy convergence; slit mouths only |
| Eyes, blink, gaze | shared (M3/M3.1) | boy legacy | spec | — |
| Accessories | `glasses/1` | boy's backpack (legacy) | spec, if the accessory type exists | more accessory types (hair flowers, band, bags) |
| Hair | `hair_clumps/2` generator, felt shader | boy's tuning | new code for long or curly hair, buns, ponytails | shared groom system for different hair structures |
| Clothing | — | boy's garments in `body_v6` | **new code** | shared garment library (tops, vests, dresses, shorts, trousers, shoes) |
| Materials | felt-hair shader, skin, eyes, glasses | boy's materials inside `body_v6` | partly new code | shared material library: plush, felt, wool, fibres, fabrics, buttons |
| Animation clips | shared clips + generated retarget (T-002) | — | nothing | motion-capture source (Option 2) |
| Engine package and export | shared exporter, profiles | — | nothing | — |

## Questions for the third character's references
1. **Body:** do proportions fit `body_generic` parameters (head size, limbs, hands)?
2. **Face:** does she need any face feature the shared system lacks (mouth type, eye shape, freckles)?
3. **Hair:** what structures does she need (e.g. long curls, round buns), and what do the girl and she share, so one
   groom system serves both?
4. **Clothing:** which garments (e.g. a dress)? These define the first shared garment set together with the girl's
   shirt, vest, shorts and boots.
5. **Materials:** which fabrics and fibres (wool, felt, cotton)? These define the shared material library.
6. **Accessories:** e.g. hair bows, flowers.

## Proposed order after the review (for owner approval)
1. Shared material library.
2. Shared groom system (girl + third character).
3. Shared garment library (girl + third character).
4. Third character from specs only, as the measured generality test.
