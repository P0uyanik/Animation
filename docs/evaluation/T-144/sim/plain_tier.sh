#!/bin/bash
# runs the check_all python-tier test list in tree $1, writes $2
cd "$1"
: > "$2"
for t in pipeline/clips/tests/test_clip_files.py:--selftest tools/fidelity/tests/test_ci.py tools/regression/tests/test_gate_tools.py pipeline/production/tests/test_run_shot_current.py tools/animcheck/tests/test_animcheck.py pipeline/charsys/tests/test_versions.py tools/fidelity/tests/test_metrics.py tools/fidelity/tests/test_metrics_v2.py tools/lipsync/test_lipsync.py tools/tests/test_version_switch.py pipeline/charsys/tests/test_materials_r2.py pipeline/production/tests/test_sets.py tools/fit/tests/test_fit.py tests/props/test_props.py pipeline/charsys/tests/test_face_v3.py pipeline/charsys/tests/test_face_v3b.py pipeline/charsys/tests/test_face_v4.py pipeline/charsys/tests/test_hair_r4.py pipeline/charsys/tests/test_hair_r5.py pipeline/charsys/tests/test_hands_r2.py pipeline/charsys/tests/test_guard_allowlist.py pipeline/charsys/tests/test_garments_r3.py pipeline/charsys/tests/test_expressions_r3.py tests/acting/test_girl_signature.py tests/acting/test_e909_beats.py tests/acting/test_boy_signature.py pipeline/charsys/tests/test_boy2_face.py tools/ci/tests/test_t127_shards.py tools/tests/test_task_kit.py pipeline/charsys/tests/test_store.py pipeline/charsys/tests/test_asset_store_guard.py pipeline/charsys/tests/test_material_presets.py pipeline/charsys/tests/test_skin_presets.py pipeline/charsys/tests/test_face_v2.py pipeline/charsys/tests/test_hair_v3.py tools/review/tests/test_recipe.py; do
  f=${t%%:*}; arg=""; [[ $t == *:* ]] && arg=${t##*:}
  timeout 600 python3 $f $arg > "$2.$(basename $f).log" 2>&1; rc=$?
  echo "$f rc=$rc" >> "$2"
done
