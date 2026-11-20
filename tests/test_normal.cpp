// N(x) and phi(x): known answers at high precision, the symmetry that any
// implementation must satisfy, and the tail that the obvious implementation
// throws away.

#include "errors.hpp"
#include "json_file.hpp"

#include <touchstone/normal.hpp>

#include <doctest/doctest.h>

#include <cmath>
#include <initializer_list>
#include <cstddef>
#include <limits>
#include <string>

#ifndef TOUCHSTONE_NORMAL_FIXTURE_PATH
#error "TOUCHSTONE_NORMAL_FIXTURE_PATH must name golden/normal-known-answers.json; tests/CMakeLists defines it."
#endif

namespace {

constexpr auto relative = touchstone::testing::relative_error;

// The references are correctly rounded doubles, computed at 60 decimal digits
// with mpmath and rounded once: reference values, not the output of the code
// under test. They live in `golden/normal-known-answers.json` so that the
// WebAssembly module's smoke test is held to the same numbers.
//
// Each row carries its tolerance. For N it is `(4 + x^2) eps` relative, and the
// reason is how accurately N(x) can be evaluated at all. The limit is not erfc:
// it is the rounding of x itself. A double carries x to half an ulp, so the
// input is uncertain by |x| eps / 2, and that uncertainty arrives in N amplified
// by the relative sensitivity |d ln N / dx| = phi/N, which grows like |x| in the
// left tail. The product is x^2 eps / 2, and no implementation taking a double
// can do better. The constant 4 is a floor for small |x|, where erfc's own
// couple of ulps dominate instead. Measured against these bounds on glibc:
// 1.3e-15 at x = -3 (bound 2.9e-15), 3.7e-15 at x = -10 (2.3e-14), 3.3e-14 at
// x = -30 (2.0e-13). At x = 0 the value is exact.
[[nodiscard]] const nlohmann::json& references()
{
    static const nlohmann::json fixture = [] {
        const std::string path = touchstone::testing::fixture_path(
            "TOUCHSTONE_NORMAL_FIXTURE_PATH", TOUCHSTONE_NORMAL_FIXTURE_PATH);
        nlohmann::json read = touchstone::testing::read_json(path, "normal fixture");
        touchstone::testing::require_schema(read, "touchstone/golden/normal@1", "normal fixture");
        return read;
    }();
    return fixture;
}

/// Every row of `block`: `function(x)` within the row's relative tolerance of its
/// value. Returns how many rows were checked.
template <class Function>
std::size_t check_rows(const char* block, Function function)
{
    std::size_t rows = 0;
    for (const auto& row : references().at(block)) {
        const double x = row.at("x").get<double>();
        CAPTURE(x);
        CHECK(relative(function(x), row.at("value").get<double>())
              <= row.at("relative_tolerance").get<double>());
        ++rows;
    }
    return rows;
}

}  // namespace

TEST_SUITE("normal")
{
    TEST_CASE("N(x) matches high-precision reference values")
    {
        // The far left tail among them: N(-10) and N(-30), which the case below
        // is about.
        CHECK(check_rows("cdf", [](double x) { return touchstone::norm_cdf(x); }) >= 7u);
    }

    TEST_CASE("the far left tail survives")
    {
        // This is the check that fails on the misunderstanding. N(-10) is
        // 7.6e-24; an implementation that computes it as 1 - N(10) returns
        // exactly zero, because 1 - 0.9999...  has no digits left to carry it.
        // A deep out-of-the-money option would then be priced at zero rather
        // than at something small, and the golden file's 272 rows below 1e-15
        // could not be reproduced at all.
        // Each is also held to its reference in the case above.
        CHECK(touchstone::norm_cdf(-10.0) > 0.0);
        CHECK(touchstone::norm_cdf(-30.0) > 0.0);

        // The misconception, demonstrated rather than asserted: the subtraction
        // really does collapse, so this is not a hypothetical failure mode.
        CHECK(1.0 - touchstone::norm_cdf(10.0) == 0.0);
    }

    TEST_CASE("N is a distribution function")
    {
        CHECK(touchstone::norm_cdf(-std::numeric_limits<double>::infinity()) == 0.0);
        CHECK(touchstone::norm_cdf(std::numeric_limits<double>::infinity()) == 1.0);

        double previous = 0.0;
        for (int step = -400; step <= 400; ++step) {
            const double x = static_cast<double>(step) * 0.02;
            const double value = touchstone::norm_cdf(x);

            CAPTURE(x);
            CHECK(value >= previous);            // non-decreasing
            CHECK(value >= 0.0);
            CHECK(value <= 1.0);
            // Exact in real arithmetic, and here it costs one rounding: the
            // observed departure is eps/2, the smallest a sum near 1.0 can be
            // wrong by.
            CHECK(std::abs(touchstone::norm_cdf(x) + touchstone::norm_cdf(-x) - 1.0)
                  <= std::numeric_limits<double>::epsilon());
            previous = value;
        }
    }

    TEST_CASE("phi is the density N is the integral of")
    {
        CHECK(check_rows("pdf", [](double x) { return touchstone::norm_pdf(x); }) >= 2u);

        for (int step = 0; step <= 400; ++step) {
            const double x = static_cast<double>(step) * 0.02;
            CAPTURE(x);
            CHECK(touchstone::norm_pdf(x) == touchstone::norm_pdf(-x));  // exactly even
            CHECK(touchstone::norm_pdf(x) >= 0.0);
        }

        // A central difference of N is phi, to the accuracy a central
        // difference has. Nothing here shares a line of code with either.
        constexpr double h = 1e-5;
        for (double x : {-2.5, -1.0, 0.0, 0.5, 2.0}) {
            const double numerical =
                (touchstone::norm_cdf(x + h) - touchstone::norm_cdf(x - h)) / (2.0 * h);
            CAPTURE(x);
            CHECK(std::abs(numerical - touchstone::norm_pdf(x)) <= 1e-9);
        }
    }
}
