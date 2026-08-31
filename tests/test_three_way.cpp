// Constitution I20, stated as one test.
//
//   "Correctness is three-way agreement. Closed form, Monte Carlo and finite
//    differences MUST agree within stated tolerances; analytic and bump Greeks
//    likewise; Monte Carlo standard error is reported, never hidden."
//
// The other test files each hold one method against one reference. This one puts
// all three side by side on the same rows and asks whether they agree, which is
// a different question: two methods can each be within tolerance of an oracle
// and still disagree with each other, and a bug in the oracle's *interpretation*
// — a discount factor applied twice, a dividend yield read as a rate — is
// invisible until three implementations that share no arithmetic are compared.
//
// What each leg is compared in:
//
//   - **Closed form vs Monte Carlo:** standard errors. A sampling estimate is
//     not close to anything; it is within so many standard errors of it, and the
//     number of them is the test. Reported, never hidden — the same discipline
//     T2 established, restated here on the same rows the grid sees.
//   - **Closed form vs finite differences:** the underlying's own scale, which
//     is the scale a truncation error lives on. `test_pde.cpp` explains why.
//   - **Analytic vs bump Greeks:** the second sentence of I20, on the same rows.
//   - **Analytic delta vs grid delta vs pathwise delta:** three routes to one
//     derivative, none of which is a difference of the other two.

#include "golden_file.hpp"
#include "statistics.hpp"

#include <touchstone/black_scholes.hpp>
#include <touchstone/bump_greeks.hpp>
#include <touchstone/monte_carlo.hpp>
#include <touchstone/pde.hpp>

#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <iomanip>
#include <limits>
#include <sstream>
#include <string>
#include <vector>

#ifndef TOUCHSTONE_SWEEP_SCALE
#define TOUCHSTONE_SWEEP_SCALE 1
#endif

namespace {

using touchstone::MonteCarloResult;
using touchstone::MonteCarloSettings;
using touchstone::PdeResult;
using touchstone::PdeSettings;
using touchstone::PriceAndGreeks;
using touchstone::testing::GoldenCase;

constexpr std::size_t sweep_scale = TOUCHSTONE_SWEEP_SCALE;
constexpr std::size_t stride = 53 * sweep_scale;

// Whether the sample is large enough for a statement about its shape. The
// sanitizer build runs a sixteenth of the rows, which is a valid smaller test of
// every code path and not a sample a standard deviation can be estimated from;
// the two assertions that need the whole sample say so and stand aside.
constexpr bool full_sweep = (sweep_scale == 1);

/// A row worth comparing three ways.
///
/// The Monte Carlo leg needs a row where a standard error means something: an
/// option so far out of the money that no path finishes in it has an estimate of
/// zero and a standard error of zero, and their ratio is not a z-score. T2
/// established that rule and this reuses it — the row must have a material price
/// and a healthy fraction of its paths in the money.
[[nodiscard]] bool comparable(const GoldenCase& row, const MonteCarloResult& mc)
{
    return row.reference.price > 1e-3 && mc.in_the_money > 200 && mc.price_standard_error > 0.0;
}

}  // namespace

