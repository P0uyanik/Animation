# Engine modules. Dependencies point downward only:
#   core <- geom <- anim (secondary motion reads its JSON block) <- fuzz <- model <- scene ;  render depends on core + geom only.
function(plush_module name)
  cmake_parse_arguments(M "" "" "SOURCES;DEPS" ${ARGN})
  add_library(${name} STATIC ${M_SOURCES})
  target_include_directories(${name} PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
  target_link_libraries(${name} PUBLIC ${M_DEPS} PRIVATE plush_warnings)
endfunction()

plush_module(plush_core SOURCES core/core.cpp DEPS glm::glm Threads::Threads)
plush_module(plush_geom SOURCES geom/json_io.cpp DEPS plush_core nlohmann_json::nlohmann_json)
plush_module(plush_anim SOURCES anim/animation.cpp anim/secondary.cpp anim/body_mechanics.cpp anim/principles.cpp anim/personality.cpp DEPS plush_geom)
plush_module(plush_fuzz SOURCES fuzz/fuzz.cpp DEPS plush_geom)
plush_module(plush_model SOURCES model/sdf.cpp model/character.cpp model/imported_character.cpp model/clip.cpp DEPS plush_geom plush_anim plush_fuzz)
plush_module(plush_scene SOURCES scene/asset_library.cpp scene/scene.cpp scene/actions.cpp scene/shot_bake.cpp scene/clip_layers.cpp scene/emotion.cpp scene/face_layer.cpp scene/interaction.cpp scene/collision.cpp DEPS plush_model)
plush_module(plush_render SOURCES render/bsdf.cpp render/pathtracer.cpp render/image.cpp DEPS plush_geom embree plush_stb)

if(OpenImageDenoise_FOUND)
  target_link_libraries(plush_render PRIVATE OpenImageDenoise)
  target_compile_definitions(plush_render PRIVATE PLUSH_HAS_OIDN=1)
endif()
