# Vendored single headers, carried as SYSTEM includes so that this project's
# warnings-as-errors apply to this project's code and to nothing else.
#
# Only the test executable links this. Neither header is reachable from
# `include/touchstone/`, so nothing here can reach the library, the WASM
# artifact at T4, or anything the site vendors. Provenance — version, URL,
# SHA-256 — is in README.md beside them.
add_library(touchstone_vendor INTERFACE)
target_include_directories(touchstone_vendor SYSTEM INTERFACE ${CMAKE_CURRENT_SOURCE_DIR})
