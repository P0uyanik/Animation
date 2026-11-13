# Iteration 4 — Phase A: references vs Iteration 3

Evidence: `docs/iteration4/phaseA_ref_vs_it3.png` (reference | Iteration 3, for A, B, C).
References on disk (`docs/references/`): the three character sheets, the lineup, three classroom stills and
**one** animation video (`video_watertable.mp4`). **The second animation reference video mentioned in the brief
is not in this workspace** (only one video was ever uploaded); nothing below is based on it.

## Measured on the front views (fractions of total height)
| Measure | Reference A | Iteration 3 A | Verdict |
| --- | --- | --- | --- |
| Head incl. hair, excluding buns | ~0.28 | ~0.27 | close |
| Dress (neck → hem) | ~0.33 | ~0.34 | close, but shape differs (see below) |
| Legs + boots | ~0.26 | ~0.29 | ours slightly long |
| Eye opening width / face width | ~0.25 | ~0.17 | **ours far too small** |
| Eye centre spacing / face width | ~0.50 | ~0.38 | **ours too close** |
| Eye line between fringe and chin | ~0.53 | ~0.36 | **our lower face too long, fringe too low** |

Overall proportions were not the main problem; **faces, hair mass and garment shapes were.**

## Differences by character (cause in brackets)
**All:** eyes too small and too close, lower face too long, cheeks not full enough at the bottom, nose too faint,
mouth too far from the eyes [geometry]. Skin reads plastic [shading: no subsurface scattering].

**A:** hair is a set of separate cords with gaps instead of a soft mass with locks on its surface; side volume too
narrow; buns too small [geometry]. Dress is a straight tube; the reference is a short bodice with a flared bell skirt
and a hem band [geometry]. Bow fine. Boots fine.

**B:** glasses too large (cover the cheeks) and the lenses glare [geometry + material]. Hair volume around the face
too thin; curls too regular; side-swept fringe missing [geometry]. Vest fragmented; the reference is one V-neck
piece with motifs [geometry]. Shorts fine, slightly long.

**C:** hair volume too small and cap-like; reference spikes are long, irregular, flaring out and down [geometry].
Hoodie and trousers too slim; reference is loose and bulky [geometry]. Half-lidded look already right.

## Required improvements (implementation order)
1. Face rig scale-up: bigger, wider-set eyes (with lids, lashes, sockets), shorter lower face, fuller low cheeks, nose.
2. Hair = soft felted **mass volume** + locks on its surface; larger silhouettes (A side volume and buns, B curls
   around the face, C flaring spikes).
3. Garment silhouettes: A bodice + bell skirt + hem band; B single V-neck vest; C loose hoodie and wide joggers.
4. Then materials (skin subsurface scattering, hair halo integration), hands (finger bones), animation.
