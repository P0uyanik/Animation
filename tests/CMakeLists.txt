add_executable(plush_tests test_main.cpp test_engine.cpp test_imported_character.cpp test_clips.cpp test_emotions.cpp
                           test_asset_library.cpp)
target_link_libraries(plush_tests PRIVATE plush_scene plush_render doctest::doctest plush_warnings)
target_compile_definitions(plush_tests PRIVATE PLUSH_SOURCE_DIR="${CMAKE_SOURCE_DIR}")
# Plush Studio production workflow (no OpenGL), built when the studio is built.
if(TARGET plush_shot_workflow)
  target_sources(plush_tests PRIVATE test_shot_workflow.cpp)
  target_link_libraries(plush_tests PRIVATE plush_shot_workflow)
  target_compile_definitions(plush_tests PRIVATE PLUSH_RENDER_CLI="$<TARGET_FILE:plush-render>")
endif()
add_test(NAME plush_tests COMMAND plush_tests)

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
