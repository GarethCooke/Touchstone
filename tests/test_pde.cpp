// Crank-Nicolson on a log-spot grid, against the closed form it is approximating.
//
// The claims a finite-difference scheme makes are not "the answer is close". They
// are: the error falls as the square of the grid step, the error falls as the
// square of the time step, the truncated domain contributes nothing measurable,
// and the matrix being solved is one an unpivoted sweep can be trusted with.
// Each of those is a number, and this file measures each of them. The sweep over
// the golden grid at the end is the consequence, not the evidence.
//
// Where a tolerance appears it is a measured figure with a margin, and the
// measurement is printed beside the assertion so that a run which passes still
// says by how much.

#include "golden_file.hpp"

#include <touchstone/black_scholes.hpp>
#include <touchstone/pde.hpp>

#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

// One row of the golden grid in every `TOUCHSTONE_SWEEP_SCALE`. A finite
// -difference sweep is thousands of tridiagonal solves and the sanitizer build
// is nine times slower again; every row exercises the same code, so a scaled run
// is a shorter test rather than a weaker one. The two compiler jobs run it whole.
#ifndef TOUCHSTONE_SWEEP_SCALE
#define TOUCHSTONE_SWEEP_SCALE 1
#endif

namespace {

using touchstone::BlackScholesMarket;
using touchstone::EuropeanVanilla;
using touchstone::OptionType;
using touchstone::PdeResult;
using touchstone::PdeSettings;
using touchstone::PriceAndGreeks;
using touchstone::testing::GoldenCase;

constexpr std::size_t grid_stride = TOUCHSTONE_SWEEP_SCALE;

/// The settings the golden sweep runs at.
///
/// Deliberately coarser than `PdeSettings`' own defaults, and stated here rather
/// than defaulted: a finite-difference tolerance without a grid beside it means
/// nothing, so the sweep names its grid and the tolerances below are that grid's.
[[nodiscard]] PdeSettings sweep_settings()
{
    PdeSettings settings{};
    settings.space_intervals = 512;
    settings.time_steps = 256;
    return settings;
}

/// The error of a grid value, in the units the error actually lives in.
///
/// `golden/SCHEMA.md`'s rule — relative above 1.0, absolute below — is the right
/// rule for the closed form, whose noise floor is a few ulps of the spot. It is
/// the wrong rule for a grid. A discretisation error is a fraction of the value
/// function's curvature scale, and a European vanilla's only scale is the
/// underlying's: the same grid that prices a hundred-currency-unit option to 1e-5
/// prices a 1e-19 option to 1e-5 as well, because both errors come from the same
/// truncated Taylor series about the same kink. Dividing by the option's own
/// price there would measure how far out of the money it is.
///
/// So the sweep reports both and asserts both, at their own tolerances: this one,
/// which is the scheme's own accuracy, and SCHEMA.md's, which is what a caller
/// comparing against the golden file directly would see.
[[nodiscard]] double grid_error(double actual, double reference, const BlackScholesMarket& market)
{
    if (actual == reference) {
        return 0.0;
    }
    if (!std::isfinite(actual) || !std::isfinite(reference)) {
        return std::numeric_limits<double>::infinity();
    }
    return std::abs(actual - reference) / std::max(std::abs(reference), market.spot);
}

/// A representative option, away from every boundary of the domain.
constexpr BlackScholesMarket typical_market{100.0, 0.30, 0.05, 0.02};
constexpr EuropeanVanilla typical_call{100.0, 1.0, OptionType::Call};

struct Fit {
    double first{};
    double last{};
    double worst_ratio{};
    double best_ratio{};
    std::string table;
};

/// Halve the step twice over and watch the error. Second order means each ratio
/// is near four; the test asserts the whole sequence rather than an endpoint, so
/// a scheme that is second order over one doubling and first order over the next
/// cannot pass.
[[nodiscard]] Fit refine(const char* what,
                         const std::vector<std::size_t>& steps,
                         const std::vector<double>& errors)
{
    Fit fit{};
    fit.first = errors.front();
    fit.last = errors.back();
    fit.worst_ratio = std::numeric_limits<double>::infinity();
    fit.best_ratio = 0.0;

    std::ostringstream out;
    out << what;
    for (std::size_t i = 0; i < errors.size(); ++i) {
        out << "\n    " << std::setw(6) << steps[i] << "  " << std::scientific
            << std::setprecision(3) << errors[i];
        if (i > 0) {
            const double ratio = errors[i - 1] / errors[i];
            out << "   ratio " << std::fixed << std::setprecision(2) << ratio;
            fit.worst_ratio = std::min(fit.worst_ratio, ratio);
            fit.best_ratio = std::max(fit.best_ratio, ratio);
        }
        out << std::defaultfloat;
    }
    fit.table = out.str();
    return fit;
}

}  // namespace

