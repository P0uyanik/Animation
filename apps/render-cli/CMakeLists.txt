# plush-render: scene renderer (PLUSH_BUILD_RENDERER=ON) and the animation bake hand-off (--bake, always built).
add_executable(plush-render main.cpp)
target_link_libraries(plush-render PRIVATE plush_scene plush_warnings)
if(PLUSH_BUILD_RENDERER)
  target_link_libraries(plush-render PRIVATE plush_render)
  target_compile_definitions(plush-render PRIVATE PLUSH_HAS_RENDERER=1)
endif()
