// Running the pricing map backwards, and Brent's method on its own.
//
// The roadmap's exit criterion for this is one sentence: "implied vol
// round-trips golden prices to 1e-8". The sentence has two readings and this
// file tests both, because only one of them is satisfiable everywhere.
//
//   - **The price round trip.** Take a golden price, solve for the volatility,
//     price again at what came back, and compare with where you started. That is
//     well posed on every row where a solution exists, and it is what the
//     criterion is measured on below.
//
//   - **The volatility round trip.** Compare the recovered volatility with the
//     one the golden file was generated at. That is well posed only where the
//     price depends on the volatility at all. On 1,776 of the 7,200 rows vega is
//     below 1e-6, and on the worst of them a whole volatility point moves the
//     price by less than one unit in its last place: the implied volatility is
//     mathematically unique and numerically absent. Those rows are reported with
//     the bound the price actually affords — `tolerance / vega` — rather than
//     asserted against a figure the arithmetic cannot deliver.
//
// Reporting the second reading rather than quietly testing only the first is the
// point. A solver that returned 0.2 for everything would pass a price round trip
// on the dead rows and fail here.

#include "golden_file.hpp"

#include <touchstone/black_scholes.hpp>
#include <touchstone/implied_vol.hpp>
#include <touchstone/root_finding.hpp>

#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <iomanip>
#include <limits>
#include <numbers>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using touchstone::EuropeanVanilla;
using touchstone::ImpliedVolMethod;
using touchstone::ImpliedVolResult;
using touchstone::ImpliedVolSettings;
using touchstone::OptionType;
using touchstone::QuotedMarket;
using touchstone::RootSearch;
using touchstone::testing::GoldenCase;

[[nodiscard]] QuotedMarket quoted(const GoldenCase& row)
{
    return QuotedMarket{row.market.spot, row.market.rate, row.market.dividend_yield};
}

}  // namespace

