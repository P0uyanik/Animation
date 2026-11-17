# Iteration 3 — reference gap analysis

_Inputs studied: character sheets (white-haired girl, brown-haired girl, boy, lineup), classroom stills,
the 5 s water-table reference video, Milestone 02 video, face test sheet._

## 1. Visual target in one paragraph
Felted art-doll figures (~3 heads tall, head ≈ 40% of height) photographed like miniatures in a warm,
richly dressed classroom. Every surface is a textile or wood: wool locks with a soft fibre halo, fleece and
knit garments with thickness, seams and motifs, suede boots with fuzzy cuffs. Faces are smooth porcelain with
huge glossy eyes (two catchlights), drawn lash lines, soft blush and tiny mouths. Light is low warm window
light with soft bounce, deep contact shadows and very shallow depth of field.

## 2. The three characters
| | A — white-haired girl | B — brown-haired girl | C — boy |
| --- | --- | --- | --- |
| Silhouette | Round head, two high buns, wide wavy hair mass to the elbows | Round head, one tall bun, curly mass to the chest, glasses | Spiky tousled crown, compact body, hands in pockets |
| Face | Big blue eyes, upper lash line, tiny open smile, blush | Big brown eyes behind round thin frames, visible brows, open smile | Half-lidded brown eyes, low flat brows, small flat mouth |
| Hair build | Many wavy off-white locks over a full volume; fringe of soft locks; bow of 2 loops + tails | Thick brown curls (spiral locks), bun = coiled locks, pastel pompom/flower clips | Short dense black tapered clumps pointing out/down, fuzzy |
| Clothes | Fleece-knit dress, Peter Pan collar, cuffs, textured skirt with hem band; cream tights; suede boots | White blouse with collar and buttons; rose knit vest with motifs, pockets, brass buttons; sage puffy shorts; boots | Mustard fleece hoodie with hood, pocket, drawstrings; black fleece joggers; backpack straps; yellow/white sneakers |
| Personality | Curious, gentle | Lively, expressive | Sleepy, unimpressed |

## 3. Milestone 02 vs references (by cause)
| Gap | Seen in M02 | Cause |
| --- | --- | --- |
| Hair reads as a cap with locks attached | cap volume dominates; locks hang as a curtain | **Geometry**: one smooth volume + procedural curtain; no layered individual locks, no curls |
| Buns read as balls; bow as beads | spheres; three blobs | **Geometry**: no coiled-lock buns, no ribbon/loop shapes |
| Eyes lack the drawn look | no lashes; one physical reflection | **Geometry + shading**: missing lash curves and stylized catchlights |
| Face is mask-like at distance | brows hidden, mouth small | **Geometry/rig**: brow/lid/mouth set only for one character, no sad/angry shapes |
| Skin slightly plastic | flat matte with sheen | **Shading**: no subsurface response |
| Garments are smooth shells | no seams, cuffs, hems, pockets, buttons | **Geometry**: no accessory/detail primitives (rings, buttons, seams) |
| Only one character | — | **Content + tools**: no character construction kit |
| No glasses, water, folding paper | — | **Geometry + materials**: no thin tube geometry, no dielectric material, no deformable paper |
| Classroom sparse | walls, shelf, blocks | **Content**: no prop kit (books, posters, bunting, cushions, chairs) |
| Editing limited to sliders on primitives | — | **Editor tools**: no hair-lock editor, no garment/prop editing workflow |

## 4. Highest-impact improvements (ordered)
1. **Explicit hair locks** (curve-based, tapered felt core + fibre halo + curl/spiral) usable for wavy hair, curls,
   coiled buns, spiky clumps and fringe — one system covers all three hairstyles; editable lock by lock.
2. **Bone-attached curve accessories**: lashes, glasses frames, drawstrings, bow loops, straps.
3. **Character kit**: shared body/face builder with per-character proportions and personality (default pose).
4. **Thin glass and water materials** (dielectric), stylized catchlights in the eye texture.
5. **Garment details**: hems, cuffs, pockets, buttons, motifs, collars per character.
6. **Expression controls** for all characters: happy, surprised, sad, annoyed, blink, eye opening, gaze.
7. **Group scene**: water table with rippling water, paper fold (staged), boat placement, reactions.
8. **Editor**: hair-lock panel, save/close/reopen test.
9. **Skin subsurface scattering** (planned; risk: noise and render time).

## 5. Implementation order (impact × risk × effort)
Locks → curve accessories → glass/water + catchlights → character kit + B and C → expressions → group scene
→ editor lock panel + project round trip → SSS if time allows. Milestone 01 regression stays green throughout.
