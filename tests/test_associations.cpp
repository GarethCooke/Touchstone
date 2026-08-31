// `require_valid`'s promise, and the way it was broken.
//
// T1 made the promise: an input this library accepts never produces a NaN,
// because a NaN compares false against every tolerance a caller might test it
// with and so defeats the check that was meant to catch it. T2's review found
// the promise's method fragile — the domain checks form the same quantities the
// formulas do, and nothing made them form them the *same way* — and left it for
// T3. T3 found it was not merely fragile: one input got through.
//
// This file is what closes it. It pins the escape itself, and then the boundary
// of every other check in `require_valid`, so that a future edit that changes an
// association has to change a test to do it.

#include "golden_file.hpp"

#include <touchstone/black_scholes.hpp>
#include <touchstone/monte_carlo.hpp>
#include <touchstone/scales.hpp>

#include <doctest/doctest.h>

#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>

namespace {

using touchstone::BlackScholesMarket;
using touchstone::EuropeanVanilla;
using touchstone::OptionType;
using touchstone::PriceAndGreeks;

/// True if the closed form prices this input without a NaN anywhere.
[[nodiscard]] bool prices_cleanly(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    const PriceAndGreeks out = touchstone::price_and_greeks(option, market);
    return !std::isnan(out.price) && !std::isnan(out.delta) && !std::isnan(out.gamma)
           && !std::isnan(out.vega) && !std::isnan(out.theta) && !std::isnan(out.rho)
           && !std::isnan(out.dividend_rho);
}

}  // namespace

