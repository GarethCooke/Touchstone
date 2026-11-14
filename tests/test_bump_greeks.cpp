// Difference quotients against the formulas they approximate.
//
// This is where the analytic Greeks and the bumped ones are held to agree.
// Seven hand-transcribed derivative formulas on one side; on the other, a
// difference of prices that knows nothing about them. A slip in any of the
// seven — a sign, a discount factor on the wrong term, `d1` where `d2` belongs
// — shows up here as a disagreement, because a difference quotient of the price
// cannot make the same mistake twice.
//
// The bump sizes are the other claim. `bump_greeks.hpp` says the optimum is
// `eps^(1/3)` for a first derivative and `eps^(1/4)` for a second, and that the
// error grows as `h^2` above the optimum and as `1/h` (or `1/h^2`) below it. The
// sweep here measures that shape rather than taking it on faith, which is what
// makes the defaults evidence rather than folklore.

#include "grid_bumps.hpp"
#include "golden_file.hpp"
#include "greek_fields.hpp"
#include "sweep.hpp"

#include <touchstone/black_scholes.hpp>
#include <touchstone/bump_greeks.hpp>
#include <touchstone/pde.hpp>

#include <doctest/doctest.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using touchstone::BlackScholesMarket;
using touchstone::BumpSizes;
using touchstone::EuropeanVanilla;
using touchstone::OptionType;
using touchstone::PriceAndGreeks;
using touchstone::testing::GoldenCase;
using touchstone::testing::Worst;

using touchstone::testing::sweep_scale;

constexpr const auto& fields = touchstone::testing::greek_fields;

/// One tolerance per field of `fields`: measured over the whole main grid at the
/// default bump sizes, then rounded up by roughly a factor of three. The spread
/// between them is the point: a first difference reaches `eps^(2/3)` and a
/// second only `eps^(1/2)`, so gamma is two orders looser than delta and no
/// tolerance can hide that.
constexpr touchstone::testing::GreekTolerances tolerance{0.0, 1e-9, 1e-7, 1e-7, 1e-8, 1e-8, 1e-8};

}  // namespace

