// Early exercise: the one thing in v1 that only the grid can price.
//
// There is no closed form for an American vanilla, so the usual shape of a test
// here — compute it two ways and compare — is not available. What is available
// is four things of decreasing strength, and this file uses all four.
//
//   1. **Two exact identities.** An American call on an underlying with no
//      dividend yield and a non-negative rate is worth *exactly* its European
//      counterpart; so is an American put with a non-positive rate and a
//      non-negative yield. On those rows the American solver can be held to the
//      closed form's fifteen digits, which is a stronger statement than any
//      lattice could support.
//
//      The conditions are not decoration. "Never exercise an American call
//      early" is a theorem about non-negative rates: at `r < 0` the strike is
//      worth more later than now, and immediate exercise can be optimal. The
//      golden file contains rows where it is, and the test below names one.
//
//   2. **Inequalities that hold everywhere.** At least the European value, at
//      least the intrinsic value, and — where the derivation holds — inside the
//      American put-call bounds.
//
//   3. **An independent oracle.** `golden/american_vanilla.json`: QuantLib's
//      Leisen-Reimer lattice at two thousand steps, with Cox-Ross-Rubinstein and
//      Tian beside it, and the disagreement among the three carried per row as
//      the oracle's own uncertainty. Compared against that uncertainty rather
//      than against a tolerance invented here.
//
//   4. **Convergence.** The American price on a refining sequence of grids,
//      approaching one value.
//
// The solver itself — the direction of the projected sweep, and that it returns
// the complementarity solution rather than something plausible — is established
// in `test_tridiagonal.cpp` against projected SOR, on the matrices this scheme
// builds. That is the part a price comparison cannot reach.

#include "american_file.hpp"
#include "golden_file.hpp"

#include <touchstone/black_scholes.hpp>
#include <touchstone/pde.hpp>

#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <iomanip>
#include <map>
#include <sstream>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

#ifndef TOUCHSTONE_SWEEP_SCALE
#define TOUCHSTONE_SWEEP_SCALE 1
#endif

namespace {

using touchstone::BlackScholesMarket;
using touchstone::EuropeanVanilla;
using touchstone::Exercise;
using touchstone::OptionType;
using touchstone::PdeResult;
using touchstone::PdeSettings;
using touchstone::testing::AmericanCase;

constexpr std::size_t grid_stride = TOUCHSTONE_SWEEP_SCALE;

[[nodiscard]] PdeSettings american_settings()
{
    PdeSettings settings{};
    settings.space_intervals = 1024;
    settings.time_steps = 512;
    settings.exercise = Exercise::American;
    return settings;
}

[[nodiscard]] PdeSettings european_settings()
{
    PdeSettings settings = american_settings();
    settings.exercise = Exercise::European;
    return settings;
}

/// The option's own scale — its value, or the strike where that is larger. The
/// scale a free-boundary error lives on, and the scale the oracle's spread is
/// quoted in.
[[nodiscard]] double option_scale(const AmericanCase& row)
{
    return std::max(std::abs(row.price), row.option.strike);
}

}  // namespace