TEST_SUITE("implied-vol")
{
    TEST_CASE("Brent finds roots that are known without it")
    {
        struct Problem {
            const char* what;
            double lower;
            double upper;
            double root;
            double (*f)(double);
        };

        const Problem problems[] = {
            {"x^3 - 2x - 5, Wallis's cubic", 2.0, 3.0, 2.0945514815423265,
             [](double x) { return x * x * x - 2.0 * x - 5.0; }},
            {"cos x - x", 0.0, 1.0, 0.7390851332151607,
             [](double x) { return std::cos(x) - x; }},
            {"exp(x) - 3", 0.0, 3.0, std::numbers::ln2 + std::log(1.5),
             [](double x) { return std::exp(x) - 3.0; }},
            // A root the secant slides past and bisection crawls to: flat over
            // most of the bracket and near-vertical at the root.
            {"x^25, flat then vertical", -1.0, 1.3, 0.0,
             [](double x) { return std::pow(x, 25.0); }},
            // Continuous, monotone, and with a derivative that vanishes at the
            // root — where Newton would take forever and Brent does not care.
            {"cbrt(x - 0.3) shape", -2.0, 5.0, 0.3,
             [](double x) { return std::cbrt(x - 0.3); }},
        };

        std::ostringstream table;
        table << "Brent on roots known independently";
        for (const Problem& problem : problems) {
            RootSearch search{};
            search.x_tolerance = 1e-15;
            search.max_iterations = 200;
            const touchstone::RootResult found =
                touchstone::brent(problem.f, problem.lower, problem.upper, search);
            table << "\n    " << std::left << std::setw(30) << problem.what << std::right
                  << "  root " << std::setprecision(17) << found.root << "  in "
                  << found.iterations << " calls";
            const std::string what = problem.what;
            CAPTURE(what);
            CHECK(found.converged);
            CHECK(std::abs(found.root - problem.root)
                  <= 1e-9 * std::max(1.0, std::abs(problem.root)));
            // Brent's guarantee is about bracket halvings, not function calls:
            // it never needs many more halvings than bisection, and bisection on
            // these brackets to a tolerance of 1e-15 needs about fifty. The
            // interpolation steps it interleaves are what take the count above
            // that, and on `x^25` — a function that is 1e-250 over most of its
            // bracket — they take it to 128. That is the honest ceiling for this
            // set, and it is why the fallback in `implied_vol` is given two
            // hundred rather than the hundred this defaults to.
            CHECK(found.iterations <= 140u);
        }
        MESSAGE(table.str());
    }

    TEST_CASE("a bracket without a sign change is reported, not guessed at")
    {
        const auto positive = [](double x) { return x * x + 1.0; };
        const touchstone::RootResult found = touchstone::brent(positive, -1.0, 1.0, {});
        CHECK_FALSE(found.converged);
        // An end of the bracket, whichever is closer to zero — the most useful
        // thing to hand back. Here the two ends are the same height, so it is 2.
        CHECK(std::abs(found.value) == doctest::Approx(2.0));
        CHECK(std::abs(found.root) == doctest::Approx(1.0));

        // An end that is already a root is answered without iterating.
        const auto through_zero = [](double x) { return x - 2.0; };
        const touchstone::RootResult exact = touchstone::brent(through_zero, 2.0, 5.0, {});
        CHECK(exact.converged);
        CHECK(exact.root == 2.0);
    }

    TEST_CASE("the price round trip, on every golden row that has a solution")
    {
        // The exit criterion. Every row of the main grid and the edge block:
        // price -> volatility -> price, compared the way `SCHEMA.md` compares
        // anything, and required to be inside 1e-8.
        const auto& file = touchstone::testing::golden_file();

        double worst = 0.0;
        std::string worst_at;
        std::size_t solved = 0;
        std::size_t refused = 0;
        std::size_t unconverged = 0;
        std::size_t by_newton = 0;
        std::size_t by_brent = 0;
        std::size_t at_zero = 0;
        std::size_t worst_iterations = 0;

        const auto walk = [&](const std::vector<GoldenCase>& rows) {
            for (const GoldenCase& row : rows) {
                const QuotedMarket market = quoted(row);
                ImpliedVolResult found{};
                try {
                    found = touchstone::implied_vol(row.option, market, row.reference.price);
                } catch (const std::invalid_argument&) {
                    // The oracle's own price is below the zero-volatility price
                    // by more than a rounding: 106 rows of the file carry a
                    // slightly negative price, which SCHEMA.md documents and
                    // which no volatility produces.
                    ++refused;
                    continue;
                }
                ++solved;
                if (!found.converged) {
                    ++unconverged;
                }
                switch (found.method) {
                    case ImpliedVolMethod::Newton: ++by_newton; break;
                    case ImpliedVolMethod::Brent: ++by_brent; break;
                    case ImpliedVolMethod::Exact: ++at_zero; break;
                }
                worst_iterations = std::max(worst_iterations, found.iterations);

                const double repriced = touchstone::price(row.option, market.at(found.vol));
                const double error =
                    touchstone::testing::scaled_error(repriced, row.reference.price);
                if (error > worst) {
                    worst = error;
                    worst_at = touchstone::testing::describe(row);
                }
            }
        };
        walk(file.cases);
        walk(file.edge_cases);

        std::ostringstream report;
        report << "price round trip over " << solved << " rows (" << refused
               << " refused as below the zero-volatility price)"
               << "\n    worst scaled |repriced - golden|  " << std::scientific
               << std::setprecision(3) << worst << "   (criterion 1e-8)"
               << "\n    Newton " << by_newton << ", Brent " << by_brent << ", exact at zero "
               << at_zero << ", not converged " << unconverged << "\n    worst iteration count "
               << worst_iterations << "\n    worst at " << worst_at;
        MESSAGE(report.str());

        CHECK(solved > 7000u);
        CHECK(unconverged == 0u);
        CHECK_MESSAGE(worst <= 1e-8, worst_at);
        // Tighter than the criterion, so a regression that stayed inside 1e-8
        // still fails here rather than quietly consuming the margin.
        CHECK(worst <= 1e-11);
    }

    TEST_CASE("the volatility round trip, where the price identifies a volatility")
    {
        // A price is a number of finite precision, so a volatility is recoverable
        // only to about `tolerance / vega`. That is not a caveat, it is the
        // measurement: this test computes that bound per row and requires the
        // error to be inside it, which is a *stronger* statement than any fixed
        // tolerance because it holds on the dead rows too.
        const auto& file = touchstone::testing::golden_file();
        const ImpliedVolSettings settings{};

        double worst_absolute = 0.0;
        double worst_against_bound = 0.0;
        std::string worst_at;
        std::string bound_worst_at;
        std::size_t identifiable = 0;
        std::size_t dead = 0;
        double worst_identifiable = 0.0;

        for (const GoldenCase& row : file.cases) {
            const QuotedMarket market = quoted(row);
            ImpliedVolResult found{};
            try {
                found = touchstone::implied_vol(row.option, market, row.reference.price, settings);
            } catch (const std::invalid_argument&) {
                continue;
            }

            const double error = std::abs(found.vol - row.market.vol);
            if (error > worst_absolute) {
                worst_absolute = error;
                worst_at = touchstone::testing::describe(row);
            }

            // What the price affords: the tolerance the solver stopped at, divided
            // by the slope available between where it stopped and where it should
            // have stopped.
            //
            // The slope is the *smaller* of the two vegas, not the one at the
            // answer. Vega is unimodal in the volatility — it peaks at Manaster
            // and Koehler's point and falls away either side — so the smallest
            // slope on any interval is at one of its ends, and it is the smallest
            // slope that decides how far apart two volatilities can be while
            // producing prices a tolerance apart. Taking the vega at the answer
            // instead understates the bound by a factor of thirty on the worst
            // row here: a deep in-the-money put whose vega at the recovered 0.2
            // is much larger than at the true 0.05.
            const double scale =
                touchstone::price_scale(row.option, market) * settings.price_tolerance;
            const double vega_at_truth = touchstone::vega(row.option, row.market);
            const double flattest = std::min(found.vega, vega_at_truth);
            const double affordable = (flattest > 0.0)
                                          ? scale / flattest
                                          : std::numeric_limits<double>::infinity();
            // A floor of a few ulps of the volatility itself: at a large vega the
            // bound above goes below the precision of the answer's own
            // representation, and no solver can beat that.
            const double bound = std::max(affordable, 8.0 * std::numeric_limits<double>::epsilon()
                                                          * std::max(row.market.vol, 1.0));
            const double against = error / bound;
            if (against > worst_against_bound) {
                worst_against_bound = against;
                bound_worst_at = touchstone::testing::describe(row);
            }

            if (found.vega > 1e-6) {
                ++identifiable;
                worst_identifiable = std::max(worst_identifiable, error);
            } else {
                ++dead;
            }
        }

        std::ostringstream report;
        report << "volatility round trip over " << (identifiable + dead) << " rows"
               << "\n    " << identifiable << " with vega above 1e-6: worst |sigma - sigma| "
               << std::scientific << std::setprecision(3) << worst_identifiable << "\n    " << dead
               << " with vega at or below 1e-6, where the price carries no volatility"
               << "\n    worst over all rows               " << worst_absolute << "\n        at "
               << worst_at << "\n    worst as a multiple of what the price affords  " << std::fixed
               << std::setprecision(3) << worst_against_bound << "\n        at " << bound_worst_at;
        MESSAGE(report.str());

        CHECK(identifiable > 4000u);
        CHECK(dead > 0u);
        // Every row, dead ones included, inside the resolution its own price has.
        //
        // Within a factor of two of it, rather than inside it exactly: the bound
        // is `tolerance / slope`, a linearisation, and the price is not linear in
        // the volatility over the interval it is applied to. The worst row comes
        // out at 1.00, which is the solver sitting exactly on the resolution its
        // input affords — the bound is tight, and a factor of two is the room the
        // linearisation needs rather than room the solver is using.
        CHECK_MESSAGE(worst_against_bound <= 2.0, bound_worst_at);
        // And where the volatility is identifiable at all, it comes back.
        CHECK(worst_identifiable < 1e-6);
    }

    TEST_CASE("Brent finishes what Newton cannot")
    {
        // Newton finishes every row of the golden file on its own — 6,910 of them,
        // in at most 27 steps — which is a good property of the solver and a bad
        // one for the fallback: a path nothing reaches is a path nothing tests.
        //
        // Giving Newton a budget of one step routes every row through Brent
        // instead. Brent's own budget is fixed inside the solver rather than
        // shared with Newton's, precisely so that this is a test of the fallback
        // and not of an exhausted iteration count.
        const auto& file = touchstone::testing::golden_file();
        ImpliedVolSettings crippled{};
        crippled.max_iterations = 1;

        std::size_t rows = 0;
        std::size_t fell_back = 0;
        double worst = 0.0;
        std::string worst_at;

        for (std::size_t i = 0; i < file.cases.size(); i += 7) {
            const GoldenCase& row = file.cases[i];
            const QuotedMarket market = quoted(row);
            ImpliedVolResult found{};
            try {
                found = touchstone::implied_vol(row.option, market, row.reference.price, crippled);
            } catch (const std::invalid_argument&) {
                continue;
            }
            ++rows;
            if (found.method == ImpliedVolMethod::Brent) {
                ++fell_back;
            }
            const double repriced = touchstone::price(row.option, market.at(found.vol));
            const double error = touchstone::testing::scaled_error(repriced, row.reference.price);
            if (error > worst) {
                worst = error;
                worst_at = touchstone::testing::describe(row);
            }
        }

        MESSAGE("with one Newton step allowed: " << fell_back << " of " << rows
                                                 << " rows finished in Brent; worst scaled reprice "
                                                 << std::scientific << std::setprecision(3) << worst
                                                 << "\n    at " << worst_at);
        CHECK(fell_back > rows * 9 / 10);
        // Brent alone, on one iteration of Newton's budget, still round-trips
        // inside the criterion.
        CHECK(worst <= 1e-8);
    }

    TEST_CASE("prices no volatility produces are refused")
    {
        const QuotedMarket market{100.0, 0.05, 0.01};
        const EuropeanVanilla call{100.0, 1.0, OptionType::Call};
        const EuropeanVanilla put{100.0, 1.0, OptionType::Put};

        const double floor_price = touchstone::lowest_price(call, market);
        const double ceiling = touchstone::highest_price(call, market);

        // The bounds are the model's, and they are what they claim to be.
        CHECK(floor_price == doctest::Approx(touchstone::price(call, market.at(0.0))));
        CHECK(ceiling == doctest::Approx(market.spot * std::exp(-market.dividend_yield * 1.0)));
        CHECK(touchstone::highest_price(put, market)
              == doctest::Approx(put.strike * std::exp(-market.rate * 1.0)));

        // Below the floor by more than a rounding: an arbitrage, not a quote.
        CHECK_THROWS_AS(touchstone::implied_vol(call, market, floor_price - 1.0),
                        std::invalid_argument);
        // At or above the asymptote: no finite volatility reaches it.
        CHECK_THROWS_AS(touchstone::implied_vol(call, market, ceiling), std::invalid_argument);
        CHECK_THROWS_AS(touchstone::implied_vol(call, market, ceiling + 1.0),
                        std::invalid_argument);
        // Not a number at all.
        CHECK_THROWS_AS(touchstone::implied_vol(call, market, std::nan("")),
                        std::invalid_argument);

        // Inside the search range but above what `max_vol` can price: a statement
        // about the search, and the message says so.
        ImpliedVolSettings narrow{};
        narrow.max_vol = 0.1;
        const double beyond = touchstone::price(call, market.at(0.5));
        CHECK_THROWS_AS(touchstone::implied_vol(call, market, beyond, narrow),
                        std::invalid_argument);

        // And nonsense settings.
        ImpliedVolSettings bad{};
        bad.max_vol = 0.0;
        CHECK_THROWS_AS(touchstone::implied_vol(call, market, 10.0, bad), std::invalid_argument);
        bad = ImpliedVolSettings{};
        bad.max_iterations = 0;
        CHECK_THROWS_AS(touchstone::implied_vol(call, market, 10.0, bad), std::invalid_argument);
        bad = ImpliedVolSettings{};
        bad.price_tolerance = 0.0;
        CHECK_THROWS_AS(touchstone::implied_vol(call, market, 10.0, bad), std::invalid_argument);

        // The zero-volatility price itself has the answer zero, exactly, and it
        // is reached without iterating.
        const ImpliedVolResult at_floor = touchstone::implied_vol(call, market, floor_price);
        CHECK(at_floor.vol == 0.0);
        CHECK(at_floor.method == ImpliedVolMethod::Exact);
        CHECK(at_floor.converged);
    }

    TEST_CASE("the solver is monotone in the price it is given")
    {
        // Vega is positive, so the map is increasing, so its inverse must be too.
        // A solver that landed on a different branch, or on the wrong side of a
        // bracket, would break this without breaking the round trip.
        const QuotedMarket market{100.0, 0.03, 0.01};
        const EuropeanVanilla call{100.0, 2.0, OptionType::Call};

        double previous = -1.0;
        for (const double vol : {0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0}) {
            const double target = touchstone::price(call, market.at(vol));
            const ImpliedVolResult found = touchstone::implied_vol(call, market, target);
            CAPTURE(vol);
            CHECK(found.converged);
            CHECK(found.vol > previous);
            CHECK(found.vol == doctest::Approx(vol).epsilon(1e-10));
            previous = found.vol;
        }
    }
}
