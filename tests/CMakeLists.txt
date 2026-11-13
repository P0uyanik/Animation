add_executable(plush_tests test_main.cpp test_engine.cpp)
target_link_libraries(plush_tests PRIVATE plush_scene plush_render doctest::doctest plush_warnings)
add_test(NAME plush_tests COMMAND plush_tests)