TEST_SUITE("three-way")
{
    TEST_CASE("closed form, Monte Carlo and finite differences agree")
    {
        const auto& file = touchstone::testing::golden_file();

        PdeSettings grid{};
        grid.space_intervals = 1024;
        grid.time_steps = 512;

        MonteCarloSettings paths{};
        paths.paths = 1u << 17;
        paths.antithetic = true;

        std::vector<double> z;
        std::vector<std::string> z_labels;
        double worst_grid = 0.0;
        std::string worst_grid_at;
        std::size_t rows = 0;
        std::size_t skipped = 0;
        double smallest_error_bar = std::numeric_limits<double>::infinity();
        double largest_error_bar = 0.0;

        for (std::size_t i = 0; i < file.cases.size(); i += stride) {
            const GoldenCase& row = file.cases[i];

            // Each row gets its own stream, derived from its index, so that a
            // failure is reproducible from the row alone and no two rows share
            // draws.
            MonteCarloSettings settings = paths;
            settings.seed = static_cast<std::uint32_t>(900000u + i);

            const MonteCarloResult mc = touchstone::monte_carlo(row.option, row.market, settings);
            const PdeResult pde = touchstone::crank_nicolson(row.option, row.market, grid);

            const double reference = row.reference.price;
            const double error = std::abs(pde.price - reference)
                                 / std::max(std::abs(reference), row.market.spot);
            if (error > worst_grid) {
                worst_grid = error;
                worst_grid_at = touchstone::testing::describe(row);
            }

            if (!comparable(row, mc)) {
                ++skipped;
                continue;
            }
            ++rows;
            z.push_back((mc.price - reference) / mc.price_standard_error);
            z_labels.push_back(touchstone::testing::describe(row));
            const double relative_bar = mc.price_standard_error / reference;
            smallest_error_bar = std::min(smallest_error_bar, relative_bar);
            largest_error_bar = std::max(largest_error_bar, relative_bar);
        }

        REQUIRE(rows > 40u / sweep_scale);
        REQUIRE(rows > 2u);
        const touchstone::testing::Standardised standardised =
            touchstone::testing::standardise(z, z_labels);

        std::ostringstream report;
        report << "I20 on " << (rows + skipped) << " rows of the golden grid (" << skipped
               << " with too little Monte Carlo signal to score)"
               << "\n  finite differences vs closed form, scaled by max(|V|, S):"
               << "\n    worst " << std::scientific << std::setprecision(3) << worst_grid
               << "\n    at    " << worst_grid_at
               << "\n  Monte Carlo vs closed form, in standard errors:"
               << "\n    " << standardised.report("scored rows")
               << "\n    standard error as a fraction of the price: " << std::scientific
               << std::setprecision(2) << smallest_error_bar << " to " << largest_error_bar
               << "\n  and the two numerical methods, against each other, are therefore within"
               << "\n    the sum of what each is within of the closed form.";
        MESSAGE(report.str());

        // The finite-difference leg, at its own stated tolerance: measured at
        // 2.2e-5 on this sample at 1024 x 512, which is the same figure
        // `test_pde.cpp` measures over the whole grid at a coarser resolution,
        // divided by four.
        CHECK_MESSAGE(worst_grid <= 5e-5, worst_grid_at);

        // The Monte Carlo leg. Not a per-row three-standard-error rule — on a
        // sample this size roughly one row in three hundred exceeds three by
        // chance — but the sample's own shape: mean zero, unit spread, and no row
        // beyond the bound a sample of this size should reach.
        CHECK(std::abs(standardised.mean) < 4.0 / std::sqrt(static_cast<double>(rows)));
        if (full_sweep) {
            // A spread estimated from eight rows is not a spread, so these two
            // are the whole sample's or nothing.
            CHECK(standardised.standard_deviation > 0.6);
            CHECK(standardised.standard_deviation < 1.5);
        }
        // The worst-case bound scales with the sample size on its own — it is the
        // quantile a sample of this many rows should not exceed — so it holds at
        // any stride.
        CHECK_MESSAGE(standardised.worst <= standardised.worst_bound, standardised.worst_at);
    }

    TEST_CASE("analytic, bumped and grid Greeks agree")
    {
        // Delta three ways on the same row: differentiated by hand, differenced
        // from prices, and read off the grid as a central difference in log-spot.
        // Gamma two ways, since the Monte Carlo has no second-order estimator in
        // v1. And the pathwise Monte Carlo delta beside them, in standard errors,
        // because it is a sampling estimate and nothing else here is.
        const auto& file = touchstone::testing::golden_file();

        PdeSettings grid{};
        grid.space_intervals = 1024;
        grid.time_steps = 512;

        touchstone::BumpSizes wide{};
        wide.spot_relative = 1e-3;
        wide.spot_relative_for_gamma = 1e-2;
        wide.vol_absolute = 1e-3;
        wide.rate_absolute = 1e-3;
        wide.dividend_yield_absolute = 1e-3;
        wide.expiry_absolute = 1e-3;

        MonteCarloSettings paths{};
        paths.paths = 1u << 17;
        paths.antithetic = true;

        double worst_bumped = 0.0;
        double worst_grid_delta = 0.0;
        double worst_grid_gamma = 0.0;
        double worst_bumped_grid = 0.0;
        std::vector<double> delta_z;
        std::vector<std::string> delta_labels;
        std::size_t rows = 0;
        std::string worst_at;

        for (std::size_t i = 0; i < file.cases.size(); i += stride) {
            const GoldenCase& row = file.cases[i];
            if (row.reference.price <= 1e-3) {
                continue;
            }
            ++rows;

            const PriceAndGreeks analytic = touchstone::price_and_greeks(row.option, row.market);
            const PriceAndGreeks bumped = touchstone::bump_greeks(row.option, row.market);
            const PdeResult pde = touchstone::crank_nicolson(row.option, row.market, grid);

            const auto on_the_grid = [&](const touchstone::EuropeanVanilla& option,
                                         const touchstone::BlackScholesMarket& market) {
                return touchstone::crank_nicolson(option, market, grid).price;
            };
            const PriceAndGreeks bumped_grid =
                touchstone::bump_greeks(row.option, row.market, wide, on_the_grid);

            const auto compare = [](double a, double b) {
                return std::abs(a - b) / std::max(std::abs(b), 1.0);
            };
            const double this_row = std::max({compare(bumped.delta, analytic.delta),
                                              compare(bumped.gamma, analytic.gamma),
                                              compare(bumped.vega, analytic.vega),
                                              compare(bumped.theta, analytic.theta),
                                              compare(bumped.rho, analytic.rho)});
            if (this_row > worst_bumped) {
                worst_bumped = this_row;
                worst_at = touchstone::testing::describe(row);
            }
            worst_grid_delta = std::max(worst_grid_delta, compare(pde.delta, analytic.delta));
            worst_grid_gamma = std::max(worst_grid_gamma, compare(pde.gamma, analytic.gamma));
            worst_bumped_grid =
                std::max(worst_bumped_grid, std::max(compare(bumped_grid.vega, analytic.vega),
                                                     compare(bumped_grid.rho, analytic.rho)));

            MonteCarloSettings settings = paths;
            settings.seed = static_cast<std::uint32_t>(910000u + i);
            const MonteCarloResult mc = touchstone::monte_carlo(row.option, row.market, settings);
            if (mc.delta_standard_error > 0.0 && mc.in_the_money > 200) {
                delta_z.push_back((mc.delta - analytic.delta) / mc.delta_standard_error);
                delta_labels.push_back(touchstone::testing::describe(row));
            }
        }

        REQUIRE(rows > 40u / sweep_scale);
        REQUIRE(rows > 2u);
        REQUIRE(delta_z.size() > 30u / sweep_scale);
        REQUIRE(delta_z.size() > 2u);
        const touchstone::testing::Standardised delta_fit =
            touchstone::testing::standardise(delta_z, delta_labels);

        std::ostringstream report;
        report << "Greeks three ways over " << rows << " rows"
               << "\n    bumped closed form vs analytic, worst scaled   " << std::scientific
               << std::setprecision(3) << worst_bumped << "\n        at " << worst_at
               << "\n    grid delta vs analytic, worst scaled           " << worst_grid_delta
               << "\n    grid gamma vs analytic, worst scaled           " << worst_grid_gamma
               << "\n    bumped grid vega and rho vs analytic, worst    " << worst_bumped_grid
               << "\n    pathwise Monte Carlo delta, in standard errors:\n    "
               << delta_fit.report("scored rows");
        MESSAGE(report.str());

        // Measured on this sample and rounded up. The ordering is the finding:
        // bumping an exact pricer beats reading a grid, reading a grid beats
        // bumping one, and every one of them is a different kind of error. The
        // scale here is `max(|analytic|, 1)`, so for delta — which never exceeds
        // one — these are absolute figures.
        CHECK_MESSAGE(worst_bumped <= 1e-7, worst_at);
        CHECK(worst_grid_delta <= 2e-4);
        CHECK(worst_grid_gamma <= 1e-5);
        // The loosest of the four, and necessarily: a bumped grid divides the
        // grid's own discretisation error by the bump, and vega and rho are
        // large enough numbers that the quotient is still small beside them.
        CHECK(worst_bumped_grid <= 1e-2);
        CHECK(std::abs(delta_fit.mean) < 4.0 / std::sqrt(static_cast<double>(delta_z.size())));
        CHECK_MESSAGE(delta_fit.worst <= delta_fit.worst_bound, delta_fit.worst_at);
    }
}
