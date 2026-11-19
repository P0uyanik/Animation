# plush-render: the animation bake hand-off (--bake). The image renderer was removed in T-142.
add_executable(plush-render main.cpp)
target_link_libraries(plush-render PRIVATE plush_scene plush_warnings)
