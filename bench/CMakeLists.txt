# The timing harness. Built wherever the tests are, under the same warnings, so
# that it keeps compiling; never run by ctest, because a time taken on a shared
# CI runner describes the runner.
add_executable(touchstone_timing timing.cpp)
target_link_libraries(touchstone_timing PRIVATE touchstone::touchstone touchstone_warnings)
