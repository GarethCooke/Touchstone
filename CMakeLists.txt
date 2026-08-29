cmake_minimum_required(VERSION 3.20)

project(touchstone
    VERSION 0.1.0
    DESCRIPTION "A C++20 pricing-and-risk library for European vanilla options"
    HOMEPAGE_URL "https://github.com/GarethCooke/Touchstone"
    LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE RelWithDebInfo CACHE STRING "Build type" FORCE)
endif()

option(TOUCHSTONE_BUILD_TESTS "Build the test suite" ON)
option(TOUCHSTONE_WARNINGS_AS_ERRORS "Fail the build on any warning" ON)

# --- Warnings ---------------------------------------------------------------
# Tech-decision B1: GCC and Clang both green, warnings as errors. Those two are
# what CI runs and what this project claims. The MSVC branch is here so the
# owner's Windows checkout configures rather than dying on unknown flags; it is
# not exercised by CI and nothing claims it is.
add_library(touchstone_warnings INTERFACE)
if(MSVC)
    target_compile_options(touchstone_warnings INTERFACE /W4 /permissive-)
    if(TOUCHSTONE_WARNINGS_AS_ERRORS)
        target_compile_options(touchstone_warnings INTERFACE /WX)
    endif()
else()
    target_compile_options(touchstone_warnings INTERFACE
        -Wall
        -Wextra
        -Wpedantic
        -Wshadow
        -Wconversion
        -Wsign-conversion
        -Wold-style-cast
        -Wcast-qual
        -Wdouble-promotion
        -Wformat=2
        -Wnon-virtual-dtor
        -Woverloaded-virtual
        -Wnull-dereference
        -Wunused)
    if(TOUCHSTONE_WARNINGS_AS_ERRORS)
        target_compile_options(touchstone_warnings INTERFACE -Werror)
    endif()
endif()

# --- The library ------------------------------------------------------------
add_library(touchstone STATIC
    src/black_scholes.cpp)
add_library(touchstone::touchstone ALIAS touchstone)

target_include_directories(touchstone
    PUBLIC $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>)
target_link_libraries(touchstone PRIVATE touchstone_warnings)

# --- Header self-containment ------------------------------------------------
# One generated translation unit per public header, including only that header.
# A header that quietly depends on something its includer happened to pull in
# first fails here rather than in the first consumer that includes it alone —
# which at T4 is the Emscripten binding, the least convenient place to find out.
set(TOUCHSTONE_PUBLIC_HEADERS
    black_scholes.hpp
    normal.hpp)

set(touchstone_header_check_sources "")
foreach(header IN LISTS TOUCHSTONE_PUBLIC_HEADERS)
    string(MAKE_C_IDENTIFIER "${header}" header_stem)
    set(generated "${CMAKE_CURRENT_BINARY_DIR}/header_check/${header_stem}.cpp")
    file(CONFIGURE OUTPUT "${generated}" CONTENT "#include <touchstone/${header}>\n")
    list(APPEND touchstone_header_check_sources "${generated}")
endforeach()

add_library(touchstone_header_check OBJECT ${touchstone_header_check_sources})
target_link_libraries(touchstone_header_check PRIVATE touchstone touchstone_warnings)

# --- Tests ------------------------------------------------------------------
if(TOUCHSTONE_BUILD_TESTS)
    enable_testing()
    add_subdirectory(third_party)
    add_subdirectory(tests)
endif()
