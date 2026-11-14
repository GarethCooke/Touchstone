// Three-way agreement, stated as one test: closed form, Monte Carlo and finite
// differences agree within stated tolerances; analytic and bump Greeks
// likewise; the Monte Carlo's standard error is reported, never hidden.
//
// The other test files each hold one method against one reference. This one puts
// all three side by side on the same rows and asks whether they agree, which is
// a different question: two methods can each be within tolerance of an oracle
// and still disagree with each other, and a bug in the oracle's *interpretation*
// — a discount factor applied twice, a dividend yield read as a rate — is
// invisible until three methods are compared. They are different methods, not
// wholly separate code: `ARCHITECTURE.md` §1 lists what they share, and a
// mistake in a shared piece shows only against a method that does not share it.
//
// What each leg is compared in:
//
//   - **Closed form vs Monte Carlo:** standard errors. A sampling estimate is
//     not close to anything; it is within so many standard errors of it, and the
//     number of them is the test. Reported, never hidden — the discipline of
//     `test_monte_carlo.cpp`, restated here on the same rows the grid sees.
//   - **Closed form vs finite differences:** the underlying's own scale, which
//     is the scale a truncation error lives on. `test_pde.cpp` explains why.
//   - **Analytic vs bump Greeks:** the same agreement for the Greeks, on the
//     same rows.
//   - **Analytic delta vs grid delta vs pathwise delta:** three routes to one
//     derivative, none of which is a difference of the other two.

#include "grid_bumps.hpp"
#include "golden_file.hpp"
#include "statistics.hpp"
#include "sweep.hpp"

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

namespace {

using touchstone::MonteCarloResult;
using touchstone::MonteCarloSettings;
using touchstone::PdeResult;
using touchstone::PdeSettings;
using touchstone::PriceAndGreeks;
using touchstone::testing::GoldenCase;

using touchstone::testing::sweep_scale;
constexpr std::size_t stride = 53 * sweep_scale;

// Whether the sample is large enough for a statement about its shape. The
// sanitizer build runs a sixteenth of the rows, which is a valid smaller test of
// every code path and not a sample a standard deviation can be estimated from;
// the two assertions that need the whole sample say so and stand aside.
using touchstone::testing::full_sweep;

/// A row worth comparing three ways.
///
/// The Monte Carlo leg needs a row where a standard error means something: an
/// option so far out of the money that no path finishes in it has an estimate
/// of zero and a standard error of zero, and their ratio is not a z-score.
/// `test_monte_carlo.cpp` applies that rule and this reuses it — the row must
/// have a material price and a healthy fraction of its paths in the money.
/// The grid both cases run at, stated rather than defaulted: a finite-difference
/// tolerance means nothing without its grid beside it.
[[nodiscard]] PdeSettings grid_settings()
{
    PdeSettings grid{};
    grid.space_intervals = 1024;
    grid.time_steps = 512;
    return grid;
}

/// The Monte Carlo both cases run, before each row's own seed.
[[nodiscard]] MonteCarloSettings path_settings()
{
    MonteCarloSettings paths{};
    paths.paths = 1u << 17;
    paths.antithetic = true;
    return paths;
}

/// A Monte Carlo estimate whose standard error means something: enough paths in
/// the money, and a standard error that is not zero.
[[nodiscard]] bool has_signal(const MonteCarloResult& mc, double standard_error)
{
    return mc.in_the_money > 200 && standard_error > 0.0;
}

[[nodiscard]] bool comparable(const GoldenCase& row, const MonteCarloResult& mc)
{
    return row.reference.price > 1e-3 && has_signal(mc, mc.price_standard_error);
}

}  // namespace

