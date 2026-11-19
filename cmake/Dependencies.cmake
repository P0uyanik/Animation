# Third-party dependencies.
# Preferred source: system packages (apt on Linux) or vcpkg (Windows, see vcpkg.json).
# Small libraries fall back to FetchContent when not installed.
include(FetchContent)

find_package(Threads REQUIRED)
find_package(glm CONFIG REQUIRED)           # math (MIT)
find_package(nlohmann_json 3 CONFIG REQUIRED)

# stb (PNG read/write for the studio's screenshots and production frame view)
find_path(PLUSH_STB_INCLUDE stb_image_write.h PATH_SUFFIXES stb)
if(NOT PLUSH_STB_INCLUDE)
  FetchContent_Declare(stb GIT_REPOSITORY https://github.com/nothings/stb.git GIT_TAG 5c205738c191bcb0abc65c4febfa9bd25ff35234)
  FetchContent_MakeAvailable(stb)
  set(PLUSH_STB_INCLUDE ${stb_SOURCE_DIR})
endif()
add_library(plush_stb INTERFACE)
target_include_directories(plush_stb SYSTEM INTERFACE ${PLUSH_STB_INCLUDE})

if(PLUSH_BUILD_TESTS)
  find_package(doctest CONFIG QUIET)
  if(NOT doctest_FOUND)
    FetchContent_Declare(doctest GIT_REPOSITORY https://github.com/doctest/doctest.git GIT_TAG v2.4.11)
    FetchContent_MakeAvailable(doctest)
  endif()
endif()

if(PLUSH_BUILD_STUDIO)
  find_package(OpenGL REQUIRED)
  find_package(glfw3 3.3 CONFIG REQUIRED)
  # Dear ImGui, docking branch, pinned to a commit for reproducible builds.
  FetchContent_Declare(imgui GIT_REPOSITORY https://github.com/ocornut/imgui.git GIT_TAG cf53467ab0db7a783f04b32dd9160e6aa5b720ef)
  FetchContent_MakeAvailable(imgui)
  add_library(plush_imgui STATIC
    ${imgui_SOURCE_DIR}/imgui.cpp ${imgui_SOURCE_DIR}/imgui_draw.cpp ${imgui_SOURCE_DIR}/imgui_tables.cpp
    ${imgui_SOURCE_DIR}/imgui_widgets.cpp ${imgui_SOURCE_DIR}/imgui_demo.cpp
    ${imgui_SOURCE_DIR}/backends/imgui_impl_glfw.cpp ${imgui_SOURCE_DIR}/backends/imgui_impl_opengl3.cpp)
  target_include_directories(plush_imgui SYSTEM PUBLIC ${imgui_SOURCE_DIR} ${imgui_SOURCE_DIR}/backends)
  target_link_libraries(plush_imgui PUBLIC glfw OpenGL::GL)
endif()