TEST_SUITE("american")
{
    TEST_CASE("the american file is the one these tests were written against")
    {
        const auto& file = touchstone::testing::american_file();
        MESSAGE("american file " << file.path << "\n    schema  " << file.schema
                                 << "\n    oracle  QuantLib " << file.oracle_version << "\n    engine  "
                                 << file.engine << "\n    worst lattice spread  "
                                 << std::scientific << std::setprecision(3) << file.worst_spread);
        CHECK(file.schema == "touchstone/golden/american_vanilla@1");
        CHECK(file.cases.size() == file.declared_cases);
        CHECK(file.cases.size() == 864u);

        std::size_t identity_rows = 0;
        for (const AmericanCase& row : file.cases) {
            if (row.equals_european()) {
                ++identity_rows;
            }
        }
        MESSAGE(identity_rows << " rows where American exercise is worth exactly European");
        CHECK(identity_rows > 300u);
    }

    TEST_CASE("where early exercise is worthless, the grid says so exactly")
    {
        // The strongest check available on the American solver: on these rows the
        // answer is a closed form, so the projected sweep has to reproduce it to
        // the accuracy of the European scheme and not one part looser. A
        // projection applied where it should not bind — a direction chosen
        // wrongly, a boundary condition raised to intrinsic where it should not
        // be — shows up here first.
        const auto& file = touchstone::testing::american_file();
        const PdeSettings settings = american_settings();

        double worst = 0.0;
        std::string worst_at;
        std::size_t rows = 0;
        double worst_against_european_grid = 0.0;

        for (const AmericanCase& row : file.cases) {
            if (!row.equals_european()) {
                continue;
            }
            ++rows;
            const double exact = touchstone::price(row.option, row.market);
            const PdeResult american = touchstone::crank_nicolson(row.option, row.market, settings);
            const PdeResult european =
                touchstone::crank_nicolson(row.option, row.market, european_settings());

            const double scale = std::max(std::abs(exact), row.market.spot);
            const double error = std::abs(american.price - exact) / scale;
            if (error > worst) {
                worst = error;
                worst_at = touchstone::testing::describe(row);
            }
            // And the two runs are the same run: the projection never fired.
            worst_against_european_grid =
                std::max(worst_against_european_grid,
                         std::abs(american.price - european.price) / scale);
        }

        std::ostringstream report;
        report << "identity rows (" << rows << "): American exercise worth exactly European"
               << "\n    worst |american grid - closed form| scaled by max(|V|, S)  "
               << std::scientific << std::setprecision(3) << worst
               << "\n    worst |american grid - european grid|                     "
               << worst_against_european_grid << "\n    worst at " << worst_at;
        MESSAGE(report.str());

        CHECK(rows > 300u);
        CHECK_MESSAGE(worst <= 3e-5, worst_at);
        // The projection is a no-op on these rows — but not to the last bit, and
        // the reason is worth knowing. Brennan and Schwartz's sweep for a *put*
        // eliminates from the high end down where Thomas eliminates from the low
        // end up: the same system, factored the other way round, and two
        // factorisations of one matrix agree to round-off rather than exactly.
        // For a *call* the direction is Thomas's own, and there the two runs are
        // bit-identical. The worst row below is a put, as it has to be.
        CHECK(worst_against_european_grid < 1e-11);
    }

    TEST_CASE("a negative rate makes early exercise of a call optimal")
    {
        // The counterexample to the folklore, priced. With `r < 0` the strike is
        // worth more later than now, so holding the call costs money and
        // exercising it immediately can be worth more than its European value.
        // The golden file has such rows and the lattice agrees with the grid on
        // them; both are above the European price, which is the whole point.
        const auto& file = touchstone::testing::american_file();
        const PdeSettings settings = american_settings();

        std::size_t found = 0;
        double largest_premium = 0.0;
        std::string largest_at;

        for (const AmericanCase& row : file.cases) {
            if (row.option.type != OptionType::Call || row.market.rate >= 0.0) {
                continue;
            }
            const double european = touchstone::price(row.option, row.market);
            const double premium = row.price - european;
            if (premium <= 1e-6 * std::max(european, 1.0)) {
                continue;
            }
            ++found;
            const PdeResult american = touchstone::crank_nicolson(row.option, row.market, settings);
            CAPTURE(touchstone::testing::describe(row));
            CHECK(american.price > european);
            if (premium > largest_premium) {
                largest_premium = premium;
                largest_at = touchstone::testing::describe(row);
            }
        }

        MESSAGE("calls at a negative rate worth more than European: " << found
                                                                      << " rows; largest premium "
                                                                      << std::fixed
                                                                      << std::setprecision(4)
                                                                      << largest_premium
                                                                      << "\n    at " << largest_at);
        CHECK(found > 20u);
    }

    TEST_CASE("the american golden file, priced on the grid")
    {
        const auto& file = touchstone::testing::american_file();
        const PdeSettings settings = american_settings();

        double worst_against_spread = 0.0;
        double worst_scaled = 0.0;
        std::string worst_at;
        std::string spread_worst_at;
        std::size_t rows = 0;

        for (std::size_t i = 0; i < file.cases.size(); i += grid_stride) {
            const AmericanCase& row = file.cases[i];
            ++rows;
            const PdeResult on_grid = touchstone::crank_nicolson(row.option, row.market, settings);
            const double scale = option_scale(row);
            const double error = std::abs(on_grid.price - row.price);

            if (error / scale > worst_scaled) {
                worst_scaled = error / scale;
                worst_at = touchstone::testing::describe(row);
            }

            // Against the oracle's own uncertainty about this row, with a floor:
            // where all three lattices returned the intrinsic value exactly the
            // spread is zero, and the lattices are still only good to about 5e-7
            // scaled — measured on the identity rows, where a closed form says
            // what they were really worth.
            const double allowance = row.spread + 1e-6 * scale;
            const double against = error / allowance;
            if (against > worst_against_spread) {
                worst_against_spread = against;
                spread_worst_at = touchstone::testing::describe(row);
            }
        }

        std::ostringstream report;
        report << "american golden file by Crank-Nicolson with a projected sweep: " << rows
               << " rows at " << settings.space_intervals << " x " << settings.time_steps
               << "\n    worst |grid - lattice| scaled by max(|V|, K)   " << std::scientific
               << std::setprecision(3) << worst_scaled << "\n        at " << worst_at
               << "\n    worst as a multiple of the row's lattice spread " << std::fixed
               << std::setprecision(2) << worst_against_spread << "\n        at "
               << spread_worst_at;
        MESSAGE(report.str());

        CHECK_MESSAGE(worst_scaled <= 5e-4, worst_at);
        CHECK_MESSAGE(worst_against_spread <= 12.0, spread_worst_at);
    }

    TEST_CASE("every American value is at least European and at least intrinsic")
    {
        // Two inequalities that hold for every input, with no conditions, and
        // that a solver can break in either direction: a projection that never
        // fires loses the first, and one that fires on the wrong side loses the
        // second.
        const auto& file = touchstone::testing::american_file();
        const PdeSettings settings = american_settings();

        double worst_below_european = 0.0;
        double worst_below_intrinsic = 0.0;
        std::string worst_at;
        std::size_t with_premium = 0;
        std::size_t rows = 0;

        for (std::size_t i = 0; i < file.cases.size(); i += grid_stride) {
            const AmericanCase& row = file.cases[i];
            ++rows;
            const double european = touchstone::price(row.option, row.market);
            const double intrinsic = std::max(
                touchstone::option_sign(row.option.type) * (row.market.spot - row.option.strike),
                0.0);
            const PdeResult american = touchstone::crank_nicolson(row.option, row.market, settings);
            const double scale = std::max(std::abs(european), row.market.spot);

            const double below_european = (european - american.price) / scale;
            if (below_european > worst_below_european) {
                worst_below_european = below_european;
                worst_at = touchstone::testing::describe(row);
            }
            worst_below_intrinsic =
                std::max(worst_below_intrinsic, (intrinsic - american.price) / scale);
            if (american.price > european * (1.0 + 1e-6) + 1e-9) {
                ++with_premium;
            }
        }

        MESSAGE("bounds over " << rows << " rows"
                               << "\n    worst shortfall against European   " << std::scientific
                               << std::setprecision(3) << worst_below_european << "\n    worst "
                               << "shortfall against intrinsic  " << worst_below_intrinsic
                               << "\n    " << with_premium
                               << " rows carry a material early-exercise premium"
                               << "\n    worst at " << worst_at);

        // The shortfall allowance is the European grid's own error, not slack:
        // both numbers here are grid values, and the grid is accurate to about
        // 3e-5 of the underlying's scale.
        CHECK_MESSAGE(worst_below_european <= 3e-5, worst_at);
        CHECK(worst_below_intrinsic <= 3e-5);
        // And the premium is real on a large part of the grid, or these
        // inequalities are being satisfied by an American solver that is quietly
        // European.
        CHECK(with_premium > rows / 3);
    }

    TEST_CASE("the American put-call bounds, where their derivation holds")
    {
        // S e^{-qT} - K  <=  C_A - P_A  <=  S - K e^{-rT}, for r >= 0 and q >= 0.
        //
        // Asserted only under those conditions, and the file contains rows
        // outside them where the lower bound genuinely fails — the same negative
        // -rate corner that makes early exercise of a call optimal. Testing it
        // everywhere would be testing a statement that is false.
        const auto& file = touchstone::testing::american_file();
        const PdeSettings settings = american_settings();

        struct Key {
            double spot, strike, vol, rate, yield;
            int days;
            [[nodiscard]] bool operator<(const Key& other) const
            {
                return std::tie(spot, strike, vol, rate, yield, days)
                       < std::tie(other.spot, other.strike, other.vol, other.rate, other.yield,
                                  other.days);
            }
        };

        std::map<Key, std::pair<double, double>> priced;  // call, put
        for (std::size_t i = 0; i < file.cases.size(); i += grid_stride) {
            const AmericanCase& row = file.cases[i];
            if (row.market.rate < 0.0 || row.market.dividend_yield < 0.0) {
                continue;
            }
            const Key key{row.market.spot,  row.option.strike,        row.market.vol,
                          row.market.rate,  row.market.dividend_yield, row.expiry_days};
            const double value = touchstone::crank_nicolson(row.option, row.market, settings).price;
            auto& pair = priced[key];
            (row.option.type == OptionType::Call ? pair.first : pair.second) = value;
        }

        double worst_low = 0.0;
        double worst_high = 0.0;
        std::size_t pairs = 0;
        for (const auto& [key, values] : priced) {
            if (values.first == 0.0 || values.second == 0.0) {
                continue;  // only one side of the pair survived the stride
            }
            ++pairs;
            const double years = static_cast<double>(key.days) / 365.0;
            const double difference = values.first - values.second;
            const double low = key.spot * std::exp(-key.yield * years) - key.strike;
            const double high = key.spot - key.strike * std::exp(-key.rate * years);
            const double scale = std::max(std::abs(difference), key.strike);
            worst_low = std::max(worst_low, (low - difference) / scale);
            worst_high = std::max(worst_high, (difference - high) / scale);
        }

        MESSAGE("American put-call bounds over " << pairs << " grid-priced pairs with r >= 0"
                                                 << "\n    worst breach of the lower bound "
                                                 << std::scientific << std::setprecision(3)
                                                 << worst_low
                                                 << "\n    worst breach of the upper bound "
                                                 << worst_high);
        CHECK(pairs > 50u / grid_stride);
        CHECK(pairs > 4u);
        CHECK(worst_low <= 3e-5);
        CHECK(worst_high <= 3e-5);
    }

    TEST_CASE("the American price converges at the order the sweep is worth")
    {
        // The strongest test of the projected sweep that a price can carry, and
        // the only one that catches the mistake it is most likely to make.
        //
        // Brennan and Schwartz's sweep must substitute *towards* the exercise
        // region: `pde.cpp` picks the direction from the option type, and a put's
        // is the opposite of a call's. Point one of them the wrong way and the
        // answer is still *consistent* — it converges to the same limit, so no
        // comparison at one resolution can see it — but it converges at first
        // order instead of second, because at every step the constraint is
        // applied to a node whose neighbour has not been constrained yet and the
        // free boundary lands a node out.
        //
        // So the test is the rate, not the value. Measured, on the two rows below:
        //
        //     row                      correct direction    reversed
        //     put  S=90 K=100          3.40 3.14 2.95       2.21 2.11 2.06
        //     call S=120 K=90 q=0.04   3.95 4.00 4.00       2.28 2.16 2.09
        //
        // A ratio of four is second order and two is first. The put's rate is
        // short of four even when it is right — the free boundary is only located
        // to `O(dx)` and for a put that costs more than it does for this call —
        // which is why the bound below is a measured figure per row rather than a
        // theoretical one shared between them.
        struct Row {
            const char* what;
            BlackScholesMarket market;
            EuropeanVanilla option;
            double least_ratio;      ///< bound on the worst successive-move ratio
            double least_premium;    ///< the early-exercise premium must be real
        };
        const Row rows[] = {
            {"put  S=90 K=100 vol=0.25 r=0.06",
             {90.0, 0.25, 0.06, 0.0},
             {100.0, 1.0, OptionType::Put},
             2.5,
             0.3},
            {"call S=120 K=90 vol=0.30 r=0.05 q=0.04",
             {120.0, 0.30, 0.05, 0.04},
             {90.0, 5.0, OptionType::Call},
             3.2,
             1.0},
        };

        for (const Row& row : rows) {
            std::ostringstream table;
            table << "American convergence, " << row.what;

            std::vector<double> prices;
            for (const std::size_t n : {256u, 512u, 1024u, 2048u, 4096u}) {
                PdeSettings settings{};
                settings.space_intervals = n;
                settings.time_steps = n / 2;
                settings.exercise = Exercise::American;
                const PdeResult result = touchstone::crank_nicolson(row.option, row.market, settings);
                prices.push_back(result.price);
                table << "\n    " << std::setw(6) << n << " x " << std::setw(5) << (n / 2) << "  "
                      << std::fixed << std::setprecision(9) << result.price;
            }

            double worst_ratio = std::numeric_limits<double>::infinity();
            for (std::size_t i = 2; i < prices.size(); ++i) {
                const double before = std::abs(prices[i - 1] - prices[i - 2]);
                const double after = std::abs(prices[i] - prices[i - 1]);
                REQUIRE(after > 0.0);
                const double ratio = before / after;
                table << "\n        move ratio " << std::fixed << std::setprecision(2) << ratio;
                worst_ratio = std::min(worst_ratio, ratio);
            }

            const double european = touchstone::price(row.option, row.market);
            const double premium = prices.back() - european;
            table << "\n    worst ratio " << std::fixed << std::setprecision(2) << worst_ratio
                  << " (bound " << row.least_ratio << ");  European " << std::setprecision(9)
                  << european << ", early-exercise premium " << premium;
            MESSAGE(table.str());

            const std::string what = row.what;
            CAPTURE(what);
            CHECK(worst_ratio > row.least_ratio);
            // And the premium is real, or the rate above is the European
            // scheme's and says nothing about the projection at all.
            CHECK(premium > row.least_premium);
        }
    }
}