TEST_SUITE("bump-greeks")
{
    TEST_CASE("bumped and analytic agree over the golden grid")
    {
        const auto& file = touchstone::testing::golden_file();

        touchstone::testing::WorstPerField worst;
        std::size_t rows = 0;
        std::size_t refused = 0;

        for (std::size_t i = 0; i < file.cases.size(); i += sweep_scale) {
            const GoldenCase& row = file.cases[i];
            PriceAndGreeks bumped{};
            try {
                bumped = touchstone::bump_greeks(row.option, row.market);
            } catch (const std::invalid_argument&) {
                ++refused;
                continue;
            }
            ++rows;
            worst.observe(bumped, touchstone::price_and_greeks(row.option, row.market), row);
        }

        std::ostringstream header;
        header << "bumped vs analytic over " << rows << " rows (" << refused
               << " refused: a bump would have left the domain)";
        MESSAGE(worst.report(header.str(), &tolerance));

        CHECK(rows > 7000u / sweep_scale);
        worst.check(tolerance);
        // The price is not a difference quotient at all: it is the pricer's own
        // answer, passed through. Anything but zero means the wrong call was
        // returned.
        CHECK(worst.error(0) == 0.0);
    }

    TEST_CASE("the bump size has an optimum, and it is where the analysis says")
    {
        // One bump varied at a time from 1e-9 to 1e-2, everything else at its
        // default. Truncation dominates above the optimum and grows as `h^2`;
        // cancellation dominates below it and grows as the bump shrinks. Both
        // sides are asserted, because a scheme with only one of them would be a
        // scheme where one of the two error terms is missing.
        struct Axis {
            const char* name;
            std::size_t field;                 ///< index into `fields`
            double BumpSizes::* size;
            double best;                       ///< the default, and the measured optimum
        };
        const Axis axes[] = {
            {"spot (delta)", 1, &BumpSizes::spot_relative, 1e-6},
            {"spot (gamma)", 2, &BumpSizes::spot_relative_for_gamma, 3e-5},
            {"vol (vega)", 3, &BumpSizes::vol_absolute, 1e-6},
            {"rate (rho)", 5, &BumpSizes::rate_absolute, 1e-6},
        };
        const double sizes[] = {1e-9, 1e-8, 3e-7, 1e-6, 3e-5, 1e-3, 1e-2};

        // A small, fixed sample of the grid: this is measuring the shape of a
        // curve in the bump size, not sweeping the option space again.
        const BlackScholesMarket markets[] = {
            {100.0, 0.30, 0.05, 0.02}, {60.0, 0.15, -0.005, 0.0}, {150.0, 0.60, 0.01, 0.05}};
        const EuropeanVanilla options[] = {{100.0, 1.0, OptionType::Call},
                                           {120.0, 0.25, OptionType::Put},
                                           {80.0, 5.0, OptionType::Call}};

        std::ostringstream table;
        table << "worst scaled |bumped - analytic| against bump size";
        table << "\n    " << std::left << std::setw(14) << "axis";
        for (const double h : sizes) {
            table << std::setw(11) << h;
        }
        table << std::right;

        for (const Axis& axis : axes) {
            std::vector<double> measured;
            for (const double h : sizes) {
                double worst = 0.0;
                for (const BlackScholesMarket& market : markets) {
                    for (const EuropeanVanilla& option : options) {
                        BumpSizes bumps{};
                        bumps.*(axis.size) = h;
                        if (market.vol < bumps.vol_absolute
                            || option.expiry_years < bumps.expiry_absolute) {
                            continue;
                        }
                        const PriceAndGreeks bumped =
                            touchstone::bump_greeks(option, market, bumps);
                        const PriceAndGreeks analytic = touchstone::price_and_greeks(option, market);
                        const double reference = analytic.*(fields[axis.field].value);
                        const double got = bumped.*(fields[axis.field].value);
                        worst = std::max(worst, touchstone::testing::scaled_error(got, reference));
                    }
                }
                measured.push_back(worst);
            }

            table << "\n    " << std::left << std::setw(14) << axis.name << std::right;
            for (const double value : measured) {
                std::ostringstream cell;
                cell << std::scientific << std::setprecision(2) << value;
                table << std::setw(11) << cell.str();
            }

            const std::string name = axis.name;
            CAPTURE(name);

            // The curve has an interior minimum, and it is at the default.
            const std::size_t best =
                static_cast<std::size_t>(std::min_element(measured.begin(), measured.end())
                                         - measured.begin());
            const std::size_t expected = static_cast<std::size_t>(
                std::find(std::begin(sizes), std::end(sizes), axis.best) - std::begin(sizes));
            REQUIRE(expected < measured.size());
            CHECK(best == expected);

            // Truncation on one side of it, cancellation on the other. Both, not
            // one: a scheme with only truncation would be a scheme missing an
            // error term, and a test that checked only the large bumps would not
            // notice.
            CHECK(measured.back() > measured[best] * 10.0);
            CHECK(measured.front() > measured[best] * 10.0);
        }
        MESSAGE(table.str());
    }

    TEST_CASE("bumping a grid gets the grid's Greeks, at the grid's bump size")
    {
        // The reason bump Greeks are in the library and not only in the tests:
        // they work on a pricer that has no formula for vega. The finite
        // -difference grid is such a pricer, and bumping it produces all six.
        //
        // The bumps here are a hundred to a thousand times the defaults, and the
        // header says why: the balance is between truncation and the *pricer's*
        // own error, which for a grid is far above machine precision. The default
        // bumps would divide the grid's discretisation noise by 1e-6 and report
        // the result as a Greek.
        const BlackScholesMarket market{100.0, 0.30, 0.05, 0.02};
        const EuropeanVanilla call{100.0, 1.0, OptionType::Call};

        touchstone::PdeSettings grid{};
        const auto on_the_grid = touchstone::testing::grid_pricer(grid);

        const BumpSizes wide = touchstone::testing::grid_bumps();

        const PriceAndGreeks analytic = touchstone::price_and_greeks(call, market);
        const PriceAndGreeks bumped = touchstone::bump_greeks(call, market, wide, on_the_grid);

        std::ostringstream report;
        report << "Greeks by bumping the Crank-Nicolson grid, against the closed form";
        double worst = 0.0;
        for (std::size_t f = 1; f < fields.size(); ++f) {
            const double reference = analytic.*(fields[f].value);
            const double got = bumped.*(fields[f].value);
            const double error = touchstone::testing::scaled_error(got, reference);
            worst = std::max(worst, error);
            report << "\n    " << std::left << std::setw(14) << fields[f].name << std::right
                   << std::fixed << std::setprecision(8) << std::setw(16) << got << " vs "
                   << std::setw(16) << reference << "   scaled error " << std::scientific
                   << std::setprecision(3) << error;
        }
        MESSAGE(report.str());
        CHECK(worst < 1e-5);

        // And the header's warning, measured: with the defaults instead of these
        // bumps, the *second* difference collapses and the first one barely
        // notices.
        //
        // That asymmetry is the whole finding. A first difference divides by `h`,
        // and the grid's error varies smoothly with the spot — it rebuilds itself
        // around each bumped spot — so the same bias appears in both legs and
        // subtracts out, and delta's error moves by less than a factor of ten
        // between bumps three decades apart. Gamma divides by `h^2`, which turns
        // what is left of the grid's error into that over `h^2`: at the default
        // bumps, a relative error more than fifty times the wide bumps' (asserted
        // below; it measures over two hundred).
        const PriceAndGreeks too_fine = touchstone::bump_greeks(call, market, {}, on_the_grid);
        const auto relative = touchstone::testing::relative_error;
        const double fine_gamma = relative(too_fine.gamma, analytic.gamma);
        const double wide_gamma = relative(bumped.gamma, analytic.gamma);
        const double fine_delta = relative(too_fine.delta, analytic.delta);
        const double wide_delta = relative(bumped.delta, analytic.delta);
        MESSAGE("off the grid, default bumps vs wide bumps"
                << "\n    gamma  " << std::scientific << std::setprecision(3) << fine_gamma
                << " vs " << wide_gamma << "\n    delta  " << fine_delta << " vs " << wide_delta);
        CHECK(fine_gamma > wide_gamma * 50.0);
        // Delta, on the same two bump sizes, moves by less than a factor of ten:
        // the claim is about the second difference, and asserting it for the first
        // would be asserting something the measurement contradicts.
        CHECK(fine_delta < wide_delta * 10.0);
        CHECK(wide_delta < fine_delta * 10.0);
    }

    TEST_CASE("a bump that would leave the domain is refused")
    {
        const BlackScholesMarket market{100.0, 0.2, 0.03, 0.01};
        const EuropeanVanilla call{100.0, 1.0, OptionType::Call};

        const auto refused = [](const EuropeanVanilla& option, const BlackScholesMarket& state,
                                const BumpSizes& sizes) {
            CHECK_THROWS_AS(touchstone::require_valid(option, state, sizes), std::invalid_argument);
            CHECK_THROWS_AS(touchstone::bump_greeks(option, state, sizes), std::invalid_argument);
        };

        // A spot of zero has no relative bump.
        refused(call, {0.0, 0.2, 0.03, 0.01}, {});
        // A volatility or an expiry smaller than its own bump would go negative.
        refused(call, {100.0, 1e-9, 0.03, 0.01}, {});
        refused({100.0, 1e-9, OptionType::Call}, market, {});
        // Nonsense bump sizes.
        BumpSizes bad{};
        bad.vol_absolute = 0.0;
        refused(call, market, bad);
        bad = BumpSizes{};
        bad.spot_relative = -1e-6;
        refused(call, market, bad);

        // The domain is the closed form's, inherited.
        refused(call, {-1.0, 0.2, 0.03, 0.01}, {});

        // A one-sided difference is not offered as a consolation: the refusal is
        // the answer, and the closed form's exact Greeks are the alternative.
        CHECK(std::isfinite(touchstone::vega(call, {100.0, 1e-9, 0.03, 0.01})));
        CHECK_NOTHROW(touchstone::require_valid(call, market, BumpSizes{}));
    }
}
