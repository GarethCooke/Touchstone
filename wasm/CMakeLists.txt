# The WebAssembly artifact: one .wasm and the ES module that loads it.
#
#   touchstone.mjs   export default createTouchstone(): Promise<module>
#   touchstone.wasm  fetched by the .mjs from beside itself
#
# Built only under Emscripten (emcmake cmake ...); the root CMakeLists.txt adds
# this directory then and not otherwise.

add_executable(touchstone_wasm binding.cpp)

set_target_properties(touchstone_wasm PROPERTIES
    OUTPUT_NAME touchstone
    SUFFIX ".mjs")

target_compile_definitions(touchstone_wasm PRIVATE TOUCHSTONE_VERSION="${PROJECT_VERSION}")
target_link_libraries(touchstone_wasm PRIVATE touchstone touchstone_warnings)

target_link_options(touchstone_wasm PRIVATE
    -lembind
    # An ES module exporting a factory, so that the site and Node both import it
    # and nothing is put on the global object.
    -sMODULARIZE=1
    -sEXPORT_ES6=1
    -sEXPORT_NAME=createTouchstone
    # The browser's main thread, a worker for a demo that computes off it, and
    # Node for the smoke test.
    -sENVIRONMENT=web,worker,node
    # A grid's whole solution surface is megabytes; a fixed heap would make the
    # largest grid a demo may ask for a build-time decision.
    -sALLOW_MEMORY_GROWTH=1
    # Nothing here reads or writes a file.
    -sFILESYSTEM=0
    # The throwing names, put in place of the error-returning ones.
    "--post-js=${CMAKE_CURRENT_SOURCE_DIR}/errors.post.js")

set_property(TARGET touchstone_wasm APPEND PROPERTY
    LINK_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/errors.post.js")
