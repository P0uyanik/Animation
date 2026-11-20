add_executable(plush_tests test_main.cpp test_engine.cpp test_imported_character.cpp test_clips.cpp test_emotions.cpp
                           test_asset_library.cpp test_secondary.cpp test_interaction.cpp test_face_layer.cpp
                           test_body_mechanics.cpp test_anim_principles.cpp
                           test_personality.cpp test_collision.cpp test_timing_profile.cpp test_reaction.cpp
                           test_emotion_blend.cpp test_reaction_playback.cpp test_bake_golden.cpp test_verbs.cpp
                           test_hand_shapes.cpp test_gaze_legibility.cpp test_framing.cpp
                           test_reach_mechanics.cpp test_grasp_contact.cpp
                           test_blink_schedule.cpp test_gaze_chain.cpp)
target_link_libraries(plush_tests PRIVATE plush_scene doctest::doctest plush_warnings)
target_compile_definitions(plush_tests PRIVATE PLUSH_SOURCE_DIR="${CMAKE_SOURCE_DIR}")
# Plush Studio production workflow (no OpenGL), built when the studio is built.
if(TARGET plush_shot_workflow)
  target_sources(plush_tests PRIVATE test_shot_workflow.cpp)
  target_link_libraries(plush_tests PRIVATE plush_shot_workflow)
  target_compile_definitions(plush_tests PRIVATE PLUSH_RENDER_CLI="$<TARGET_FILE:plush-render>")
endif()
add_test(NAME plush_tests COMMAND plush_tests)


# T-163 starter prop library: one verb test per prop (own doctest main, so its own binary).
add_executable(plush_prop_tests props/test_prop_verbs.cpp)
target_link_libraries(plush_prop_tests PRIVATE plush_scene doctest::doctest plush_warnings)
target_compile_definitions(plush_prop_tests PRIVATE PLUSH_SOURCE_DIR="${CMAKE_SOURCE_DIR}")
add_test(NAME plush_prop_tests COMMAND plush_prop_tests)
