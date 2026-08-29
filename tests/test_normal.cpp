// N(x) and phi(x): known answers at high precision, the symmetry that any
// implementation must satisfy, and the tail that the obvious implementation
// throws away.

#include <touchstone/normal.hpp>

#include <doctest/doctest.h>

#include <cmath>
#include <initializer_list>
#include <limits>

namespace {

// Correctly rounded doubles for erfc(-x/sqrt(2))/2, computed at 60 decimal
// digits with mpmath and rounded once. They are reference values, not the
// output of the code under test.
constexpr double n_at_1 = 0.8413447460685429;
constexpr double n_at_minus_1 = 0.15865525393145705;
constexpr double n_at_1_96 = 0.9750021048517795;
constexpr double n_at_minus_3 = 0.0013498980316300946;
constexpr double n_at_minus_10 = 7.619853024160526e-24;
constexpr double n_at_minus_30 = 4.906713927148187e-198;

constexpr double phi_at_0 = 0.3989422804014326779399461;
constexpr double phi_at_1 = 0.2419707245191433497978302;

double relative(double actual, double reference)
{
    return std::abs(actual - reference) / std::abs(reference);
}

/// How accurately N(x) can be evaluated at all, in relative terms.
///
/// The limit is not erfc: it is the rounding of x itself. A double carries x to
/// half an ulp, so the input is uncertain by |x| eps / 2, and that uncertainty
/// arrives in N amplified by the relative sensitivity |d ln N / dx| = phi/N,
/// which grows like |x| in the left tail. The product is x^2 eps / 2, and no
/// implementation taking a double can do better. The constant 4 is a floor for
/// small |x|, where erfc's own couple of ulps dominate instead.
///
/// Measured against these bounds on glibc: 1.3e-15 at x = -3 (bound 2.9e-15),
/// 3.7e-15 at x = -10 (2.3e-14), 3.3e-14 at x = -30 (2.0e-13).
double tolerance_at(double x)
{
    return (4.0 + x * x) * std::numeric_limits<double>::epsilon();
}

}  // namespace

TEST_SUITE("normal")
{
    TEST_CASE("N(x) matches high-precision reference values")
    {
        CHECK(touchstone::norm_cdf(0.0) == 0.5);
        CHECK(relative(touchstone::norm_cdf(1.0), n_at_1) <= tolerance_at(1.0));
        CHECK(relative(touchstone::norm_cdf(-1.0), n_at_minus_1) <= tolerance_at(-1.0));
        CHECK(relative(touchstone::norm_cdf(1.96), n_at_1_96) <= tolerance_at(1.96));
        CHECK(relative(touchstone::norm_cdf(-3.0), n_at_minus_3) <= tolerance_at(-3.0));
    }

    TEST_CASE("the far left tail survives")
    {
        // This is the check that fails on the misunderstanding. N(-10) is
        // 7.6e-24; an implementation that computes it as 1 - N(10) returns
        // exactly zero, because 1 - 0.9999...  has no digits left to carry it.
        // A deep out-of-the-money option would then be priced at zero rather
        // than at something small, and the golden file's 272 rows below 1e-15
        // could not be reproduced at all.
        CHECK(touchstone::norm_cdf(-10.0) > 0.0);
        CHECK(relative(touchstone::norm_cdf(-10.0), n_at_minus_10) <= tolerance_at(-10.0));
        CHECK(touchstone::norm_cdf(-30.0) > 0.0);
        CHECK(relative(touchstone::norm_cdf(-30.0), n_at_minus_30) <= tolerance_at(-30.0));

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
        CHECK(relative(touchstone::norm_pdf(0.0), phi_at_0) <= 1e-16);
        CHECK(relative(touchstone::norm_pdf(1.0), phi_at_1) <= 4e-16);

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
