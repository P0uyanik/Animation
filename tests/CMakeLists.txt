add_executable(plush_tests test_main.cpp test_engine.cpp)
target_link_libraries(plush_tests PRIVATE plush_scene plush_render doctest::doctest plush_warnings)
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
