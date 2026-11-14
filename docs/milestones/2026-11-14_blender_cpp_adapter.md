# Milestone 2026-11-14: Blender → C++ character adapter

| Item | Result |
| --- | --- |
| Changed | New: exporter, rig profiles (Rigify + fixture), engine behaviour table, C++ importer, scene loading branch (+1 field), behaviour tests, exporter tests, fixture script, package doc, 2 test packages |
| Reused | Existing engine actions, life layer, IK, aim, hand pose, skinning, morphs (unchanged); charsys master 1.0.0 (read-only); `verify_charsys`; `ctest` regressions |
| Reusable for other characters | Exporter and importer are profile-driven (no boy names or dimensions); new rig families need a profile; new character kinds need a profile plus behaviour requirements |
| Supported on both packages (tested) | rest skinning, reach/IK, look-at, morph expressions, idle |
| Partial | walk on the short-legged fixture (8/59 sliding frames; fixed 0.11 m step) |
| Unsupported (tested, reasons documented) | grasp (engine hand convention vs A-pose; the fixture has no fingers), life-layer blink (lid bones only) |
| Tests | `ctest` 4/4 (unit incl. 143 imported-character assertions, 3 image regressions unchanged); exporter tests 8/8; `verify_charsys` 67/0 |
| Scope note | The fixture is an engineering test, not a second production character |
| Protected | v6, 1.0.0, frozen baselines unchanged; no version published |
| Next | Go-ahead for 4 small generic engine fixes; face expression layer; H26 irregularity |
