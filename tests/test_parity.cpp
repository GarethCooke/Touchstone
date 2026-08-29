// Put-call parity, and the identity each Greek inherits from it.
//
// This suite reads the golden file for its parameter sweep and for nothing
// else: every number compared is one this library computed. QuantLib could be
// wrong about all 7234 rows and these identities would still have to hold, so a
// failure here is a failure of internal consistency rather than of agreement.

#include "golden_file.hpp"

#include <touchstone/black_scholes.hpp>

#include <doctest/doctest.h>

#include <array>
#include <cmath>
#include <cstddef>
#include <initializer_list>
#include <iomanip>
#include <sstream>
#include <vector>

namespace {

using touchstone::BlackScholesMarket;
using touchstone::EuropeanVanilla;
using touchstone::OptionType;
using touchstone::PriceAndGreeks;
using touchstone::testing::GoldenCase;
using touchstone::testing::Worst;

/// The seven identities, in the order the fields appear in PriceAndGreeks.
/// With F = S e^{-qT} and D = K e^{-rT}:
///
///     price_c        - price_p        =  F - D
///     delta_c        - delta_p        =  e^{-qT}
///     gamma_c        - gamma_p        =  0
///     vega_c         - vega_p         =  0
///     theta_c        - theta_p        =  q F - r D
///     rho_c          - rho_p          =  T D
///     dividend_rho_c - dividend_rho_p = -T F
struct Identity {
    const char* name;
    double PriceAndGreeks::* value;
};

constexpr std::array<Identity, 7> identities{{
    {"price", &PriceAndGreeks::price},
    {"delta", &PriceAndGreeks::delta},
    {"gamma", &PriceAndGreeks::gamma},
    {"vega", &PriceAndGreeks::vega},
    {"theta", &PriceAndGreeks::theta},
    {"rho", &PriceAndGreeks::rho},
    {"dividend_rho", &PriceAndGreeks::dividend_rho},
}};

std::array<double, 7> expected_differences(const EuropeanVanilla& option,
                                           const BlackScholesMarket& market)
{
    const double t = option.expiry_years;
    const double discounted_spot = market.spot * std::exp(-market.dividend_yield * t);
    const double discounted_strike = option.strike * std::exp(-market.rate * t);
    return {
        discounted_spot - discounted_strike,
        std::exp(-market.dividend_yield * t),
        0.0,
        0.0,
        market.dividend_yield * discounted_spot - market.rate * discounted_strike,
        t * discounted_strike,
        -t * discounted_spot,
    };
}

void sweep(const std::vector<GoldenCase>& rows, double tolerance, const char* what)
{
    REQUIRE_FALSE(rows.empty());

    std::array<Worst, identities.size()> worst{};
    std::size_t pairs = 0;

    for (const GoldenCase& row : rows) {
        if (row.option.type != OptionType::Call) {
            continue;  // Each parameter set appears twice; take it once.
        }
        ++pairs;

        EuropeanVanilla put = row.option;
        put.type = OptionType::Put;

        const PriceAndGreeks call_side = touchstone::price_and_greeks(row.option, row.market);
        const PriceAndGreeks put_side = touchstone::price_and_greeks(put, row.market);
        const std::array<double, 7> expected = expected_differences(row.option, row.market);

        for (std::size_t f = 0; f < identities.size(); ++f) {
            const double difference =
                call_side.*(identities[f].value) - put_side.*(identities[f].value);
            worst[f].observe(difference, expected[f], row);
        }
    }

    std::ostringstream report;
    report << what << ": " << pairs << " call/put pairs at tolerance " << tolerance
           << "; worst scaled departure from the identity";
    for (std::size_t f = 0; f < identities.size(); ++f) {
        report << "\n    " << std::left << std::setw(14) << identities[f].name << std::right
               << std::scientific << std::setprecision(3) << worst[f].error();
    }
    MESSAGE(report.str());

    for (std::size_t f = 0; f < identities.size(); ++f) {
        CHECK_MESSAGE(worst[f].error() <= tolerance, worst[f].describe(identities[f].name));
    }
}

}  // namespace

TEST_SUITE("parity")
{
    // Three orders tighter than the golden tolerance, and it should be: these
    // are exact algebraic identities of the closed form, so what is measured
    // here is rounding, not agreement between two implementations.
    //
    // Not tighter still, because the identity is a difference of two numbers of
    // order S. On the grid's largest spot, 150, one ulp is 2.8e-14, so a few
    // ulps of the terms is 1e-13 of the difference however small that
    // difference happens to be. The worst observed is 1.4e-14, at S = K = 80.
    constexpr double tolerance = 1e-13;

    TEST_CASE("main grid: parity and its six Greek identities")
    {
        sweep(touchstone::testing::golden_file().cases, tolerance, "main grid");
    }

    TEST_CASE("edge block: parity where the formulas are least comfortable")
    {
        sweep(touchstone::testing::golden_file().edge_cases, tolerance, "edge block");
    }

    TEST_CASE("parity holds where the closed form degenerates")
    {
        // sigma = 0 and T = 0 take a different branch inside the library, so the
        // identity has to be re-established there rather than assumed. Strikes
        // straddle the forward, and 100 * exp(-0.015 * T) = K * exp(-0.04 * T)
        // is hit exactly at T = 0, K = 100 — the at-the-forward case.
        for (double vol : {0.0, 0.2}) {
            for (double expiry : {0.0, 0.25, 1.0, 5.0}) {
                if (vol > 0.0 && expiry > 0.0) {
                    continue;  // Not degenerate; the sweeps above cover it.
                }
                for (double strike : {50.0, 99.0, 100.0, 101.0, 250.0}) {
                    const BlackScholesMarket market{100.0, vol, 0.04, 0.015};
                    const EuropeanVanilla call{strike, expiry, OptionType::Call};
                    const EuropeanVanilla put{strike, expiry, OptionType::Put};

                    const double difference =
                        touchstone::price(call, market) - touchstone::price(put, market);

                    CAPTURE(vol);
                    CAPTURE(expiry);
                    CAPTURE(strike);
                    CHECK(touchstone::testing::scaled_error(
                              difference, expected_differences(call, market)[0]) <= tolerance);
                }
            }
        }
    }
}
