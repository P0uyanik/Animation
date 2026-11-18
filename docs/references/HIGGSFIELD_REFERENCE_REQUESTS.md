# Additional reference images to generate with Higgsfield

Prepared 2026-11-18 by the Supervisor for the owner. Goal: close the visual gaps between our current models
(boy 2.0.0, girl 0.11.0, third character not built yet) and the original references, using as few new images as
possible. Every request below names the gap it closes. Anything already well covered by the existing references is
listed under **Already covered: do not generate**.

Sources of the gaps:
- Codex fidelity gap report: `docs/evaluation/review/T-083/README.md` (overall 4/10).
- Owner sheets for boy 2.0.0 (T-080) and girl 0.11.0 (strict comparison, T-081).
- Latest-characters still from T-082, and the owner decisions in `docs/process/OWNER_DECISIONS.md`.

## How to use this file

1. **Always attach the reference images named under "Attach".** Use Higgsfield's image-reference / character-reference
   input so the character stays identical. The text prompt alone is not enough to keep the exact design.
2. **Copy each prompt as it is.** Each prompt is complete (the identity lock is already written into it) and has the same four parts:
   - an *identity lock*, which describes the exact character;
   - a *style lock*, which keeps all images comparable;
   - the shot itself;
   - a negative prompt.
3. **Make 2–4 variants per prompt and keep the most faithful one.** Reject an image if anything in the design changed:
   hair shape, colours, eye colour, clothes, accessories or proportions. A faithful image is worth more than a pretty one.
4. **Image settings:** highest resolution available (≥ 2048 px on the long side), PNG if possible. Use the aspect ratio
   given in each request.
5. **Name each file** `<character>_<ID>_<short-name>.png`, for example `boy_B01_face_front.png`, and send them back.
   I store them read-only in `assets/characters/<character>/references/uploads/` with a README row each. They become
   primary targets for round 2.

**Priorities**

| Priority | Meaning |
| --- | --- |
| **P1** | Fixes a top-ranked gap in our current models and is needed before round 2 starts. Generate these first. |
| **P2** | Materials and garment detail for the round 2 materials and garment work. |
| **P3** | Acting, lighting and staging; useful later in animation and shot work. |

### Shared negative prompt (paste into the negative field of every prompt)

```text
different character, changed hairstyle, changed hair colour, changed eye colour, changed clothing, extra accessories, missing accessories, text, labels, captions, watermark, logo, frame, collage, extra fingers, fused fingers, glossy plastic skin, shiny vinyl, porcelain glaze, anime style, 2D illustration, cartoon outline, cel shading, low detail, blurry subject, heavy depth of field on the subject, coloured gels, dramatic lighting, harsh shadows, cropped head, cropped feet when full body is requested, multiple characters when one is requested, human child, realistic human skin
```

### Shared style lock (already included in every prompt below)

> Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a
> soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle
> rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural
> true colours, no text, no props unless stated.

---

## 1. Boy (yellow hoodie): `boy_yellow_hoodie`

**What we already have:**
- Full-body front, 3/4, side and back views (`val27_*`, `canon29_*`, `turn08_*`, `hero24_front`, `orig07_front`).
- One close-up sheet: hair from above, crown tufts, face front, hoodie back (`uploads/01_closeups_…`).
- `char_C_boy.jpg` and `lineup.webp`.

**Biggest gaps in our model:**
- **Face:** too narrow eyes (eye width 0.114 of head width vs 0.154 in the reference) and weak blush. There is only
  one front face close-up, and no 3/4 or profile face close-up.
- **Hair:** the crown reads flat. We lack deep channels between thick petals, and we have no hair close-ups from the
  side or back.
- **Backpack:** its body is never shown in any reference (only the straps), so our backpack is a guess.
- **Materials:** the hoodie fleece looks mottled and the trousers shaggy. There is no fabric close-up of the trouser
  pile, cuffs or sneakers.
- **Hands:** there is no reference for the hands, which matters for the cup handover (T-083 gap 2).

**Attach for every boy prompt:**
- `docs/references/char_C_boy.jpg`
- `assets/characters/boy_yellow_hoodie/references/views/val27_front.png`
- `assets/characters/boy_yellow_hoodie/references/uploads/01_closeups_hair_top_crown_face_fleece_2026-11-17.webp`
- Add the matching view from `views/` when the prompt is a side or back view.

**Identity lock (boy):** the same handmade needle-felted wool plush doll boy as in the attached references, chibi
proportions with a large head (about 37 % of total height), pale porcelain-peach flocked felt skin with a soft rosy
blush on the cheeks, heavy-lidded sleepy half-closed eyes with dark brown irises and a thin dark upper lid line, thin
straight dark brows, a very small slightly pouting closed mouth, small rounded ears, messy spiky black-brown felted wool
hair made of thick pointed petal-like clumps radiating from a crown whorl with a few flyaway fibres and a fringe
falling over the forehead, matte mustard-yellow fleece pullover hoodie with hood, kangaroo pocket, cream drawstrings,
ribbed cuffs and hem, black fuzzy fleece jogger trousers, mustard-yellow sneakers with cream rubber toe caps and soles
and white stripes, dark navy backpack straps over both shoulders.

