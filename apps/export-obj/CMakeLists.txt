# Exports an evaluated scene frame as OBJ + MTL (meshes, plus thick curves as tubes) for external comparison tools.
add_executable(plush-export-obj main.cpp)
target_link_libraries(plush-export-obj PRIVATE plush_scene plush_warnings)
