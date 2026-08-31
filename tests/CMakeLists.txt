add_executable(touchstone_tests
    doctest_main.cpp
    golden_file.cpp
    rng_fixture.cpp
    statistics.cpp
    test_normal.cpp
    test_rng.cpp
    test_monte_carlo.cpp
    test_euler.cpp
    test_closed_form.cpp
    test_parity.cpp
    test_limits.cpp
    test_associations.cpp
    test_tridiagonal.cpp
    test_pde.cpp
    test_implied_vol.cpp
    test_bump_greeks.cpp
    test_american.cpp
    test_three_way.cpp
    american_file.cpp)

target_link_libraries(touchstone_tests
    PRIVATE
        touchstone::touchstone
        touchstone_vendor
        touchstone_warnings)

# CHECK_THROWS_AS discards the expression's value, and every entry point in the
# library is [[nodiscard]]. This is doctest's own switch for that: it casts the
# expression to void, which is what the standard blesses as "deliberately
# ignored". The alternative is a static_cast at every call site.
target_compile_definitions(touchstone_tests PRIVATE DOCTEST_CONFIG_VOID_CAST_EXPRESSIONS)

target_compile_definitions(touchstone_tests
    PRIVATE TOUCHSTONE_SWEEP_SCALE=${TOUCHSTONE_SWEEP_SCALE})

# The tests read the golden file from the source tree, so the build tree can
# live anywhere. TOUCHSTONE_GOLDEN_PATH in the environment overrides it, which
# is how CI checks a regenerated file against the same tests.
target_compile_definitions(touchstone_tests
    PRIVATE TOUCHSTONE_GOLDEN_PATH="${PROJECT_SOURCE_DIR}/golden/bs_vanilla.json"
            TOUCHSTONE_RNG_FIXTURE_PATH="${PROJECT_SOURCE_DIR}/golden/rng-known-answers.json"
            TOUCHSTONE_AMERICAN_PATH="${PROJECT_SOURCE_DIR}/golden/american_vanilla.json")

# One ctest entry per suite, so a red run names the misunderstanding rather than
# just the binary; plus one entry that runs the whole binary, so a mistyped
# filter above can leave a suite unregistered but never unrun.
foreach(suite IN ITEMS normal rng closed-form parity limits monte-carlo euler
                       associations tridiagonal pde implied-vol bump-greeks american three-way)
    add_test(NAME ts_${suite}
             COMMAND touchstone_tests --test-suite=${suite} --success=false)
endforeach()

add_test(NAME ts_all COMMAND touchstone_tests)
