# Milestone 2026-11-14: M3.1, generic facial engine completion

| Item | Result |
| --- | --- |
| Status | Experimental; technically verified; visually reviewed by me; **not approved**; nothing published |
| Blink | Engine follows the exported in-between chain (any character, any number of morph blocks per name); girl lid clearance +0.51 mm over the whole blink (linear morph: −10.7 mm) |
| Jaw | Package `expression_bones`; engine rotates the listed bones by weight × degrees. Girl: MouthOpen 10° / 14.2 mm chin, Laugh 6° / 7.5 mm, Smile 2° / 2.3 mm. Packages without metadata stay morph-only; a missing bone fails loading |
| Blink timing | Package `blink` → `LifeParams` (defaults unchanged). Girl 3.2 s / 0.26 s blinks, boy 3.6 s / 0.22 s; a scene interval overrides |
| Oval eyes | Gaze envelope widens the lid clearance only when needed. G03: 0 intersections in all states and gaze cases (was 606); Blink 0% at every gaze. Girl unchanged |
| Boy | Unchanged: legacy modules not modified; `verify_charsys` PASS; `ctest` 4/4 with the frozen image regressions; 1.0.0 package without new metadata keeps the defaults |
| Tests added | in-between chain weights; geometric blink clearance (chain vs linear); jaw angle and chin drop for 4 expressions; per-character timing (+ scene override, + default curve identical) |
| Open | piecewise in-betweens (25% stops); single-axis jaw; oval eyes limited to the configured gaze range; engine materials lack the eye and mouth-interior shading |

Agents: one primary agent, no subagents. Token counts are not exposed to me and are not estimated.
