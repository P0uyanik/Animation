find_package(GLEW REQUIRED)
add_executable(plush-studio main.cpp)
target_link_libraries(plush-studio PRIVATE plush_scene plush_render plush_imgui GLEW::GLEW plush_warnings)
# The studio launches the command-line renderer for animation jobs.
target_compile_definitions(plush-studio PRIVATE PLUSH_RENDER_CLI="$<TARGET_FILE:plush-render>")
add_dependencies(plush-studio plush-render)
