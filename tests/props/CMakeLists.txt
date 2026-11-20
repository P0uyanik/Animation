# T-163 standalone prop test (outside tests/CMakeLists.txt, which is frozen for this task):
#   cmake -S tests/props -B build/props -G Ninja -DPLUSH_BUILD_STUDIO=OFF && cmake --build build/props && ctest --test-dir build/props
# It builds the engine's plush_scene once through the repository root and links one doctest binary against it.
cmake_minimum_required(VERSION 3.24)
project(PlushPropTests LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(PLUSH_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(PLUSH_BUILD_STUDIO OFF CACHE BOOL "" FORCE)
get_filename_component(PLUSH_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
add_subdirectory(${PLUSH_ROOT} ${CMAKE_BINARY_DIR}/engine_root EXCLUDE_FROM_ALL)
find_package(doctest CONFIG REQUIRED)
enable_testing()
add_executable(plush_prop_tests test_prop_verbs.cpp)
target_link_libraries(plush_prop_tests PRIVATE plush_scene doctest::doctest plush_warnings)
target_compile_definitions(plush_prop_tests PRIVATE PLUSH_SOURCE_DIR="${PLUSH_ROOT}")
add_test(NAME plush_prop_tests COMMAND plush_prop_tests)
