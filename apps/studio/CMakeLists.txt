# Production workflow (shot discovery, jobs, status, frame mapping, merge-save): no UI, unit-tested in plush_tests.
add_library(plush_shot_workflow STATIC shot_workflow.cpp)
if(WIN32)
  target_sources(plush_shot_workflow PRIVATE shot_job_windows.cpp)
endif()
target_include_directories(plush_shot_workflow PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(plush_shot_workflow PUBLIC plush_scene PRIVATE plush_warnings)
if(NOT PLUSH_BUILD_STUDIO)
  return()
endif()
find_package(GLEW REQUIRED)
add_executable(plush-studio main.cpp image_io.cpp preview_texture.cpp)
target_link_libraries(plush-studio PRIVATE plush_scene plush_stb plush_imgui plush_shot_workflow GLEW::GLEW plush_warnings)
# The studio launches plush-render --bake (engine bake) for production jobs.
target_compile_definitions(plush-studio PRIVATE PLUSH_RENDER_CLI="$<TARGET_FILE:plush-render>")
# The production workflow runs pipeline/production/run_shot.py of this source tree.
target_compile_definitions(plush-studio PRIVATE PLUSH_SOURCE_DIR="${CMAKE_SOURCE_DIR}")
add_dependencies(plush-studio plush-render)