TEST_SUITE("associations")
{
    TEST_CASE("the input T1 accepted and returned a NaN for")
    {
        // sigma = sqrt(2e300), q = 0.5 sigma^2, r = 0, T = 1e10.
        //
        // T1's drift check was `(r - q + 0.5 sigma^2) T`. The bracket is exactly
        // zero here by construction, so the product is zero and finite whatever T
        // is, and the input was accepted. The kernel forms the two terms
        // separately — `(r - q) T` inside the log-moneyness and `0.5 sigma^2 T`
        // beside it in d1 — and at this expiry they are -inf and +inf. Their sum
        // is a NaN, and it reaches every one of the seven outputs.
        //
        // Every other check in `require_valid` passes on this input, which is
        // the point: the escape is not a missing check, it is a check that
        // guards a different set of inputs than the formulas use.
        const double sigma = std::sqrt(2e300);
        const BlackScholesMarket market{100.0, sigma, 0.0, 0.5 * sigma * sigma};
        const EuropeanVanilla option{100.0, 1e10, OptionType::Call};

        // The premises, so that a future change that makes this input ordinary
        // fails here rather than silently retiring the test.
        REQUIRE(std::isfinite(std::exp(-market.rate * option.expiry_years)));
        REQUIRE(std::isfinite(std::exp(-market.dividend_yield * option.expiry_years)));
        REQUIRE((market.rate - market.dividend_yield + 0.5 * market.vol * market.vol)
                    * option.expiry_years
                == 0.0);
        REQUIRE(std::isinf(touchstone::detail::carry_time(market.rate, market.dividend_yield,
                                                          option.expiry_years)));
        REQUIRE(std::isinf(touchstone::detail::half_variance_time(market.vol,
                                                                  option.expiry_years)));

        CHECK_THROWS_AS(touchstone::require_valid(option, market), std::invalid_argument);
        CHECK_THROWS_AS(touchstone::price_and_greeks(option, market), std::invalid_argument);
    }

    TEST_CASE("the volatility band T2 relies on is still priced")
    {
        // The other side of the same coin, and the reason the repair is two
        // separate checks rather than one tighter one. sigma = 1.6e154 squares to
        // an infinity, but over an expiry of 1e-160 neither product the closed
        // form forms overflows: `0.5 sigma^2 T` is 1.3e148 because the halving
        // comes first, and `sigma sqrt(T)` is 1.6e74. T2's Monte Carlo prices
        // this row and `test_monte_carlo.cpp` asserts a value for it, so a repair
        // that rejected it would have been a regression wearing a fix's clothes.
        const BlackScholesMarket enormous{100.0, 1.6e154, 0.01, 0.0};
        const EuropeanVanilla brief{100.0, 1e-160, OptionType::Call};

        REQUIRE(std::isinf(enormous.vol * enormous.vol));
        CHECK_NOTHROW(touchstone::require_valid(brief, enormous));
        CHECK(prices_cleanly(brief, enormous));

        touchstone::MonteCarloSettings settings{};
        settings.paths = 256;
        CHECK_NOTHROW(touchstone::monte_carlo(brief, enormous, settings));
    }

    TEST_CASE("every check has a boundary, and an input either side of it")
    {
        // One accepted input and one rejected input per check, chosen so that the
        // only thing separating them is the quantity that check guards. A check
        // deleted, loosened, or re-associated moves one of these across the line.
        struct Straddle {
            const char* what;
            EuropeanVanilla accepted_option;
            BlackScholesMarket accepted_market;
            EuropeanVanilla rejected_option;
            BlackScholesMarket rejected_market;
        };

        const double sigma = std::sqrt(2e300);
        const Straddle straddles[] = {
            // The discount factors are guarded against *overflow*, which needs a
            // negative rate: `exp(-rT)` with a large positive rate underflows to
            // zero, which is finite and perfectly priceable. The strike and spot
            // are tiny so that the discounted strike and spot, which the next two
            // checks guard, do not overflow first and take the credit.
            {"the discount factor exp(-rT)",
             {1e-300, 1.0, OptionType::Call},
             {100.0, 0.2, -709.0, 0.0},
             {1e-300, 1.0, OptionType::Call},
             {100.0, 0.2, -710.0, 0.0}},
            {"the dividend discount exp(-qT)",
             {100.0, 1.0, OptionType::Put},
             {1e-300, 0.2, 0.0, -709.0},
             {100.0, 1.0, OptionType::Put},
             {1e-300, 0.2, 0.0, -710.0}},
            {"the discounted spot S exp(-qT)",
             {100.0, 1.0, OptionType::Call},
             {1e300, 0.2, 0.0, -5.0},
             {100.0, 1.0, OptionType::Call},
             {1e300, 0.2, 0.0, -50.0}},
            {"the discounted strike K exp(-rT)",
             {1e300, 1.0, OptionType::Put},
             {100.0, 0.2, -5.0, 0.0},
             {1e300, 1.0, OptionType::Put},
             {100.0, 0.2, -50.0, 0.0}},
            {"the carry (r - q) T",
             {100.0, 1e10, OptionType::Call},
             {100.0, 0.2, 0.0, 1e290},
             {100.0, 1e10, OptionType::Call},
             {100.0, 0.2, 0.0, 1e300}},
            {"half the variance, 0.5 vol^2 T",
             {100.0, 1e-160, OptionType::Call},
             {100.0, 1.6e154, 0.01, 0.0},
             {100.0, 1e10, OptionType::Call},
             {100.0, sigma, 0.0, 0.5 * sigma * sigma}},
            {"T times the discounted strike",
             {1e12, 1e290, OptionType::Put},
             {0.0, 0.0, 0.0, 0.0},
             {1e12, 1e300, OptionType::Put},
             {0.0, 0.0, 0.0, 0.0}},
            {"the moneyness S/K",
             {1e-300, 1.0, OptionType::Call},
             {1e-8, 0.2, 0.05, 0.01},
             {1e-300, 1.0, OptionType::Call},
             {1e300, 0.2, 0.05, 0.01}},
        };

        for (const Straddle& straddle : straddles) {
            const std::string what = straddle.what;
            CAPTURE(what);
            CHECK_NOTHROW(
                touchstone::require_valid(straddle.accepted_option, straddle.accepted_market));
            CHECK(prices_cleanly(straddle.accepted_option, straddle.accepted_market));
            CHECK_THROWS_AS(
                touchstone::require_valid(straddle.rejected_option, straddle.rejected_market),
                std::invalid_argument);
        }
    }

    TEST_CASE("the check and the formula call the same function")
    {
        // The repair is not a tighter bound, it is a shared expression: both
        // `require_valid` and `make_kernel` reach the quantities through
        // `scales.hpp`, so they cannot round differently. This asserts the
        // associations that file promises, at values where a regrouping shows.
        //
        // `0.5 sigma^2 T` grouped as `((0.5 sigma) sigma) T` survives a
        // volatility that `(sigma sigma) 0.5 T` does not, by a factor of two —
        // and that factor is the whole of T2's accepted band.
        const double sigma = 1.6e154;
        CHECK(std::isfinite(touchstone::detail::half_variance_time(sigma, 1e-160)));
        CHECK(std::isinf(sigma * sigma));

        // And the association is pinned from the other side too, at an input
        // where the two groupings of the same product disagree about whether
        // the answer exists at all. `((0.5 sigma) sigma) T` at sigma = 1e300 and
        // T = 1e-300 overflows on its first multiplication; `(0.5 sigma)(sigma T)`
        // does not, because `sigma T` is one. The kernel forms the first, so the
        // check must guard the first, and this is what says which one it is.
        CHECK_FALSE(std::isfinite(touchstone::detail::half_variance_time(1e300, 1e-300)));
        CHECK(std::isfinite(0.5 * 1e300 * (1e300 * 1e-300)));

        // `sigma sqrt(T)` rather than `sqrt(sigma^2 T)`: same number where both
        // are finite, more room where they are not.
        CHECK(std::isfinite(touchstone::detail::total_volatility(sigma, 1e-160)));
        CHECK(touchstone::detail::total_volatility(0.3, 4.0) == 0.3 * 2.0);

        // And the two drift terms are formed apart and added, never combined
        // first — which is exactly what the first test in this file is about.
        CHECK(touchstone::detail::forward_log_moneyness(100.0, 50.0, 0.05, 0.01, 2.0)
              == std::log(100.0 / 50.0) + touchstone::detail::carry_time(0.05, 0.01, 2.0));
    }

    TEST_CASE("the golden grid is untouched by the repair")
    {
        // The repair changes which inputs are accepted. Every row of the golden
        // file must still be one of them, or T1's evidence describes a library
        // that no longer exists.
        const auto& file = touchstone::testing::golden_file();
        for (const auto& row : file.cases) {
            CHECK_NOTHROW(touchstone::require_valid(row.option, row.market));
        }
        for (const auto& row : file.edge_cases) {
            CHECK_NOTHROW(touchstone::require_valid(row.option, row.market));
        }
        MESSAGE("all " << file.cases.size() + file.edge_cases.size()
                       << " golden rows still inside the accepted domain");
    }
}