### B01 · Face close-up, front · **P1**
**Closes:** narrow eyes, lid shape, blush strength, skin colour under neutral light (T-083 gaps 1 and 6). Aspect 1:1.
```text
The same handmade needle-felted wool plush doll boy as in the attached references, chibi proportions with a large head (about 37 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush on the cheeks, heavy-lidded sleepy half-closed eyes with dark brown irises and a thin dark upper lid line, thin straight dark brows, a very small slightly pouting closed mouth, small rounded ears, messy spiky black-brown felted wool hair made of thick pointed petal-like clumps radiating from a crown whorl with a few flyaway fibres and a fringe falling over the forehead, matte mustard-yellow fleece pullover hoodie with hood, kangaroo pocket, cream drawstrings, ribbed cuffs and hem, black fuzzy fleece jogger trousers, mustard-yellow sneakers with cream rubber toe caps and soles and white stripes, dark navy backpack straps over both shoulders. Close-up portrait of the head and shoulders, camera exactly at eye level, perfectly frontal, the face filling two thirds of the frame, neutral calm sleepy expression with half-closed eyes looking straight at the camera, mouth closed, the full width of both eyes and both cheeks clearly visible, hair fringe in its natural position. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:**
- A frontal, symmetrical head shot that matches the face in `char_C_boy.jpg`.
- Readable eye width and spacing, lid line, brow shape and blush gradient.
- The skin is pale porcelain-peach, not tan.

### B02 · Face close-up, 3/4 left · **P1**
**Closes:** eye shape at 3/4 and the eye-socket rim, cheek volume, ear position, how the fringe overlaps the face at
3/4 (we have no 3/4 face reference). Aspect 1:1.
```text
The same handmade needle-felted wool plush doll boy as in the attached references, chibi proportions with a large head (about 37 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush on the cheeks, heavy-lidded sleepy half-closed eyes with dark brown irises and a thin dark upper lid line, thin straight dark brows, a very small slightly pouting closed mouth, small rounded ears, messy spiky black-brown felted wool hair made of thick pointed petal-like clumps radiating from a crown whorl with a few flyaway fibres and a fringe falling over the forehead, matte mustard-yellow fleece pullover hoodie with hood, kangaroo pocket, cream drawstrings, ribbed cuffs and hem, black fuzzy fleece jogger trousers, mustard-yellow sneakers with cream rubber toe caps and soles and white stripes, dark navy backpack straps over both shoulders. Close-up portrait of the head and shoulders turned 45 degrees to the doll's right so we see the left three-quarter view of the face, camera at eye level, neutral calm sleepy expression, half-closed eyes looking in the direction the head faces, mouth closed, the left ear, the cheek curve and the side of the fringe clearly visible. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:**
- A clean 3/4 face, with the far eye partly behind the nose bridge and the near eye fully readable.
- The cheek volume and the ear shape are clear.
- It matches the 3/4 body view `val27_threequarter_right.png`, mirrored.

### B03 · Face close-up, profile · **P1**
**Closes:** face depth and flatness (our face reads wide and flat), brow ridge, nose bump, lip and chin profile, how
far the fringe sticks out. Aspect 1:1.
```text
The same handmade needle-felted wool plush doll boy as in the attached references, chibi proportions with a large head (about 37 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush on the cheeks, heavy-lidded sleepy half-closed eyes with dark brown irises and a thin dark upper lid line, thin straight dark brows, a very small slightly pouting closed mouth, small rounded ears, messy spiky black-brown felted wool hair made of thick pointed petal-like clumps radiating from a crown whorl with a few flyaway fibres and a fringe falling over the forehead, matte mustard-yellow fleece pullover hoodie with hood, kangaroo pocket, cream drawstrings, ribbed cuffs and hem, black fuzzy fleece jogger trousers, mustard-yellow sneakers with cream rubber toe caps and soles and white stripes, dark navy backpack straps over both shoulders. Close-up portrait of the head and shoulders in exact side profile facing left, camera at eye level, neutral calm sleepy expression, mouth closed, the silhouette of forehead, tiny nose bump, lips and chin clearly readable against the background, the hair silhouette from fringe to nape fully inside the frame. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:** a pure profile head shot giving the face depth, the forehead-to-chin curve and the hair volume
in front of and behind the ear.

### B04 · Hair close-up, side · **P1**
**Closes:** hair clump depth and channels and the length of the tufts at the temple and above the ear (T-083 gap 3).
Aspect 1:1.
```text
The same handmade needle-felted wool plush doll boy as in the attached references, chibi proportions with a large head (about 37 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush on the cheeks, heavy-lidded sleepy half-closed eyes with dark brown irises and a thin dark upper lid line, thin straight dark brows, a very small slightly pouting closed mouth, small rounded ears, messy spiky black-brown felted wool hair made of thick pointed petal-like clumps radiating from a crown whorl with a few flyaway fibres and a fringe falling over the forehead, matte mustard-yellow fleece pullover hoodie with hood, kangaroo pocket, cream drawstrings, ribbed cuffs and hem, black fuzzy fleece jogger trousers, mustard-yellow sneakers with cream rubber toe caps and soles and white stripes, dark navy backpack straps over both shoulders. Close-up of the head in exact side view facing right, framed from the top of the hair to the chin, focusing on the felted wool hair: thick rounded petal-like clumps with deep shadowed gaps between them, pointed tips, flyaway fibres, the fringe and the hair over the ear clearly separated into individual clumps. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:**
- A side view of the hair mass with readable clump count, width and depth, and the gaps between clumps.
- The size of the hair silhouette relative to the head.

### B05 · Hair close-up, back and crown whorl · **P1**
**Closes:** how the clumps flow from the crown whorl down to the nape (our back hair reads as a helmet), and the
neck and hood line. Aspect 1:1.
```text
The same handmade needle-felted wool plush doll boy as in the attached references, chibi proportions with a large head (about 37 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush on the cheeks, heavy-lidded sleepy half-closed eyes with dark brown irises and a thin dark upper lid line, thin straight dark brows, a very small slightly pouting closed mouth, small rounded ears, messy spiky black-brown felted wool hair made of thick pointed petal-like clumps radiating from a crown whorl with a few flyaway fibres and a fringe falling over the forehead, matte mustard-yellow fleece pullover hoodie with hood, kangaroo pocket, cream drawstrings, ribbed cuffs and hem, black fuzzy fleece jogger trousers, mustard-yellow sneakers with cream rubber toe caps and soles and white stripes, dark navy backpack straps over both shoulders. Close-up of the back of the head seen from behind and slightly above (camera 20 degrees above eye level), framed from the top of the hair to the hood, showing the crown whorl, the thick felted petal clumps radiating down to the nape, their pointed tips over the neck, and the top edge of the mustard hood. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:** the clump layout from behind, consistent with the top-down close-up in upload 01 and the back
view `val27_back.png`.

### B06 · Backpack, full back view · **P1**
**Closes:** the backpack design (shape, size, colour, flap, zipper and how the straps attach), which no existing
reference shows. **Owner: please confirm the design you get.** The straps in the references are dark navy, so the
prompt keeps that colour.
```text
The same handmade needle-felted wool plush doll boy as in the attached references, chibi proportions with a large head (about 37 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush on the cheeks, heavy-lidded sleepy half-closed eyes with dark brown irises and a thin dark upper lid line, thin straight dark brows, a very small slightly pouting closed mouth, small rounded ears, messy spiky black-brown felted wool hair made of thick pointed petal-like clumps radiating from a crown whorl with a few flyaway fibres and a fringe falling over the forehead, matte mustard-yellow fleece pullover hoodie with hood, kangaroo pocket, cream drawstrings, ribbed cuffs and hem, black fuzzy fleece jogger trousers, mustard-yellow sneakers with cream rubber toe caps and soles and white stripes, dark navy backpack straps over both shoulders. Full-body photograph from directly behind, standing in a relaxed A-pose, wearing a small rounded dark navy felt backpack on both shoulders, the whole backpack clearly visible: simple rounded rectangular shape about as wide as the shoulders and reaching the lower back, a soft top flap, one front zipper pocket, small top grab loop, the navy shoulder straps meeting the top of the backpack, the hood resting above the backpack, feet fully in frame. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:**
- A back view with the complete backpack, consistent with the strap position in the front references.
- Aspect 2:3.
- If you prefer another backpack colour or shape, change the description in the prompt; that becomes the design.

### B07 · Backpack, side view · **P2**
**Closes:** backpack depth and how it sits against the hood and back. Aspect 2:3.
```text
The same handmade needle-felted wool plush doll boy as in the attached references, chibi proportions with a large head (about 37 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush on the cheeks, heavy-lidded sleepy half-closed eyes with dark brown irises and a thin dark upper lid line, thin straight dark brows, a very small slightly pouting closed mouth, small rounded ears, messy spiky black-brown felted wool hair made of thick pointed petal-like clumps radiating from a crown whorl with a few flyaway fibres and a fringe falling over the forehead, matte mustard-yellow fleece pullover hoodie with hood, kangaroo pocket, cream drawstrings, ribbed cuffs and hem, black fuzzy fleece jogger trousers, mustard-yellow sneakers with cream rubber toe caps and soles and white stripes, dark navy backpack straps over both shoulders. Full-body photograph in exact side view facing right, standing in a relaxed A-pose, wearing the same small rounded dark navy felt backpack, showing its depth, the soft top flap, the strap running from the top of the backpack over the shoulder to the bottom of the backpack, and how the hood rests on top of it, feet fully in frame. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:** a side silhouette of the backpack (depth and strap path), consistent with B06.

### B08 · Hoodie fleece macro · **P2**
**Closes:** the fleece pile (our hoodie is mottled and blotchy; the reference fibre detail is about 3.5× ours).
Aspect 4:3.
```text
The same handmade needle-felted wool plush doll boy as in the attached references, chibi proportions with a large head (about 37 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush on the cheeks, heavy-lidded sleepy half-closed eyes with dark brown irises and a thin dark upper lid line, thin straight dark brows, a very small slightly pouting closed mouth, small rounded ears, messy spiky black-brown felted wool hair made of thick pointed petal-like clumps radiating from a crown whorl with a few flyaway fibres and a fringe falling over the forehead, matte mustard-yellow fleece pullover hoodie with hood, kangaroo pocket, cream drawstrings, ribbed cuffs and hem, black fuzzy fleece jogger trousers, mustard-yellow sneakers with cream rubber toe caps and soles and white stripes, dark navy backpack straps over both shoulders. Macro close-up of the front of the mustard-yellow fleece hoodie: the kangaroo pocket edge, the cream drawstrings with small knotted tips, the ribbed hem and one ribbed cuff with the doll's hand just visible, showing the soft even matte fleece pile with fine fibres and a soft fuzzy halo, no blotches, no shiny spots. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:**
- Fabric detail at a scale where single fibres and the pile direction are visible.
- An even mustard colour for colour calibration.
- The rib structure at the cuff and hem.

### B09 · Trousers and sneakers macro · **P2**
**Closes:** trouser fleece pile and length, trouser cuff at the ankle, sneaker construction (toe cap, stripes, laces,
sole). Aspect 4:3.
```text
The same handmade needle-felted wool plush doll boy as in the attached references, chibi proportions with a large head (about 37 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush on the cheeks, heavy-lidded sleepy half-closed eyes with dark brown irises and a thin dark upper lid line, thin straight dark brows, a very small slightly pouting closed mouth, small rounded ears, messy spiky black-brown felted wool hair made of thick pointed petal-like clumps radiating from a crown whorl with a few flyaway fibres and a fringe falling over the forehead, matte mustard-yellow fleece pullover hoodie with hood, kangaroo pocket, cream drawstrings, ribbed cuffs and hem, black fuzzy fleece jogger trousers, mustard-yellow sneakers with cream rubber toe caps and soles and white stripes, dark navy backpack straps over both shoulders. Macro close-up of the lower legs and feet from a front three-quarter angle at knee height: the black fuzzy fleece jogger trousers with their soft pile and gathered ankle cuffs, and both mustard-yellow sneakers with cream rubber toe caps, cream soles, white side stripes and laces clearly visible. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:** a material and shape reference for the trouser fleece (how fuzzy it really is), the cuff break
over the shoe, and the sneaker details.

### B10 · Hands, relaxed and holding a small cup · **P2**
**Closes:** hand shape, finger count and size, and a readable grasp silhouette for the cup handover (T-083 gap 2:
our cup disappears inside the fist). Aspect 3:2.
```text
The same handmade needle-felted wool plush doll boy as in the attached references, chibi proportions with a large head (about 37 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush on the cheeks, heavy-lidded sleepy half-closed eyes with dark brown irises and a thin dark upper lid line, thin straight dark brows, a very small slightly pouting closed mouth, small rounded ears, messy spiky black-brown felted wool hair made of thick pointed petal-like clumps radiating from a crown whorl with a few flyaway fibres and a fringe falling over the forehead, matte mustard-yellow fleece pullover hoodie with hood, kangaroo pocket, cream drawstrings, ribbed cuffs and hem, black fuzzy fleece jogger trousers, mustard-yellow sneakers with cream rubber toe caps and soles and white stripes, dark navy backpack straps over both shoulders. Close-up of the doll's two hands at chest height in front of the hoodie: the left hand relaxed and open with soft rounded felt fingers, the right hand holding a small pale ceramic cup by its side with the fingertips and thumb wrapped around it so that the cup stays clearly visible, the ribbed hoodie cuffs at the wrists. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, only the small cup as a prop.
```
**Expected output:** hand proportions and a grasp pose in which the cup stays visible; we use it for hand-pose and
grasp shapes.

### B11 · Expression sheet, subtle low-energy · **P3**
**Closes:** expression range consistent with his personality (subtle, low energy, sleepy), used for face rig targets.
We have only the neutral face. Aspect 3:2.
```text
The same handmade needle-felted wool plush doll boy as in the attached references, chibi proportions with a large head (about 37 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush on the cheeks, heavy-lidded sleepy half-closed eyes with dark brown irises and a thin dark upper lid line, thin straight dark brows, a very small slightly pouting closed mouth, small rounded ears, messy spiky black-brown felted wool hair made of thick pointed petal-like clumps radiating from a crown whorl with a few flyaway fibres and a fringe falling over the forehead, matte mustard-yellow fleece pullover hoodie with hood, kangaroo pocket, cream drawstrings, ribbed cuffs and hem, black fuzzy fleece jogger trousers, mustard-yellow sneakers with cream rubber toe caps and soles and white stripes, dark navy backpack straps over both shoulders. A clean grid of six head-and-shoulder portraits of the same doll on the same background, all from the front at eye level: 1 neutral sleepy, 2 tiny reluctant smile with closed mouth, 3 mild surprise with eyes slightly more open, 4 mildly annoyed with lowered brows, 5 eyes fully closed in a slow blink, 6 glancing sideways without turning the head. Expressions stay subtle and low-energy, the same felt face in every portrait, no text. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, natural true colours.
```
**Expected output:** six faces with identical design and only lids, brows and mouth changing; the targets for face
round 3 and acting.

### B12 · Slouched pose, hands in pockets · **P3**
**Closes:** his signature acting pose for the acting round (shoulder slouch, hands inside the kangaroo pocket).
Aspect 2:3.
```text
The same handmade needle-felted wool plush doll boy as in the attached references, chibi proportions with a large head (about 37 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush on the cheeks, heavy-lidded sleepy half-closed eyes with dark brown irises and a thin dark upper lid line, thin straight dark brows, a very small slightly pouting closed mouth, small rounded ears, messy spiky black-brown felted wool hair made of thick pointed petal-like clumps radiating from a crown whorl with a few flyaway fibres and a fringe falling over the forehead, matte mustard-yellow fleece pullover hoodie with hood, kangaroo pocket, cream drawstrings, ribbed cuffs and hem, black fuzzy fleece jogger trousers, mustard-yellow sneakers with cream rubber toe caps and soles and white stripes, dark navy backpack straps over both shoulders. Full-body photograph from a front three-quarter angle, standing in a relaxed slouch with both hands pushed into the kangaroo pocket of the hoodie, shoulders slightly forward, head tilted a little down, sleepy eyes looking at the camera, backpack straps visible, feet fully in frame. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:** a pose target with readable hand placement, fabric bunching at the pocket and spine curve.

**Boy: already covered, do not generate:**
- Full-body front, 3/4, side and back turnarounds.
- Hair from above.
- The front face close-up from upload 01 (B01 adds a cleaner, more frontal one).
- The hoodie back under rim light.

---

## 2. Girl with glasses: `girl_auburn_bun_glasses`

**What we already have:**
- Turnaround and model sheet: front, front-left, left, right, back-right and back, plus hair construction, clothing
  breakdown, four expressions and proportions (`uploads/ref_30.webp`, `views/sheet30_*`).
- Technical sheets: topology, rig, hands, hair groom, garments, materials and UVs (`ref_31`–`ref_46`).
- `char_B_brown_hair.webp` and `lineup.webp`.

**Biggest gaps in our model:**
- **Fringe:** no side-swept fringe over the forehead. No reference shows the hairline close up.
- **Eyes:** too narrow inside the glasses (eye width 0.135 of head width vs 0.164), and the lids are too pale.
- **Resting mouth:** owner decision: closed gentle smile at rest. Almost all references show an open smile.
- **Back hair:** our hair shows a band where the smooth back section meets the curls, and its silhouette is too wide.
- **Fabrics:** the vest reads frayed instead of soft felt. The cream fleece boot cuffs are missing.
- **Glasses:** there is no close-up of the frame.

**Attach for every girl prompt:**
- `docs/references/char_B_brown_hair.webp`
- `assets/characters/girl_auburn_bun_glasses/references/uploads/ref_30.webp`
- `assets/characters/girl_auburn_bun_glasses/references/views/sheet30_front.png`
- For back and side shots, add `views/sheet30_back.png` or `views/sheet30_left.png`.

**Identity lock (girl):** the same handmade needle-felted wool plush doll girl as in the attached references, chibi
proportions with a large head (about 38 % of total height), pale porcelain-peach flocked felt skin with a soft rosy
blush, large round warm-brown eyes with dark upper lashes and soft brown brows, thin round brown-copper wire glasses,
long warm chestnut-brown felted wool hair falling below the shoulders in soft ringlet curls, a soft side-swept fringe
over the forehead, a high round top bun tied with a grey-blue hair band and decorated with small pink felt flowers,
cream long-sleeved blouse with a rounded collar and gathered cuffs, dusty rose-mauve felt vest with dark embroidered
motifs, two small pockets and tiny buttons, sage-green puffy bloomer shorts, brown shaggy fleece ankle boots with a
cream fleece cuff.

### G01 · Face close-up, front, closed gentle smile (rest face) · **P1**
**Closes:** the owner-decided rest expression, eye size inside the lenses, lid and lash darkness, blush, fringe
position (T-083 gap 1). Aspect 1:1.
```text
The same handmade needle-felted wool plush doll girl as in the attached references, chibi proportions with a large head (about 38 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush, large round warm-brown eyes with dark upper lashes and soft brown brows, thin round brown-copper wire glasses, long warm chestnut-brown felted wool hair falling below the shoulders in soft ringlet curls, a soft side-swept fringe over the forehead, a high round top bun tied with a grey-blue hair band and decorated with small pink felt flowers, cream long-sleeved blouse with a rounded collar and gathered cuffs, dusty rose-mauve felt vest with dark embroidered motifs, two small pockets and tiny buttons, sage-green puffy bloomer shorts, brown shaggy fleece ankle boots with a cream fleece cuff. Close-up portrait of the head and shoulders, camera exactly at eye level, perfectly frontal, the face filling two thirds of the frame, calm friendly rest expression with a small closed gentle smile (mouth closed, no teeth), large round brown eyes wide open and looking straight at the camera through the round glasses, eyes clearly visible inside the lenses without strong reflections, the side-swept fringe resting over the forehead. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:**
- The definitive rest face: eye width and spacing inside the glasses, dark upper lid line and lashes, closed smile
  shape, blush placement.
- The fringe shape over the forehead.

### G02 · Face close-up, 3/4 left · **P1**
**Closes:** the glasses at an angle, eye and lid shape at 3/4, cheek roundness, fringe and side curls framing the
face. Aspect 1:1.
```text
The same handmade needle-felted wool plush doll girl as in the attached references, chibi proportions with a large head (about 38 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush, large round warm-brown eyes with dark upper lashes and soft brown brows, thin round brown-copper wire glasses, long warm chestnut-brown felted wool hair falling below the shoulders in soft ringlet curls, a soft side-swept fringe over the forehead, a high round top bun tied with a grey-blue hair band and decorated with small pink felt flowers, cream long-sleeved blouse with a rounded collar and gathered cuffs, dusty rose-mauve felt vest with dark embroidered motifs, two small pockets and tiny buttons, sage-green puffy bloomer shorts, brown shaggy fleece ankle boots with a cream fleece cuff. Close-up portrait of the head and shoulders turned 45 degrees to the doll's right so we see the left three-quarter view of the face, camera at eye level, calm rest expression with a small closed gentle smile, large brown eyes looking in the direction the head faces, the round glasses seen at an angle with the left temple arm going to the ear, the side-swept fringe and the loose curls framing the cheek clearly visible. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:** a clean 3/4 face with the glasses in perspective, cheek volume, and the face-framing curls in
front of the ear.

### G03 · Face close-up, profile · **P1**
**Closes:** face depth, nose and lip profile, how the glasses sit on the nose and ear, curl volume behind the ear.
Aspect 1:1.
```text
The same handmade needle-felted wool plush doll girl as in the attached references, chibi proportions with a large head (about 38 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush, large round warm-brown eyes with dark upper lashes and soft brown brows, thin round brown-copper wire glasses, long warm chestnut-brown felted wool hair falling below the shoulders in soft ringlet curls, a soft side-swept fringe over the forehead, a high round top bun tied with a grey-blue hair band and decorated with small pink felt flowers, cream long-sleeved blouse with a rounded collar and gathered cuffs, dusty rose-mauve felt vest with dark embroidered motifs, two small pockets and tiny buttons, sage-green puffy bloomer shorts, brown shaggy fleece ankle boots with a cream fleece cuff. Close-up portrait of the head and shoulders in exact side profile facing left, camera at eye level, calm rest expression with a small closed gentle smile, the glasses seen from the side with the temple arm resting on the ear, the profile of forehead, tiny nose, lips and chin clearly readable, the top bun and the ringlets behind the ear inside the frame. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:** a pure profile with the face silhouette, glasses depth and lens distance from the eye, bun
height and ringlet volume.

### G04 · Fringe and hairline close-up · **P1**
**Closes:** the missing side-swept fringe, which no current reference shows in detail. Aspect 1:1.
```text
The same handmade needle-felted wool plush doll girl as in the attached references, chibi proportions with a large head (about 38 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush, large round warm-brown eyes with dark upper lashes and soft brown brows, thin round brown-copper wire glasses, long warm chestnut-brown felted wool hair falling below the shoulders in soft ringlet curls, a soft side-swept fringe over the forehead, a high round top bun tied with a grey-blue hair band and decorated with small pink felt flowers, cream long-sleeved blouse with a rounded collar and gathered cuffs, dusty rose-mauve felt vest with dark embroidered motifs, two small pockets and tiny buttons, sage-green puffy bloomer shorts, brown shaggy fleece ankle boots with a cream fleece cuff. Close-up of the upper half of the head from the front and slightly above (camera 25 degrees above eye level), framed from the top bun to the glasses, focusing on the hair: the parting, the soft side-swept fringe crossing the forehead in thick felted wool strands, how the fringe joins the side curls, the hair band and pink felt flowers at the base of the bun. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:** the parting, the fringe direction and thickness, and where the fringe ends at the temple; this
is the direct target for the hair round 4 fringe.

### G05 · Back hair close-up: bun, band and transition into curls · **P1**
**Closes:** the visible band where our smooth back hair meets the curls, bun shape and size, and the overall width of
the hair (our silhouette is too wide, the main reason for her lower score). Aspect 3:4.
```text
The same handmade needle-felted wool plush doll girl as in the attached references, chibi proportions with a large head (about 38 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush, large round warm-brown eyes with dark upper lashes and soft brown brows, thin round brown-copper wire glasses, long warm chestnut-brown felted wool hair falling below the shoulders in soft ringlet curls, a soft side-swept fringe over the forehead, a high round top bun tied with a grey-blue hair band and decorated with small pink felt flowers, cream long-sleeved blouse with a rounded collar and gathered cuffs, dusty rose-mauve felt vest with dark embroidered motifs, two small pockets and tiny buttons, sage-green puffy bloomer shorts, brown shaggy fleece ankle boots with a cream fleece cuff. Photograph of the head and upper back from directly behind at shoulder height, framed from the top of the bun to the middle of the back: the round top bun with the grey-blue band and pink felt flowers, the smooth felted hair from the crown flowing down and turning gradually into soft ringlet curls without any visible seam or band, the overall width of the hair mass against the shoulders clearly readable. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:** how the crown hair turns into ringlets, ringlet size and count, and the hair width relative to
the shoulders; this is the target for hair round 4.

### G06 · Ringlet detail macro · **P2**
**Closes:** ringlet structure (twist, thickness, taper and tip shape). In T-083 our lower curls read as ropes.
Aspect 1:1.
```text
The same handmade needle-felted wool plush doll girl as in the attached references, chibi proportions with a large head (about 38 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush, large round warm-brown eyes with dark upper lashes and soft brown brows, thin round brown-copper wire glasses, long warm chestnut-brown felted wool hair falling below the shoulders in soft ringlet curls, a soft side-swept fringe over the forehead, a high round top bun tied with a grey-blue hair band and decorated with small pink felt flowers, cream long-sleeved blouse with a rounded collar and gathered cuffs, dusty rose-mauve felt vest with dark embroidered motifs, two small pockets and tiny buttons, sage-green puffy bloomer shorts, brown shaggy fleece ankle boots with a cream fleece cuff. Macro close-up of three or four of the long chestnut-brown ringlet curls hanging beside the shoulder and the vest, showing their spiral twist, gradual taper toward soft rounded tips, varied lengths, felted wool surface with fine flyaway fibres. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:** the curl geometry at macro scale: twist period, radius, taper and tip shape.

### G07 · Vest and blouse macro · **P2**
**Closes:** the vest's felt surface (ours reads frayed), embroidery motifs, pockets, buttons and edge finish, and the
blouse collar. Aspect 4:3.
```text
The same handmade needle-felted wool plush doll girl as in the attached references, chibi proportions with a large head (about 38 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush, large round warm-brown eyes with dark upper lashes and soft brown brows, thin round brown-copper wire glasses, long warm chestnut-brown felted wool hair falling below the shoulders in soft ringlet curls, a soft side-swept fringe over the forehead, a high round top bun tied with a grey-blue hair band and decorated with small pink felt flowers, cream long-sleeved blouse with a rounded collar and gathered cuffs, dusty rose-mauve felt vest with dark embroidered motifs, two small pockets and tiny buttons, sage-green puffy bloomer shorts, brown shaggy fleece ankle boots with a cream fleece cuff. Macro close-up of the front of the dusty rose-mauve felt vest over the cream blouse: the smooth dense felt surface with soft short fibres, clean finished edges, the dark embroidered flower motifs, the two small pockets with tiny buttons, and the rounded cream blouse collar above it. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:** a material target for the vest (dense smooth felt, not frayed), the embroidery layout to
recreate, and the collar shape.

### G08 · Boots and shorts macro · **P2**
**Closes:** the cream fleece boot cuff (missing in our model), boot shape and fleece, bloomer shorts gathering at
the leg. Aspect 4:3.
```text
The same handmade needle-felted wool plush doll girl as in the attached references, chibi proportions with a large head (about 38 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush, large round warm-brown eyes with dark upper lashes and soft brown brows, thin round brown-copper wire glasses, long warm chestnut-brown felted wool hair falling below the shoulders in soft ringlet curls, a soft side-swept fringe over the forehead, a high round top bun tied with a grey-blue hair band and decorated with small pink felt flowers, cream long-sleeved blouse with a rounded collar and gathered cuffs, dusty rose-mauve felt vest with dark embroidered motifs, two small pockets and tiny buttons, sage-green puffy bloomer shorts, brown shaggy fleece ankle boots with a cream fleece cuff. Macro close-up of the legs and feet from a front three-quarter angle at knee height: the sage-green puffy bloomer shorts with their gathered leg openings, the bare felt legs, and both brown shaggy fleece ankle boots with the cream fleece cuff folded around the top and their rounded toes and soles clearly visible. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:** boot cuff colour and height, boot fleece length, the shape of the shorts' hem; the target for
the T-067 materials and garment details.

### G09 · Glasses close-up · **P2**
**Closes:** frame thickness, colour and finish, lens size relative to the eye, nose-bridge shape. Aspect 3:2.
```text
The same handmade needle-felted wool plush doll girl as in the attached references, chibi proportions with a large head (about 38 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush, large round warm-brown eyes with dark upper lashes and soft brown brows, thin round brown-copper wire glasses, long warm chestnut-brown felted wool hair falling below the shoulders in soft ringlet curls, a soft side-swept fringe over the forehead, a high round top bun tied with a grey-blue hair band and decorated with small pink felt flowers, cream long-sleeved blouse with a rounded collar and gathered cuffs, dusty rose-mauve felt vest with dark embroidered motifs, two small pockets and tiny buttons, sage-green puffy bloomer shorts, brown shaggy fleece ankle boots with a cream fleece cuff. Close-up of the eyes and glasses from the front at eye level, framed from brows to cheeks: the thin round brown-copper wire frames, their thin bridge over the nose, the lens size relative to the large brown eyes, subtle clear lens with only a faint soft reflection, the eyes fully visible through the lenses. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:** frame thickness and colour, lens radius versus eye size, and how the lens shading should look
(ours had grey goggle shading in 0.10.0).

### G10 · Thinking and pointing poses · **P3**
**Closes:** her signature acting (hand to chin while thinking, cheerful pointing) for the acting round.
Aspect 3:2.
```text
The same handmade needle-felted wool plush doll girl as in the attached references, chibi proportions with a large head (about 38 % of total height), pale porcelain-peach flocked felt skin with a soft rosy blush, large round warm-brown eyes with dark upper lashes and soft brown brows, thin round brown-copper wire glasses, long warm chestnut-brown felted wool hair falling below the shoulders in soft ringlet curls, a soft side-swept fringe over the forehead, a high round top bun tied with a grey-blue hair band and decorated with small pink felt flowers, cream long-sleeved blouse with a rounded collar and gathered cuffs, dusty rose-mauve felt vest with dark embroidered motifs, two small pockets and tiny buttons, sage-green puffy bloomer shorts, brown shaggy fleece ankle boots with a cream fleece cuff. Two full-body photographs side by side of the same doll on the same background, front three-quarter view: left, thinking with one hand touching the chin and eyes looking up, small closed smile; right, cheerfully pointing forward with the index finger, happy open smile. Feet fully in frame in both, no text. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, natural true colours.
```
**Expected output:** pose targets with readable hand shapes and the head tilt.

**Girl: already covered, do not generate:**
- Full turnaround, proportion sheet, happy/sad/surprised/angry expressions, hair construction, clothing breakdown.
- Hand and rig technical sheets (`ref_30`–`ref_46`).

---

## 3. Third character, white hair and blue dress: `girl_white_hair_blue_dress`

**What we already have:** the most complete set of the three (`assets/characters/girl_white_hair_blue_dress/references/views/`):
- **Views:** turnaround (`s02_*`), head views (`f14_head_*`).
- **Expressions:** expression and mouth series (`f14_*`, `m04_*`).
- **Hair:** construction, structure, clumps and fibre (`s02_hair_construction`, `h07_*`).
- **Clothes and body:** dress construction (`d09_*`), material swatches (`m10_*`), hands and feet (`p13_*`), poses
  (`t05_*`).

**Biggest gaps:**
- **Buns:** our buns are almost solid. The references show soft wispy surfaces, but there is no close-up of the buns
  from the side or back.
- **Hair ends:** our wave tips merge into ribbons (T-083), and there is no close-up of the separated wavy ends.
- **Bow:** owner decision: a blue felt **bow, no flower**. Several existing references (`h07_structure`, `f14_head_side`)
  show a flower-shaped accessory, so we need one clean bow reference.
- **Resting mouth:** owner decision: a closed soft smile at rest. The identity references show a small open smile.

**Attach for every prompt:**
- `docs/references/char_A_white_hair.webp`
- `assets/characters/girl_white_hair_blue_dress/references/views/id01_full.jpg`
- `assets/characters/girl_white_hair_blue_dress/references/views/s02_back.jpg`
- `assets/characters/girl_white_hair_blue_dress/references/views/h07_fibre.jpg`

**Identity lock (third):** the same handmade needle-felted wool plush doll girl as in the attached references, chibi
proportions with a large head, pale porcelain flocked felt skin with soft rosy cheeks, large round bright blue eyes
with long dark upper lashes, small soft brows, cream-ivory fluffy felted wool hair with two round fluffy top buns, a
thick soft fringe, long loose wavy locks reaching the waist with wispy fibre ends, one small dusty-blue felt bow
(a bow, not a flower) on the left side above the fringe, powder-blue cable-knit long-sleeved dress with a rounded
Peter Pan collar and a flared knitted skirt, white knit tights, tan caramel shaggy fleece ankle boots.

### W01 · Face close-up, front, closed soft smile (rest face) · **P1**
**Closes:** the owner-decided rest face, and the reference for her eye size, lashes and blush. Aspect 1:1.
```text
The same handmade needle-felted wool plush doll girl as in the attached references, chibi proportions with a large head, pale porcelain flocked felt skin with soft rosy cheeks, large round bright blue eyes with long dark upper lashes, small soft brows, cream-ivory fluffy felted wool hair with two round fluffy top buns, a thick soft fringe, long loose wavy locks reaching the waist with wispy fibre ends, one small dusty-blue felt bow (a bow, not a flower) on the left side above the fringe, powder-blue cable-knit long-sleeved dress with a rounded Peter Pan collar and a flared knitted skirt, white knit tights, tan caramel shaggy fleece ankle boots. Close-up portrait of the head and shoulders, camera exactly at eye level, perfectly frontal, the face filling two thirds of the frame, calm happy rest expression with a small closed soft smile (mouth closed, no teeth), large bright blue eyes looking straight at the camera, the thick soft fringe, the blue felt bow on the left side, both top buns visible at the top of the frame. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:** the definitive rest face (closed soft smile) with the bow; it replaces the open-smile identity
face as the target for her neutral.

### W02 · Blue felt bow close-up · **P1**
**Closes:** the conflicting references (flower vs bow); this fixes the accessory design per the owner's decision.
Aspect 1:1.
```text
The same handmade needle-felted wool plush doll girl as in the attached references, chibi proportions with a large head, pale porcelain flocked felt skin with soft rosy cheeks, large round bright blue eyes with long dark upper lashes, small soft brows, cream-ivory fluffy felted wool hair with two round fluffy top buns, a thick soft fringe, long loose wavy locks reaching the waist with wispy fibre ends, one small dusty-blue felt bow (a bow, not a flower) on the left side above the fringe, powder-blue cable-knit long-sleeved dress with a rounded Peter Pan collar and a flared knitted skirt, white knit tights, tan caramel shaggy fleece ankle boots. Macro close-up of the left side of the head above the fringe, focusing on the small dusty-blue felt bow: two rounded felt loops, a small wrapped centre knot and two short tails, soft dense felt surface with fine fibres, sitting in the cream fluffy hair, no flower shape. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:** an unambiguous bow design (shape, size relative to the bun, colour, placement).

### W03 · Top buns close-up, front 3/4 and back · **P1**
**Closes:** solid-looking buns. We need the wispy bun surface and the bun shape from several angles. Aspect 3:2.
```text
The same handmade needle-felted wool plush doll girl as in the attached references, chibi proportions with a large head, pale porcelain flocked felt skin with soft rosy cheeks, large round bright blue eyes with long dark upper lashes, small soft brows, cream-ivory fluffy felted wool hair with two round fluffy top buns, a thick soft fringe, long loose wavy locks reaching the waist with wispy fibre ends, one small dusty-blue felt bow (a bow, not a flower) on the left side above the fringe, powder-blue cable-knit long-sleeved dress with a rounded Peter Pan collar and a flared knitted skirt, white knit tights, tan caramel shaggy fleece ankle boots. Two close-up photographs side by side of the same doll's head on the same background: left, the two round top buns seen from the front three-quarter view; right, the same buns seen from behind. Both show soft round fluffy felted wool buns with a wispy fibrous surface, loose fine fibres forming a soft halo, the way the hair is gathered up into each bun, no hard edges, no text. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, natural true colours.
```
**Expected output:** bun size and spacing, surface fibre density and halo, and how the hair rises into the buns.

### W04 · Wavy hair ends close-up, side and back · **P1**
**Closes:** wave tips merging into ribbons (T-083). We need separated, wispy, tapering ends. Aspect 3:4.
```text
The same handmade needle-felted wool plush doll girl as in the attached references, chibi proportions with a large head, pale porcelain flocked felt skin with soft rosy cheeks, large round bright blue eyes with long dark upper lashes, small soft brows, cream-ivory fluffy felted wool hair with two round fluffy top buns, a thick soft fringe, long loose wavy locks reaching the waist with wispy fibre ends, one small dusty-blue felt bow (a bow, not a flower) on the left side above the fringe, powder-blue cable-knit long-sleeved dress with a rounded Peter Pan collar and a flared knitted skirt, white knit tights, tan caramel shaggy fleece ankle boots. Close-up photograph from behind and slightly to the side at waist height, framed from the shoulders to the hair ends: the long cream wavy locks hanging down the back over the blue knitted dress, each lock clearly separated, soft S-shaped waves, ends tapering into wispy fine fibres, varied lengths, no flat ribbon-like strands. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:** lock count, wave period, separation and tip taper; the target for her hair in hair round 4.

### W05 · Dress, tights and boots macro · **P2**
**Closes:** the knit pattern scale on the skirt and sleeves, collar shape, tights texture and boot fleece. This is
for building her garments; `d09`/`m10` show construction and swatches but not the real knit at doll scale.
Aspect 4:3.
```text
The same handmade needle-felted wool plush doll girl as in the attached references, chibi proportions with a large head, pale porcelain flocked felt skin with soft rosy cheeks, large round bright blue eyes with long dark upper lashes, small soft brows, cream-ivory fluffy felted wool hair with two round fluffy top buns, a thick soft fringe, long loose wavy locks reaching the waist with wispy fibre ends, one small dusty-blue felt bow (a bow, not a flower) on the left side above the fringe, powder-blue cable-knit long-sleeved dress with a rounded Peter Pan collar and a flared knitted skirt, white knit tights, tan caramel shaggy fleece ankle boots. Macro close-up from a front three-quarter angle at hip height: the powder-blue cable-knit skirt with its vertical cable pattern and flared hem, one sleeve cuff with the doll's small hand, the white knit tights, and the tan caramel shaggy fleece ankle boots with their rounded toes. Photorealistic studio photograph of a handmade needle-felted wool plush doll, real wool and felt fibre texture with a soft fuzzy halo of loose fibres, soft diffused key light from the front-left at 45 degrees, gentle fill light, subtle rim light, neutral light warm-grey seamless background, 85 mm lens, f/8, the whole subject in sharp focus, natural true colours, no text, no props.
```
**Expected output:** knit cable width and spacing at true scale, hem shape, tights knit, boot fleece length and
colour.

**Third character: already covered, do not generate:**
- Turnaround, expression and mouth sets.
- Hair construction and fibre close-up.
- Dress construction and material swatches.
- Hands and feet, rig and topology sheets.

---

## 4. Optional: all three together (staging and lighting) · **P3**

These close T-083 gaps 2, 4, 5 and 7: hand, object and gaze rarely meet; there is no classroom; and there is no
light guiding the eye. Generate them only after P1 and P2.

**Attach:**
- `docs/references/lineup.webp`
- `docs/references/char_A_white_hair.webp`
- `docs/references/char_B_brown_hair.webp`
- `docs/references/char_C_boy.jpg`
- `docs/references/classroom_watertable.webp`

### S01 · Handover with readable hands · **P3**
```text
The same three handmade needle-felted wool plush dolls from the attached references, exactly as designed (the white-haired girl with two buns and blue knitted dress, the brown-haired girl with glasses, vest and bun, and the sleepy boy in the mustard hoodie), standing around a low light-wood table in a cosy classroom. The boy holds out a small pale ceramic cup at chest height and the girl with glasses receives it with her fingertips, both hands and the cup clearly visible and not overlapping the faces, heads at a natural distance apart (not touching), all three looking at the cup, the white-haired girl watching with clasped hands. Soft daylight from a window on the left, gentle rim light on the wool hair, warm classroom background slightly out of focus, characters in sharp focus, 50 mm lens, photorealistic, no text.
```
**Expected output:** a staging target for the cup handover: readable grasp, the distance between heads (ours now
touch) and a shared eye line.

### S02 · Window-lit three-shot at the water table · **P3**
```text
The same three handmade needle-felted wool plush dolls from the attached references, exactly as designed, seated around a low wooden water table in a cosy classroom, faces and hands at table level, a small paper boat floating on the water between them, all three looking at the boat. Soft window daylight from the left as key light, bright soft rim light catching the fuzzy wool hair, warm shelves and toys softly out of focus behind them, portrait framing, 50 mm lens, photorealistic, no text.
```
**Expected output:** a lighting and composition target (window key, rim on the hair, focus on faces and hands)
for the shot-layout study that T-083 recommends.

---

## Summary

| Character | P1 | P2 | P3 | Total |
| --- | ---: | ---: | ---: | ---: |
| Boy | 6 (B01–B06) | 4 (B07–B10) | 2 (B11, B12) | 12 |
| Girl | 5 (G01–G05) | 4 (G06–G09) | 1 (G10) | 10 |
| Third | 4 (W01–W04) | 1 (W05) | 0 | 5 |
| All three | 0 | 0 | 2 (S01, S02) | 2 |

**Recommended order:**
1. All P1 images (15). These directly feed face round 3 (eyes, lids, rest faces), hair round 4 (fringe, crowns,
   buns, wave ends) and the boy's backpack.
2. P2 (9), for the T-067 materials and garment details.
3. P3 when we reach acting and shot layout.
