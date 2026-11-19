# T-128 opt-in fast build: ccache compiler launcher + mold linker. NOT used by default or by the gate.
# Enable with a preset (cmake --preset fast-dev) or:
#   cmake -B build -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=cmake/opt_in/fast_build.cmake
# Each tool is used only when found; missing tools leave the normal build untouched.
# Disable per tool: -DPLUSH_FAST_CCACHE=OFF / -DPLUSH_FAST_MOLD=OFF.
option(PLUSH_FAST_CCACHE "T-128 opt-in: use ccache as compiler launcher" ON)
option(PLUSH_FAST_MOLD "T-128 opt-in: link with mold (GCC/Clang on Linux)" ON)

if(PLUSH_FAST_CCACHE AND NOT CMAKE_CXX_COMPILER_LAUNCHER)
  find_program(PLUSH_CCACHE_EXE ccache)
  if(PLUSH_CCACHE_EXE)
    set(CMAKE_C_COMPILER_LAUNCHER "${PLUSH_CCACHE_EXE}" CACHE STRING "" FORCE)
    set(CMAKE_CXX_COMPILER_LAUNCHER "${PLUSH_CCACHE_EXE}" CACHE STRING "" FORCE)
    message(STATUS "Plush (T-128 opt-in): ccache ${PLUSH_CCACHE_EXE}")
  endif()
endif()

if(PLUSH_FAST_MOLD AND CMAKE_SYSTEM_NAME STREQUAL "Linux" AND NOT CMAKE_HOST_WIN32)
  find_program(PLUSH_MOLD_EXE mold)
  if(PLUSH_MOLD_EXE)
    add_link_options(-fuse-ld=mold)
    message(STATUS "Plush (T-128 opt-in): mold ${PLUSH_MOLD_EXE}")
  endif()
endif()