TEST_SUITE("pde")
{
    TEST_CASE("the spot lands exactly on a node")
    {
        // Not nearly: exactly. The price is then a solution value rather than an
        // interpolation between two of them, and the delta and gamma are central
        // differences about the point they are wanted at. Checked over a spread
        // of moneyness, because the anchoring has to survive a strike that sits
        // a long way from the spot.
        for (const double spot : {1.0, 60.0, 100.0, 150.0, 5000.0}) {
            for (const double strike : {0.5, 80.0, 100.0, 120.0, 9000.0}) {
                const BlackScholesMarket market{spot, 0.25, 0.03, 0.01};
                const EuropeanVanilla option{strike, 1.5, OptionType::Call};
                const PdeResult result = touchstone::crank_nicolson(option, market, {});

                CAPTURE(spot);
                CAPTURE(strike);
                // The node's log-spot, reconstructed the way the grid builds it.
                const double at_spot =
                    result.lower_log_spot
                    + static_cast<double>(result.spot_index) * result.log_spot_step;
                // Two routes to the same node, so this is a few ulps rather than
                // zero; a mis-anchored grid is out by a whole step.
                CHECK(std::abs(at_spot - std::log(spot)) < 1e-9 * result.log_spot_step
                                                               + 1e-12 * std::abs(std::log(spot)));
                CHECK(result.spot_index >= 1);
                CHECK(result.spot_index + 1 <= result.space_intervals);

                // The strike is inside the domain, or the payoff has no kink in it.
                CHECK(result.lower_log_spot <= std::log(strike));
                CHECK(result.upper_log_spot >= std::log(strike));
            }
        }
    }

    TEST_CASE("the error falls as the square of the grid step")
    {
        const double exact = touchstone::price(typical_call, typical_market);
        std::vector<std::size_t> nodes;
        std::vector<double> errors;
        for (const std::size_t n : {128u, 256u, 512u, 1024u}) {
            PdeSettings settings{};
            settings.space_intervals = n;
            settings.time_steps = 4096;  // far finer than the space, so space dominates
            const PdeResult result = touchstone::crank_nicolson(typical_call, typical_market, settings);
            nodes.push_back(result.space_intervals);
            errors.push_back(std::abs(result.price - exact));
        }
        const Fit fit = refine("space refinement, time step held fine", nodes, errors);
        MESSAGE(fit.table);
        CHECK(fit.worst_ratio > 3.5);
        CHECK(fit.best_ratio < 4.6);
    }

    TEST_CASE("the error falls as the square of the time step")
    {
        const double exact = touchstone::price(typical_call, typical_market);
        // The space error at this resolution, which is the floor the time
        // refinement converges onto and has to be subtracted to see the time
        // error at all.
        PdeSettings fine{};
        fine.space_intervals = 4096;
        fine.time_steps = 8192;
        const double floor_error =
            touchstone::crank_nicolson(typical_call, typical_market, fine).price - exact;

        std::vector<std::size_t> steps;
        std::vector<double> errors;
        for (const std::size_t m : {32u, 64u, 128u, 256u}) {
            PdeSettings settings{};
            settings.space_intervals = 4096;
            settings.time_steps = m;
            const PdeResult result = touchstone::crank_nicolson(typical_call, typical_market, settings);
            steps.push_back(m);
            errors.push_back(std::abs(result.price - exact - floor_error));
        }
        const Fit fit = refine("time refinement, space held fine (space error removed)", steps, errors);
        MESSAGE(fit.table);
        CHECK(fit.worst_ratio > 3.0);
        CHECK(fit.best_ratio < 6.0);
    }

    TEST_CASE("the truncated domain contributes nothing measurable")
    {
        // Widening the domain at a fixed node count also coarsens the grid, so the
        // naive experiment measures `dx` and reports it as the boundary. Here the
        // node count grows with the width instead, holding `dx` fixed, and the
        // only thing left changing is how far away the Dirichlet condition sits.
        //
        // The measurement is on an at-the-money option, where the domain really is
        // proportional to the width: on a row whose strike is far from its spot,
        // part of the domain is the moneyness gap and `dx` cannot be held fixed by
        // scaling the node count. That is a limitation of the experiment, stated
        // rather than hidden — what it establishes about the boundary here is not
        // established for every row of the grid.
        //
        // What it shows: from three total volatilities outward the answer stops
        // moving at all, five thousand times below the discretisation error beside
        // it. That is far better than the crude `exp(-alpha^2/2)` estimate, and
        // for a good reason: the condition imposed is not the intrinsic value but
        // the exact European asymptote at each time level, whose error is the
        // *remaining time value* at the boundary — small at every step, and zero
        // at the last one.
        //
        // The default is six, which is therefore a margin rather than a
        // requirement. The margin is not free and the cost is stated: the error
        // goes as `dx^2` and `dx` goes as the width, so six costs four times the
        // error of three. It is kept because one at-the-money row is thin evidence
        // on which to run a whole library close to a boundary.
        const double exact = touchstone::price(typical_call, typical_market);
        std::ostringstream table;
        table << "domain width at a fixed dx of about 0.0018";

        double reference = 0.0;
        double at_two = 0.0;
        double worst_beyond_three = 0.0;
        for (const double alpha : {2.0, 3.0, 4.0, 6.0, 8.0, 12.0}) {
            PdeSettings settings{};
            settings.half_width_sigmas = alpha;
            // Nodes in proportion to the width, so dx is the same in every row.
            settings.space_intervals = static_cast<std::size_t>(alpha * 560.0);
            settings.time_steps = 2048;
            const PdeResult result = touchstone::crank_nicolson(typical_call, typical_market, settings);
            const double error = result.price - exact;
            table << "\n    alpha " << std::setw(5) << alpha << "  dx " << std::fixed
                  << std::setprecision(6) << result.log_spot_step << "  error " << std::scientific
                  << std::setprecision(3) << error << std::defaultfloat;
            if (alpha == 2.0) {
                at_two = error;
            } else if (alpha == 6.0) {
                reference = error;
            }
        }
        // Second pass, now that the reference is known.
        for (const double alpha : {3.0, 4.0, 8.0, 12.0}) {
            PdeSettings settings{};
            settings.half_width_sigmas = alpha;
            settings.space_intervals = static_cast<std::size_t>(alpha * 560.0);
            settings.time_steps = 2048;
            const double error =
                touchstone::crank_nicolson(typical_call, typical_market, settings).price - exact;
            worst_beyond_three = std::max(worst_beyond_three, std::abs(error - reference));
        }
        table << "\n    worst spread over alpha in [3, 12]: " << std::scientific
              << std::setprecision(3) << worst_beyond_three << "; the discretisation error beside "
              << "it is " << std::abs(reference);
        MESSAGE(table.str());

        // From three outward the domain no longer matters at all.
        CHECK(worst_beyond_three < 2e-7);
        CHECK(worst_beyond_three * 100.0 < std::abs(reference));
        // At two it does, which is what makes the line above a measurement of the
        // boundary rather than of nothing.
        CHECK(std::abs(at_two - reference) > worst_beyond_three);
    }

    TEST_CASE("averaging the payoff over the cell is worth an order of magnitude")
    {
        // Both starts are second order. The difference is the constant, and the
        // constant is what a tolerance is made of. Sampling the payoff at nodes
        // carries the kink's unresolvable fourth derivative into the first step;
        // averaging over the cell does not.
        const double exact = touchstone::price(typical_call, typical_market);
        std::ostringstream table;
        table << "error constant C in |error| = C dx^2, at 512 intervals";

        double constants[2] = {0.0, 0.0};
        int index = 0;
        for (const bool smooth : {false, true}) {
            PdeSettings settings{};
            settings.space_intervals = 512;
            settings.time_steps = 4096;
            settings.smooth_payoff = smooth;
            const PdeResult result = touchstone::crank_nicolson(typical_call, typical_market, settings);
            const double dx = result.log_spot_step;
            constants[index] = std::abs(result.price - exact) / (dx * dx);
            table << "\n    " << (smooth ? "cell average" : "nodal value  ") << "  error "
                  << std::scientific << std::setprecision(3) << (result.price - exact) << "  C "
                  << std::fixed << std::setprecision(2) << constants[index] << std::defaultfloat;
            ++index;
        }
        MESSAGE(table.str());
        CHECK(constants[1] * 4.0 < constants[0]);
    }

    TEST_CASE("Rannacher damps what Crank-Nicolson only fails to amplify")
    {
        // Crank-Nicolson's amplification factor for the highest frequency the
        // grid carries tends to -1, not to 0: the error from the payoff's kink is
        // not damped, it alternates. Gamma is where that shows, because a second
        // difference of an oscillation is the oscillation multiplied by four over
        // dx squared. So the measurement is gamma at the strike, on a
        // deliberately coarse time grid where the effect is visible.
        //
        // The claim is only that the start damps it. Rannacher's steps are first
        // order locally, so on a fine grid they cost a little accuracy — which is
        // why `rannacher_steps` is a setting and why its default is two rather
        // than eight.
        const BlackScholesMarket market{100.0, 0.20, 0.05, 0.0};
        const EuropeanVanilla at_the_money{100.0, 0.25, OptionType::Call};
        const double exact = touchstone::gamma(at_the_money, market);

        std::ostringstream table;
        table << "gamma at the strike, 2048 intervals and 12 time steps (exact " << std::scientific
              << std::setprecision(6) << exact << ")";
        double without = 0.0;
        double with = 0.0;
        for (const std::size_t rannacher : {0u, 1u, 2u, 4u}) {
            PdeSettings settings{};
            settings.space_intervals = 2048;
            settings.time_steps = 12;
            settings.rannacher_steps = rannacher;
            const PdeResult result = touchstone::crank_nicolson(at_the_money, market, settings);
            const double error = std::abs(result.gamma - exact) / exact;
            table << "\n    rannacher " << rannacher << "  gamma " << std::scientific
                  << std::setprecision(6) << result.gamma << "  relative error "
                  << std::setprecision(3) << error << std::defaultfloat;
            if (rannacher == 0) {
                without = error;
            }
            if (rannacher == 2) {
                with = error;
            }
        }
        MESSAGE(table.str());
        CHECK(with * 3.0 < without);
    }

    TEST_CASE("the matrix is one an unpivoted sweep can be trusted with")
    {
        // Thomas does not pivot, so the whole of its stability is the diagonal
        // dominance of the matrix it is handed. And the central difference on the
        // convection term only stays an M-matrix while the mesh Peclet number is
        // below two. Both are properties of the grid rather than of the answer,
        // so both are checked over the whole golden grid rather than sampled.
        const auto& file = touchstone::testing::golden_file();
        const PdeSettings settings = sweep_settings();

        double worst_peclet = 0.0;
        double worst_resolution = 0.0;
        double smallest_margin = std::numeric_limits<double>::infinity();
        std::string worst_peclet_at;
        std::size_t rows = 0;

        for (std::size_t i = 0; i < file.cases.size(); i += grid_stride) {
            const GoldenCase& row = file.cases[i];
            const PdeResult result = touchstone::crank_nicolson(row.option, row.market, settings);
            ++rows;
            if (result.mesh_peclet > worst_peclet) {
                worst_peclet = result.mesh_peclet;
                worst_peclet_at = touchstone::testing::describe(row);
            }
            worst_resolution = std::max(worst_resolution, result.resolution_in_sigmas);
            smallest_margin = std::min(smallest_margin, result.dominance_margin);
        }

        std::ostringstream report;
        report << "grid diagnostics over " << rows << " rows at " << settings.space_intervals
               << " x " << settings.time_steps << "\n    worst mesh Peclet      " << std::scientific
               << std::setprecision(3) << worst_peclet << "  (bound 2, at " << worst_peclet_at
               << ")\n    coarsest resolution    " << worst_resolution
               << " of one total volatility per step"
               << "\n    smallest dominance     " << smallest_margin;
        MESSAGE(report.str());

        // Two is where the central difference on the convection term stops being
        // an M-matrix. The golden grid does not come close: measured at 0.102,
        // on the row with the least diffusion and the widest domain.
        CHECK(worst_peclet < 0.15);
        CHECK(smallest_margin > 0.9);
    }

    TEST_CASE("the golden grid, priced on the grid")
    {
        const auto& file = touchstone::testing::golden_file();
        const PdeSettings settings = sweep_settings();

        struct Field {
            const char* name;
            double PriceAndGreeks::* value;
            double PdeResult::* from_grid;
            double tolerance;        ///< scaled by max(|reference|, spot)
            double schema_tolerance; ///< scaled by max(|reference|, 1), SCHEMA.md's rule
        };

        // Measured at these settings and rounded up by about a factor of two.
        // Both columns are asserted: the first is the scheme's accuracy, the
        // second is what a reader comparing against the golden file the way T1
        // does would see, and neither is allowed to hide behind the other.
        const Field fields[] = {
            {"price", &PriceAndGreeks::price, &PdeResult::price, 2e-4, 3e-3},
            {"delta", &PriceAndGreeks::delta, &PdeResult::delta, 1e-5, 5e-4},
            {"gamma", &PriceAndGreeks::gamma, &PdeResult::gamma, 1e-6, 5e-5},
        };

        double worst[3] = {0.0, 0.0, 0.0};
        double worst_schema[3] = {0.0, 0.0, 0.0};
        std::string worst_at[3];
        std::size_t rows = 0;

        for (std::size_t i = 0; i < file.cases.size(); i += grid_stride) {
            const GoldenCase& row = file.cases[i];
            const PdeResult on_grid = touchstone::crank_nicolson(row.option, row.market, settings);
            ++rows;
            for (std::size_t f = 0; f < 3; ++f) {
                const double reference = row.reference.*(fields[f].value);
                const double actual = on_grid.*(fields[f].from_grid);
                const double error = grid_error(actual, reference, row.market);
                if (error > worst[f]) {
                    worst[f] = error;
                    worst_at[f] = touchstone::testing::describe(row);
                }
                worst_schema[f] =
                    std::max(worst_schema[f], touchstone::testing::scaled_error(actual, reference));
            }
        }

        std::ostringstream report;
        report << "golden grid by Crank-Nicolson: " << rows << " rows at "
               << settings.space_intervals << " x " << settings.time_steps << ", alpha "
               << settings.half_width_sigmas;
        for (std::size_t f = 0; f < 3; ++f) {
            report << "\n    " << std::left << std::setw(6) << fields[f].name << std::right
                   << "  scaled by max(|ref|, S) " << std::scientific << std::setprecision(3)
                   << worst[f] << "   by SCHEMA.md's max(|ref|, 1) " << worst_schema[f]
                   << "\n            at " << worst_at[f];
        }
        MESSAGE(report.str());

        for (std::size_t f = 0; f < 3; ++f) {
            const std::string field = fields[f].name;
            CAPTURE(field);
            CHECK_MESSAGE(worst[f] <= fields[f].tolerance, worst_at[f]);
            CHECK(worst_schema[f] <= fields[f].schema_tolerance);
        }
    }

    TEST_CASE("the edge block, where a grid has less to work with")
    {
        // Reported rather than swept at the main grid's tolerance, and the reason
        // is `dx` rather than anything subtler. The block's hardest row is a
        // ten-year option at 150% volatility: the total volatility is 4.7, so a
        // domain six of those wide is 68 in log-spot, and 512 intervals across it
        // is a step of 0.13 — twenty times the main grid's. The error is still
        // exactly second order there (it quarters at every doubling, measured),
        // and it is still 1.4 in a price of 89, which is what a step that size
        // buys. That is the honest thing for this block to say.
        //
        // Nothing here is refused at the sweep's settings, though the block
        // contains rows that would be: `near-zero-vol` rows are priced because
        // their volatility is 0.01 rather than zero.
        const auto& file = touchstone::testing::golden_file();
        const PdeSettings settings = sweep_settings();

        std::size_t priced = 0;
        std::size_t refused = 0;
        double worst = 0.0;
        double worst_step = 0.0;
        double worst_resolution = 0.0;
        std::string worst_at;

        for (const GoldenCase& row : file.edge_cases) {
            PdeResult on_grid{};
            try {
                on_grid = touchstone::crank_nicolson(row.option, row.market, settings);
            } catch (const std::invalid_argument&) {
                ++refused;
                continue;
            }
            ++priced;
            const double error = grid_error(on_grid.price, row.reference.price, row.market);
            if (error > worst) {
                worst = error;
                worst_at = touchstone::testing::describe(row);
                worst_step = on_grid.log_spot_step;
                worst_resolution = on_grid.resolution_in_sigmas;
            }
        }

        std::ostringstream report;
        report << "edge block: " << priced << " priced, " << refused
               << " refused as outside the grid's domain"
               << "\n    worst price error scaled by max(|ref|, S): " << std::scientific
               << std::setprecision(3) << worst << "\n    at " << worst_at << "\n    dx there "
               << worst_step << ", " << worst_resolution << " of one total volatility per step";
        MESSAGE(report.str());

        CHECK(priced > 20u);
        CHECK(worst <= 3e-2);
    }

    TEST_CASE("what the grid will not price, it refuses")
    {
        const BlackScholesMarket market{100.0, 0.2, 0.03, 0.01};
        const EuropeanVanilla call{100.0, 1.0, OptionType::Call};

        const auto refused = [](const EuropeanVanilla& option, const BlackScholesMarket& state,
                                const PdeSettings& settings) {
            CHECK_THROWS_AS(touchstone::require_valid(option, state, settings),
                            std::invalid_argument);
            CHECK_THROWS_AS(touchstone::crank_nicolson(option, state, settings),
                            std::invalid_argument);
        };

        // The closed form's domain, inherited.
        refused(call, {-1.0, 0.2, 0.03, 0.01}, {});
        refused({100.0, -1.0, OptionType::Call}, market, {});

        // And three conditions of the grid's own, each of which the closed form
        // prices exactly and this cannot price at all.
        refused(call, {0.0, 0.2, 0.03, 0.01}, {});          // ln(0)
        refused({0.0, 1.0, OptionType::Call}, market, {});  // no kink to resolve
        refused(call, {100.0, 0.0, 0.03, 0.01}, {});        // no diffusion
        refused({100.0, 0.0, OptionType::Call}, market, {});  // no time

        // A domain whose top is not representable as a spot.
        refused({100.0, 1.0, OptionType::Call}, {100.0, 200.0, 0.03, 0.01}, {});

        PdeSettings bad{};
        bad.space_intervals = 1;
        refused(call, market, bad);
        bad = PdeSettings{};
        bad.time_steps = 0;
        refused(call, market, bad);
        bad = PdeSettings{};
        bad.rannacher_steps = bad.time_steps + 1;
        refused(call, market, bad);
        bad = PdeSettings{};
        bad.half_width_sigmas = 0.0;
        refused(call, market, bad);

        // And the ordinary case still goes through, so the list above is a list
        // of exclusions rather than a solver that refuses everything.
        CHECK_NOTHROW(touchstone::require_valid(call, market, {}));
    }

    TEST_CASE("the price is the same whichever grid you build it on")
    {
        // Two grids with nothing in common but the option: different node counts,
        // different step counts, different widths, different starts. If they agree
        // to the tolerance the sweep claims, the answer is a property of the
        // equation rather than of any one discretisation of it.
        const auto& file = touchstone::testing::golden_file();
        PdeSettings coarse{};
        coarse.space_intervals = 401;
        coarse.time_steps = 173;
        coarse.half_width_sigmas = 5.0;
        coarse.rannacher_steps = 1;
        PdeSettings fine{};
        fine.space_intervals = 1024;
        fine.time_steps = 512;
        fine.half_width_sigmas = 8.0;
        fine.rannacher_steps = 3;

        double worst = 0.0;
        std::string worst_at;
        std::size_t rows = 0;
        for (std::size_t i = 0; i < file.cases.size(); i += 37 * grid_stride) {
            const GoldenCase& row = file.cases[i];
            ++rows;
            const double a = touchstone::crank_nicolson(row.option, row.market, coarse).price;
            const double b = touchstone::crank_nicolson(row.option, row.market, fine).price;
            const double error = grid_error(a, b, row.market);
            if (error > worst) {
                worst = error;
                worst_at = touchstone::testing::describe(row);
            }
        }
        MESSAGE("two unrelated grids over " << rows << " rows: worst difference scaled by "
                                            << "max(|other|, S) is " << std::scientific
                                            << std::setprecision(3) << worst << "\n    at "
                                            << worst_at);
        CHECK(worst < 1e-4);
    }
}