TEST_SUITE("three-way")
{
    TEST_CASE("closed form, Monte Carlo and finite differences agree")
    {
        const auto& file = touchstone::testing::golden_file();

        const PdeSettings grid = grid_settings();

        const MonteCarloSettings paths = path_settings();

        std::vector<double> z;
        std::vector<std::string> z_labels;
        touchstone::testing::Largest<GoldenCase> worst_grid;
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
            const double error =
                touchstone::testing::scaled_error(pde.price, reference, row.market.spot);
            worst_grid.observe(error, row);

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
        report << "three-way agreement on " << (rows + skipped) << " rows of the golden grid ("
               << skipped << " with too little Monte Carlo signal to score)"
               << "\n  finite differences vs closed form, scaled by max(|V|, S):"
               << "\n    worst " << std::scientific << std::setprecision(3) << worst_grid.value()
               << "\n    at    " << worst_grid.at()
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
        CHECK_MESSAGE(worst_grid.value() <= 5e-5, worst_grid.at());

        // The Monte Carlo leg. Not a per-row three-standard-error rule — on a
        // sample this size roughly one row in three hundred exceeds three by
        // chance — but the sample's own shape: mean zero, unit spread, and no row
        // beyond the bound a sample of this size should reach.
        CHECK(std::abs(standardised.mean) < standardised.mean_bound(4.0));
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

        const PdeSettings grid = grid_settings();

        const MonteCarloSettings paths = path_settings();

        touchstone::testing::Largest<GoldenCase> worst_bumped;
        double worst_grid_delta = 0.0;
        double worst_grid_gamma = 0.0;
        double worst_bumped_grid = 0.0;
        std::vector<double> delta_z;
        std::vector<std::string> delta_labels;
        std::size_t rows = 0;

        for (std::size_t i = 0; i < file.cases.size(); i += stride) {
            const GoldenCase& row = file.cases[i];
            if (row.reference.price <= 1e-3) {
                continue;
            }
            ++rows;

            const PriceAndGreeks analytic = touchstone::price_and_greeks(row.option, row.market);
            const PriceAndGreeks bumped = touchstone::bump_greeks(row.option, row.market);
            const PdeResult pde = touchstone::crank_nicolson(row.option, row.market, grid);

            const auto on_the_grid = touchstone::testing::grid_pricer(grid);
            const PriceAndGreeks bumped_grid =
                touchstone::bump_greeks(row.option, row.market, touchstone::testing::grid_bumps(),
                                        on_the_grid);

            const auto compare = [](double a, double b) {
                return touchstone::testing::scaled_error(a, b);
            };
            const double this_row = std::max({compare(bumped.delta, analytic.delta),
                                              compare(bumped.gamma, analytic.gamma),
                                              compare(bumped.vega, analytic.vega),
                                              compare(bumped.theta, analytic.theta),
                                              compare(bumped.rho, analytic.rho)});
            worst_bumped.observe(this_row, row);
            worst_grid_delta = std::max(worst_grid_delta, compare(pde.delta, analytic.delta));
            worst_grid_gamma = std::max(worst_grid_gamma, compare(pde.gamma, analytic.gamma));
            worst_bumped_grid =
                std::max(worst_bumped_grid, std::max(compare(bumped_grid.vega, analytic.vega),
                                                     compare(bumped_grid.rho, analytic.rho)));

            MonteCarloSettings settings = paths;
            settings.seed = static_cast<std::uint32_t>(910000u + i);
            const MonteCarloResult mc = touchstone::monte_carlo(row.option, row.market, settings);
            if (has_signal(mc, mc.delta_standard_error)) {
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
               << std::setprecision(3) << worst_bumped.value() << "\n        at " << worst_bumped.at()
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
        CHECK_MESSAGE(worst_bumped.value() <= 1e-7, worst_bumped.at());
        CHECK(worst_grid_delta <= 2e-4);
        CHECK(worst_grid_gamma <= 1e-5);
        // The loosest of the four, and necessarily: a bumped grid divides the
        // grid's own discretisation error by the bump, and vega and rho are
        // large enough numbers that the quotient is still small beside them.
        CHECK(worst_bumped_grid <= 1e-2);
        CHECK(std::abs(delta_fit.mean) < delta_fit.mean_bound(4.0));
        CHECK_MESSAGE(delta_fit.worst <= delta_fit.worst_bound, delta_fit.worst_at);
    }
}
