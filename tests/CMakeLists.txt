add_executable(plush_tests test_main.cpp test_engine.cpp test_imported_character.cpp test_clips.cpp test_emotions.cpp
                           test_asset_library.cpp test_secondary.cpp test_interaction.cpp test_face_layer.cpp
                           test_body_mechanics.cpp test_anim_principles.cpp
                           test_personality.cpp test_collision.cpp test_timing_profile.cpp test_reaction.cpp
                           test_emotion_blend.cpp test_reaction_playback.cpp test_bake_golden.cpp test_verbs.cpp
                           test_hand_shapes.cpp test_gaze_legibility.cpp)
target_link_libraries(plush_tests PRIVATE plush_scene doctest::doctest plush_warnings)
if(PLUSH_BUILD_RENDERER)
  # Engine path tracer unit tests (5 doctest cases): only with the frozen renderer (T-085).
  target_sources(plush_tests PRIVATE test_render.cpp)
  target_link_libraries(plush_tests PRIVATE plush_render)
endif()
target_compile_definitions(plush_tests PRIVATE PLUSH_SOURCE_DIR="${CMAKE_SOURCE_DIR}")
# Plush Studio production workflow (no OpenGL), built when the studio is built.
if(TARGET plush_shot_workflow)
  target_sources(plush_tests PRIVATE test_shot_workflow.cpp)
  target_link_libraries(plush_tests PRIVATE plush_shot_workflow)
  target_compile_definitions(plush_tests PRIVATE PLUSH_RENDER_CLI="$<TARGET_FILE:plush-render>")
endif()
add_test(NAME plush_tests COMMAND plush_tests)

if(NOT PLUSH_BUILD_RENDERER)
  # Reported as "Not Run (Skipped)" by ctest: the renderer tests are skipped, not silently dropped.
  add_test(NAME renderer_tests_skipped
    COMMAND ${CMAKE_COMMAND} -E echo
            "SKIPPED: PLUSH_BUILD_RENDERER=OFF - 5 path tracer doctest cases (tests/test_render.cpp) and 3 image regressions (regression_milestone01, regression_face_neutral, regression_lineup_abc) not built")
  set_tests_properties(renderer_tests_skipped PROPERTIES SKIP_REGULAR_EXPRESSION "SKIPPED: PLUSH_BUILD_RENDERER=OFF")
  return()
endif()

# Look regression: Milestone 01 is frozen (scene + character copy) and must keep rendering the same.
# Intentional look changes in the engine require re-baselining the reference image (see DEVELOPMENT_LOG.md).
add_test(NAME regression_milestone01
  COMMAND plush-render ${CMAKE_SOURCE_DIR}/content/scenes/milestone01_classroom.scene.json
          --frame 24 --out ${CMAKE_BINARY_DIR}/regression_m01_f24.png --width 320 --height 180 --spp 16 --preview
          --compare ${CMAKE_SOURCE_DIR}/tests/regression/m01_f24_320x180.png --max-rmse 0.03)

# Character consistency: the current character's neutral face must not change unintentionally.
add_test(NAME regression_face_neutral
  COMMAND plush-render ${CMAKE_SOURCE_DIR}/content/scenes/test_face.scene.json
          --frame 1 --out ${CMAKE_BINARY_DIR}/regression_face_neutral.png --width 200 --height 200 --spp 16 --preview
          --compare ${CMAKE_SOURCE_DIR}/tests/regression/face_neutral_200.png --max-rmse 0.03)

# Character consistency for the three iteration-3 characters (A, B, C): unintended changes fail this test.
add_test(NAME regression_lineup_abc
  COMMAND plush-render ${CMAKE_SOURCE_DIR}/content/scenes/test_lineup.scene.json
          --frame 1 --out ${CMAKE_BINARY_DIR}/regression_lineup_abc.png --width 320 --height 240 --spp 16 --preview
          --compare ${CMAKE_SOURCE_DIR}/tests/regression/lineup_abc_320x240.png --max-rmse 0.03)
