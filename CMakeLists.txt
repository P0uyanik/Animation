cmake_minimum_required(VERSION 3.24)
project(PlushStudio VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
endif()

option(PLUSH_BUILD_STUDIO "Build the desktop studio application (needs OpenGL + GLFW)" ON)
option(PLUSH_BUILD_TESTS "Build unit tests" ON)
# The engine path tracer (engine/render/, frozen per TD-43) is the only user of Embree and Open Image Denoise.
# OFF (default): engine core, animation, scene, bake (plush-render --bake) and tests build without them;
# renderer tests are skipped and reported. ON: the renderer, its tests, the image regressions and plush-studio.
option(PLUSH_BUILD_RENDERER "Build the frozen engine path tracer (needs Embree 4; OIDN optional)" OFF)

include(cmake/Dependencies.cmake)

# Common warning settings for our own code only.
add_library(plush_warnings INTERFACE)
if(MSVC)
  target_compile_options(plush_warnings INTERFACE /W4 /permissive- /utf-8)
else()
  target_compile_options(plush_warnings INTERFACE -Wall -Wextra -Wno-unused-parameter -Wno-missing-field-initializers)
endif()

add_subdirectory(engine)
add_subdirectory(apps/render-cli)
add_subdirectory(apps/export-obj)  # comparison/export utility; does not change the engine
if(PLUSH_BUILD_STUDIO)
  add_subdirectory(apps/studio)
endif()
if(PLUSH_BUILD_TESTS)
  enable_testing()
  add_subdirectory(tests)
endif()
