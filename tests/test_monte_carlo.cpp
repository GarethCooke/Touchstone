// Monte Carlo against the closed form, across the golden grid.
//
// The exit criterion this suite exists for reads "MC price within three
// standard errors of closed form across the golden grid", and it cannot be
// tested the way it reads. Three standard errors is the bound for *one*
// comparison: 99.73% of them fall inside it, so a grid of 7,200 rows expects
// about twenty outside, and a suite that demanded none would be red on a
// correct library and green only on a seed someone went looking for. Choosing
// that seed is the failure this file is written to avoid.
//
// So the criterion is tested as what it means rather than as what it says. Each
// row is standardised — (Monte Carlo minus closed form) over the standard error
// — and the whole grid is then a sample of z-scores whose mean, spread, worst
// value and count beyond three are all pinned. That is strictly stronger than
// the per-row bound: an estimator biased by a tenth of a standard error passes
// every individual three-sigma test on the grid and fails the test of the mean
// here by eight sigma.

#include "golden_file.hpp"
#include "rng_fixture.hpp"
#include "statistics.hpp"

#include <touchstone/black_scholes.hpp>
#include <touchstone/monte_carlo.hpp>
#include <touchstone/normal.hpp>
#include <touchstone/rng.hpp>

#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

// How much of the grid the sweeps walk: one row in every `TOUCHSTONE_SWEEP_SCALE`.
// One by default, so the whole grid; CI's sanitizer job sets it higher, for the
// reason `CMakeLists.txt` gives where the option is declared. Every bound in
// this file is computed from the number of rows actually swept, so a scaled run
// is a smaller valid test rather than a weaker version of this one.
#ifndef TOUCHSTONE_SWEEP_SCALE
#define TOUCHSTONE_SWEEP_SCALE 1
#endif

namespace {

using touchstone::BlackScholesMarket;
using touchstone::EuropeanVanilla;
using touchstone::MonteCarloResult;
using touchstone::MonteCarloSettings;
using touchstone::OptionType;
using touchstone::Scheme;
using touchstone::Xoshiro128SS;
using touchstone::norm_cdf;
using touchstone::norm_inv;
using touchstone::option_sign;
using touchstone::testing::GoldenCase;
using touchstone::testing::Standardised;
using touchstone::testing::standardise;
using touchstone::testing::stream_seed;

constexpr std::size_t grid_stride = TOUCHSTONE_SWEEP_SCALE;

/// Paths per row on the grid sweep. Enough that the estimator is close to
/// normal on the rows the sweep tests, and cheap enough to run on every row.
constexpr std::size_t grid_paths = 32768;

/// Paths for the second look at a row too rarely in the money to standardise at
/// `grid_paths`. Thirty-two times as many, which moves the threshold from about
/// one path in seventy to one in two thousand. Not divided by the sweep scale:
/// the stride already cuts how many rows reach this, and dividing twice would
/// make the comment above it false in the scaled build.
constexpr std::size_t deep_paths = 32 * grid_paths;

/// The number of paths a row must *expect* to finish in the money before its
/// z-score means anything.
///
/// Derived, not chosen. A vanilla's discounted payoff is a mixture: an atom at
/// zero carrying 1 - p, and a positive part above it. Writing X = B Y with B
/// Bernoulli(p), its skewness for small p is about
/// (mu3 / mu2^{3/2}) / sqrt(p), where the first factor belongs to the payoff
/// conditional on finishing in the money — near-exponential in the tail of the
/// grid, so about 6 / 2^{3/2} = 2.12. Cochran's condition for the central limit
/// theorem to have arrived, |skewness| / sqrt(n) below 0.1, is then
/// n p >= (2.12 / 0.1)^2 = 450.
///
/// Below this the estimate is still unbiased and still converges; what it is
/// not is normal, so a standard error is a spread rather than a ruler.
///
/// **Expected, not observed.** The observed count is correlated with the price
/// estimate — the same paths produce both — so admitting a row on the strength
/// of it would be selecting on the statistic under test. Measured on one row
/// with an expected count of exactly 100, over 20,000 independent runs: the
/// mean z of every run is -0.11, and the mean z of the runs that clear an
/// observed cut of 100 is +0.45. The expected count comes from N(w d2), which
/// no path has any say in.
constexpr double clt_expected_in_the_money = 450.0;

/// The four sigma-multiples the batteries assert at. Five, not three: these
/// bounds are the sampling error of the statistic itself, so a real defect
/// arrives at tens of sigma — a standard error understated by a factor of two
/// puts the sample sd at 2.0, which on a grid of seven thousand rows is 120
/// sigma — while a spurious failure at five sigma is a one-in-three-million
/// event on a run that is deterministic anyway. Three would trade none of the
/// power for a real chance of a red run on correct code.
constexpr double sigma_bound = 5.0;

std::vector<const GoldenCase*> grid_rows()
{
    const auto& file = touchstone::testing::golden_file();
    std::vector<const GoldenCase*> rows;
    for (std::size_t i = 0; i < file.cases.size(); i += grid_stride) {
        rows.push_back(&file.cases[i]);
    }
    for (std::size_t i = 0; i < file.edge_cases.size(); i += grid_stride) {
        rows.push_back(&file.edge_cases[i]);
    }
    return rows;
}

/// P(the option finishes in the money) under the risk-neutral measure: N(w d2).
///
/// Transcribed here from `golden/SCHEMA.md` rather than taken from the library,
/// so that the number of paths that landed in the money and the price those
/// paths produce are not checked against the same arithmetic.
double in_the_money_probability(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    const double w = option_sign(option.type);
    const double total_vol = market.vol * std::sqrt(option.expiry_years);

    if (total_vol == 0.0) {
        const double forward =
            market.spot
            * std::exp((market.rate - market.dividend_yield) * option.expiry_years);
        return (w * (forward - option.strike) > 0.0) ? 1.0 : 0.0;
    }

    const double d2 = (std::log(market.spot / option.strike)
                       + (market.rate - market.dividend_yield
                          - 0.5 * market.vol * market.vol)
                             * option.expiry_years)
                      / total_vol;
    return norm_cdf(w * d2);
}

/// Assert that a sample of z-scores is what a correct estimator produces, and
/// report the numbers whether it passes or fails.
void check_standard_normal(const std::vector<double>& z,
                           const std::vector<std::string>& labels,
                           const char* what)
{
    const Standardised summary = standardise(z, labels);
    MESSAGE(summary.report(what));

    const double n = static_cast<double>(summary.count);

    // No row is further out than a sample this size should reach.
    CHECK(summary.worst <= summary.worst_bound);

    // No systematic error: the mean of n standard normals has standard
    // deviation 1/sqrt(n), and this is the assertion a bias has to get past.
    // It is what the sweep is worth more than its rows for — a bias of a tenth
    // of a standard error passes every row's three-sigma test and fails here by
    // eight sigma.
    //
    // What it does not separate is estimator bias from studentisation bias. A
    // studentised mean of a right-skewed payoff has E[z] of about
    // -c / sqrt(n p) even when the estimator itself is exact, so a little of
    // this budget is spent before any defect exists: measured across five
    // disjoint seed families, this grid's mean sits at -0.009 with a spread of
    // 0.006, against a bound of 0.063. That is the price of a cut-off at 450
    // expected paths in the money rather than at four thousand, and it is
    // stated here rather than left for a reader to discover.
    CHECK(std::abs(summary.mean) <= sigma_bound / std::sqrt(n));

    // The standard error is the right size: neither overstated, which would
    // hide a defect, nor understated, which would advertise a precision the
    // estimate does not have. The sample sd of n standard normals has standard
    // deviation 1/sqrt(2n).
    CHECK(std::abs(summary.standard_deviation - 1.0) <= sigma_bound / std::sqrt(2.0 * n));

    // And the three-standard-error rule itself, in the only form a grid can
    // hold it: the right *number* of rows outside, not none.
    CHECK(std::abs(static_cast<double>(summary.beyond_three) - summary.expected_beyond_three)
          <= sigma_bound * std::sqrt(summary.expected_beyond_three) + 1.0);
}

}  // namespace

TEST_SUITE("monte-carlo")
{
    TEST_CASE("settings that cannot be run are refused")
    {
        const EuropeanVanilla option{100.0, 1.0, OptionType::Call};
        const BlackScholesMarket market{100.0, 0.2, 0.03, 0.01};

        MonteCarloSettings settings{};
        settings.paths = 0;
        CHECK_THROWS_AS(touchstone::monte_carlo(option, market, settings), std::invalid_argument);

        settings.paths = 1001;
        settings.antithetic = true;
        CHECK_THROWS_AS(touchstone::monte_carlo(option, market, settings), std::invalid_argument);

        settings.antithetic = false;
        settings.scheme = Scheme::EulerMaruyama;
        settings.steps = 0;
        CHECK_THROWS_AS(touchstone::monte_carlo(option, market, settings), std::invalid_argument);

        // And the option and market are held to the same domain the closed form
        // prices on, so that a comparison between the two is a comparison.
        settings = MonteCarloSettings{};
        const BlackScholesMarket negative_vol{100.0, -0.2, 0.03, 0.01};
        CHECK_THROWS_AS(touchstone::monte_carlo(option, negative_vol, settings),
                        std::invalid_argument);
    }

    TEST_CASE("same seed, same result")
    {
        // Constitution I6. Bit-identical, not close: nothing here is allowed to
        // depend on anything but the seed.
        const EuropeanVanilla option{95.0, 1.5, OptionType::Put};
        const BlackScholesMarket market{100.0, 0.25, 0.02, 0.01};

        for (bool antithetic : {false, true}) {
            for (Scheme scheme : {Scheme::ExactTerminal, Scheme::EulerMaruyama}) {
                MonteCarloSettings settings{};
                settings.seed = 20260829u;
                settings.paths = 4096;
                settings.scheme = scheme;
                settings.steps = 8;
                settings.antithetic = antithetic;

                const MonteCarloResult first = touchstone::monte_carlo(option, market, settings);
                const MonteCarloResult second = touchstone::monte_carlo(option, market, settings);

                CHECK(first.price == second.price);
                CHECK(first.price_standard_error == second.price_standard_error);
                CHECK(first.delta == second.delta);
                CHECK(first.delta_standard_error == second.delta_standard_error);
                CHECK(first.in_the_money == second.in_the_money);
            }
        }
    }

    TEST_CASE("the estimate is the mean of the paths the engine drew")
    {
        // The engine re-implemented naively from the same generator: draw,
        // step, discount, average. It shares no line of code with the engine's
        // accumulator or its pairing, so agreement is a check on the plumbing —
        // a stream consumed at the wrong rate, a discount applied twice, an
        // antithetic partner drawing fresh normals instead of reusing them.
        const EuropeanVanilla option{105.0, 0.75, OptionType::Call};
        const BlackScholesMarket market{100.0, 0.3, 0.04, 0.015};

        for (bool antithetic : {false, true}) {
            for (std::size_t steps : {std::size_t{0}, std::size_t{5}}) {
                MonteCarloSettings settings{};
                settings.seed = 4242u;
                settings.paths = 2048;
                settings.antithetic = antithetic;
                settings.scheme = (steps == 0) ? Scheme::ExactTerminal : Scheme::EulerMaruyama;
                settings.steps = (steps == 0) ? 1 : steps;

                const MonteCarloResult engine = touchstone::monte_carlo(option, market, settings);

                Xoshiro128SS rng(settings.seed);
                const double discount = std::exp(-market.rate * option.expiry_years);
                const std::size_t per_sample = antithetic ? 2u : 1u;
                const std::size_t samples = settings.paths / per_sample;
                const std::size_t draws = (steps == 0) ? 1u : steps;

                double total_price = 0.0;
                double total_delta = 0.0;
                std::size_t hits = 0;
                std::vector<double> normals(draws, 0.0);

                for (std::size_t sample = 0; sample < samples; ++sample) {
                    for (double& z : normals) {
                        z = rng.next_normal();
                    }
                    for (std::size_t side = 0; side < per_sample; ++side) {
                        const double sign = (side == 0) ? 1.0 : -1.0;

                        double terminal = market.spot;
                        if (steps == 0) {
                            terminal = market.spot
                                       * std::exp((market.rate - market.dividend_yield
                                                   - 0.5 * market.vol * market.vol)
                                                      * option.expiry_years
                                                  + market.vol * std::sqrt(option.expiry_years)
                                                        * sign * normals[0]);
                        } else {
                            const double dt =
                                option.expiry_years / static_cast<double>(steps);
                            for (const double z : normals) {
                                terminal *= 1.0
                                            + (market.rate - market.dividend_yield) * dt
                                            + market.vol * std::sqrt(dt) * sign * z;
                            }
                        }

                        const double intrinsic = terminal - option.strike;  // a call
                        total_price += discount * (intrinsic > 0.0 ? intrinsic : 0.0);
                        total_delta +=
                            discount * (intrinsic > 0.0 ? terminal / market.spot : 0.0);
                        if (intrinsic > 0.0) {
                            ++hits;
                        }
                    }
                }

                const double paths = static_cast<double>(settings.paths);
                CAPTURE(antithetic);
                CAPTURE(steps);
                // Not bit-identical: Welford's running mean and a naive sum
                // round differently. Twelve digits is the agreement of two
                // routes to the same arithmetic.
                CHECK(std::abs(engine.price - total_price / paths)
                      <= 1e-12 * std::abs(total_price / paths));
                CHECK(std::abs(engine.delta - total_delta / paths)
                      <= 1e-12 * std::abs(total_delta / paths));
                CHECK(engine.paths == settings.paths);
                CHECK(engine.samples == samples);
                // Counted per path, partners included. Nothing else in the
                // suite pins this under antithetic sampling, and the grid sweep
                // uses it to say where a standard error is worth reading.
                CHECK(engine.in_the_money == hits);
            }
        }
    }

    TEST_CASE("the standard error is the spread of the estimator")
    {
        // The claim a reported standard error makes is falsifiable: run the
        // whole estimate many times from different seeds and its spread should
        // be what the standard error said it would be. This is the test that
        // catches an antithetic standard error computed from paths rather than
        // from pairs — the failure mode where a variance reduction makes the
        // answer look better than it is, which no comparison against a closed
        // form would notice, because the estimate itself stays correct.
        const EuropeanVanilla option{100.0, 1.0, OptionType::Call};
        const BlackScholesMarket market{100.0, 0.3, 0.04, 0.01};
        const double reference = touchstone::price(option, market);

        constexpr std::size_t repetitions = 400;

        for (bool antithetic : {false, true}) {
            std::vector<double> estimates;
            std::vector<double> deltas;
            double reported_price_error = 0.0;
            double reported_delta_error = 0.0;

            for (std::size_t r = 0; r < repetitions; ++r) {
                MonteCarloSettings settings{};
                settings.seed = stream_seed(r);
                settings.paths = 4096;
                settings.antithetic = antithetic;

                const MonteCarloResult result = touchstone::monte_carlo(option, market, settings);
                estimates.push_back(result.price);
                deltas.push_back(result.delta);
                reported_price_error += result.price_standard_error
                                        / static_cast<double>(repetitions);
                reported_delta_error += result.delta_standard_error
                                        / static_cast<double>(repetitions);
            }

            auto spread = [](const std::vector<double>& values) {
                const double n = static_cast<double>(values.size());
                double mean = 0.0;
                for (const double value : values) {
                    mean += value / n;
                }
                double sum_squares = 0.0;
                for (const double value : values) {
                    sum_squares += (value - mean) * (value - mean);
                }
                return std::pair<double, double>{mean, std::sqrt(sum_squares / (n - 1.0))};
            };

            const auto [price_mean, price_spread] = spread(estimates);
            const auto [delta_mean, delta_spread] = spread(deltas);

            std::ostringstream report;
            report << std::fixed << std::setprecision(4);
            report << (antithetic ? "antithetic" : "crude") << ", " << repetitions
                   << " runs of 4096 paths"
                   << "\n    price    mean " << price_mean << " vs closed form " << reference
                   << "\n             observed spread " << price_spread << ", reported SE "
                   << reported_price_error
                   << "\n    delta    observed spread " << delta_spread << ", reported SE "
                   << reported_delta_error;
            MESSAGE(report.str());

            // The estimator is unbiased: the mean of 400 runs is within a few
            // standard errors of that mean.
            const double error_of_mean =
                reported_price_error / std::sqrt(static_cast<double>(repetitions));
            CHECK(std::abs(price_mean - reference) <= sigma_bound * error_of_mean);

            // And the reported standard error is the observed spread. A sample
            // standard deviation from 400 runs is itself uncertain by
            // 1/sqrt(2 * 400) = 3.5% relative, so the bound is five of those,
            // 17.7%. That is a coarse instrument next to the grid battery,
            // whose spread leg pins the standard error to within 5% — this test
            // is here for what the grid cannot see, which is the whole
            // estimator end to end, run four hundred times.
            const double relative_uncertainty =
                sigma_bound / std::sqrt(2.0 * static_cast<double>(repetitions));
            CHECK(std::abs(price_spread / reported_price_error - 1.0) <= relative_uncertainty);
            CHECK(std::abs(delta_spread / reported_delta_error - 1.0) <= relative_uncertainty);
        }
    }

    TEST_CASE("antithetic sampling reduces the variance it is supposed to")
    {
        // A vanilla's payoff is monotone in the terminal spot, so a path and its
        // mirror image are negatively correlated and the pair mean varies less
        // than two independent paths would. That is the claim; here is the
        // measurement, at equal path counts rather than equal sample counts,
        // because paths are what cost.
        const BlackScholesMarket market{100.0, 0.25, 0.03, 0.0};

        std::ostringstream report;
        report << std::fixed << std::setprecision(4) << "standard error at 8192 paths";

        for (const double strike : {80.0, 100.0, 120.0}) {
            const EuropeanVanilla option{strike, 1.0, OptionType::Call};

            MonteCarloSettings crude{};
            crude.seed = 11u;
            crude.paths = 8192;

            MonteCarloSettings paired = crude;
            paired.antithetic = true;

            const MonteCarloResult a = touchstone::monte_carlo(option, market, crude);
            const MonteCarloResult b = touchstone::monte_carlo(option, market, paired);

            report << "\n    K = " << strike << "   crude " << a.price_standard_error
                   << "   antithetic " << b.price_standard_error << "   ratio "
                   << b.price_standard_error / a.price_standard_error;

            CAPTURE(strike);
            CHECK(b.price_standard_error < a.price_standard_error);
        }
        MESSAGE(report.str());
    }

    TEST_CASE("the terminal spot has the law it should")
    {
        // Two moments of the exact sampler, against what the lognormal says
        // they are: E[S_T] = S e^{(r-q)T} is the forward, and the variance is
        // the textbook one. Nothing here goes through a payoff, so a defect in
        // the drift shows up as itself rather than as a price that is a little
        // off.
        const BlackScholesMarket market{100.0, 0.3, 0.05, 0.02};
        constexpr double expiry = 2.0;
        constexpr std::size_t draws = 2000000;

        Xoshiro128SS rng(99u);
        double mean = 0.0;
        double mean_square = 0.0;
        for (std::size_t i = 0; i < draws; ++i) {
            const double terminal =
                touchstone::terminal_spot_exact(market, expiry, rng.next_normal());
            mean += terminal / static_cast<double>(draws);
            mean_square += terminal * terminal / static_cast<double>(draws);
        }

        const double drift = (market.rate - market.dividend_yield) * expiry;
        const double variance_total = market.vol * market.vol * expiry;
        const double forward = market.spot * std::exp(drift);
        const double expected_square =
            market.spot * market.spot * std::exp(2.0 * drift + variance_total);

        // The standard error of the sample mean of a lognormal, exactly.
        const double sample_error =
            forward * std::sqrt(std::expm1(variance_total) / static_cast<double>(draws));

        std::ostringstream moments;
        moments << std::fixed << std::setprecision(4) << "E[S_T] = " << mean << " vs forward "
                << forward << " (SE " << sample_error << "); E[S_T^2] within "
                << std::abs(mean_square / expected_square - 1.0) << " relative";
        MESSAGE(moments.str());
        CHECK(std::abs(mean - forward) <= sigma_bound * sample_error);
        CHECK(std::abs(mean_square / expected_square - 1.0) <= 0.02);

        // z = 0 is the median path, and it is the formula with nothing left of
        // it but the drift.
        CHECK(touchstone::terminal_spot_exact(market, expiry, 0.0)
              == doctest::Approx(market.spot * std::exp(drift - 0.5 * variance_total))
                     .epsilon(1e-15));

        // No volatility, no randomness: every draw lands on the forward.
        const BlackScholesMarket still{100.0, 0.0, 0.05, 0.02};
        CHECK(touchstone::terminal_spot_exact(still, expiry, 3.7)
              == doctest::Approx(forward).epsilon(1e-15));
    }

    TEST_CASE("the payoff and its pathwise derivative are what they claim")
    {
        const EuropeanVanilla call{100.0, 1.0, OptionType::Call};
        const EuropeanVanilla put{100.0, 1.0, OptionType::Put};

        CHECK(touchstone::payoff(call, 120.0) == 20.0);
        CHECK(touchstone::payoff(call, 80.0) == 0.0);
        CHECK(touchstone::payoff(call, 100.0) == 0.0);
        CHECK(touchstone::payoff(put, 80.0) == 20.0);
        CHECK(touchstone::payoff(put, 120.0) == 0.0);

        // A negative terminal spot is Euler's, not the exact sampler's, and the
        // payoff has to be right there too: a call is worthless, a put is worth
        // K minus a negative number.
        CHECK(touchstone::payoff(call, -5.0) == 0.0);
        CHECK(touchstone::payoff(put, -5.0) == 105.0);

        // dS_T/dS is the growth factor, because every path is S times something
        // that does not depend on S; the payoff contributes w where it is in
        // the money and zero where it is not. (S_T = 120 from a spot of 50 is a
        // growth of 2.4.)
        CHECK(touchstone::pathwise_payoff_delta(call, 120.0, 2.4) == doctest::Approx(2.4));
        CHECK(touchstone::pathwise_payoff_delta(call, 80.0, 1.6) == 0.0);
        CHECK(touchstone::pathwise_payoff_delta(put, 80.0, 1.6) == doctest::Approx(-1.6));
        CHECK(touchstone::pathwise_payoff_delta(put, 120.0, 2.4) == 0.0);

        // And the reason it is the growth factor rather than S_T / S. A spot of
        // zero is inside the domain the closed form prices on; every path stays
        // at zero; a put is in the money on all of them and has a delta of
        // -e^{-qT}, which the ratio would return a NaN for.
        const BlackScholesMarket nothing{0.0, 0.2, 0.03, 0.01};
        const double growth = touchstone::terminal_growth_exact(nothing, 1.0, 0.5);
        CHECK(touchstone::terminal_spot_exact(nothing, 1.0, 0.5) == 0.0);
        CHECK(touchstone::pathwise_payoff_delta(put, 0.0, growth) == -growth);

        MonteCarloSettings settings{};
        settings.paths = 8192;
        const MonteCarloResult at_zero = touchstone::monte_carlo(put, nothing, settings);
        const touchstone::PriceAndGreeks closed = touchstone::price_and_greeks(put, nothing);
        CHECK(at_zero.price == doctest::Approx(closed.price).epsilon(1e-12));
        CHECK(std::abs(at_zero.delta - closed.delta)
              <= 5.0 * at_zero.delta_standard_error + 1e-12);
    }

    TEST_CASE("with no volatility or no time there is nothing to estimate")
    {
        // The branch the grid sweep keeps for rows with no randomness in them,
        // which that grid does not contain: its smallest volatility is 0.01 and
        // its shortest expiry is a day. Exercised here instead, so that the
        // sweep's exact-comparison path is not code no run has ever taken.
        const EuropeanVanilla call{95.0, 2.0, OptionType::Call};
        const EuropeanVanilla put{95.0, 2.0, OptionType::Put};
        const EuropeanVanilla expired{95.0, 0.0, OptionType::Call};

        MonteCarloSettings settings{};
        settings.paths = 512;

        for (const EuropeanVanilla& option : {call, put}) {
            const BlackScholesMarket certain{100.0, 0.0, 0.04, 0.01};
            const MonteCarloResult mc = touchstone::monte_carlo(option, certain, settings);
            const touchstone::PriceAndGreeks closed = touchstone::price_and_greeks(option, certain);

            // Every path is the forward, so every sample is the same number and
            // the spread of them is exactly zero — not nearly zero.
            CHECK(mc.price_standard_error == 0.0);
            CHECK(mc.delta_standard_error == 0.0);
            CHECK(mc.price == doctest::Approx(closed.price).epsilon(1e-14));
            CHECK(mc.delta == doctest::Approx(closed.delta).epsilon(1e-14));
            CHECK((mc.in_the_money == 0u || mc.in_the_money == mc.paths));
        }

        // No time either: the option is worth its intrinsic value and nothing
        // is random about that.
        const BlackScholesMarket market{100.0, 0.3, 0.04, 0.01};
        const MonteCarloResult now = touchstone::monte_carlo(expired, market, settings);
        CHECK(now.price == doctest::Approx(5.0).epsilon(1e-14));
        CHECK(now.price_standard_error == 0.0);
        CHECK(now.delta == doctest::Approx(1.0).epsilon(1e-14));
    }

    TEST_CASE("no input the closed form accepts makes the engine return a NaN")
    {
        // T1 made this a promise for the closed form: accepting an input means
        // no output will be a NaN, because a NaN compares false against every
        // tolerance a caller might test it with and so defeats the check that
        // was meant to catch it. The Monte Carlo validates against that same
        // domain, so it inherits the promise — and inheriting a domain is not
        // the same as inheriting the arithmetic. It sums exponentials of
        // normals, which the closed form never does.
        //
        // The sweep is `test_limits.cpp`'s, coarsened: the same corners, few
        // enough paths to run them all. Two things it found, both now fixed and
        // both re-broken to check this notices: a spot of zero made the
        // pathwise delta 0/0, and a terminal spot that overflows made Welford's
        // variance inf * (inf - inf).
        constexpr double spots[] = {0.0, 1e-300, 1e-8, 100.0, 1e8, 1e300, 1.7e308};
        constexpr double strikes[] = {0.0, 1e-300, 1e-8, 100.0, 1e8, 1e300};
        constexpr double vols[] = {0.0, 1e-300, 0.2, 30.0, 1e100};
        constexpr double expiries[] = {0.0, 1e-300, 1.0, 1e6, 1e300};
        constexpr double rates[] = {-0.5, 0.0, 0.05};

        MonteCarloSettings settings{};
        settings.paths = 64;

        std::size_t priced = 0;
        std::size_t rejected = 0;
        std::size_t infinite = 0;

        for (const double spot : spots) {
            for (const double strike : strikes) {
                for (const double vol : vols) {
                    for (const double years : expiries) {
                        for (const double rate : rates) {
                            for (const OptionType type : {OptionType::Call, OptionType::Put}) {
                                const EuropeanVanilla option{strike, years, type};
                                const BlackScholesMarket market{spot, vol, rate, 0.01};

                                MonteCarloResult result{};
                                try {
                                    result = touchstone::monte_carlo(option, market, settings);
                                } catch (const std::invalid_argument&) {
                                    ++rejected;
                                    continue;
                                }
                                ++priced;

                                CAPTURE(spot);
                                CAPTURE(strike);
                                CAPTURE(vol);
                                CAPTURE(years);
                                CAPTURE(rate);
                                REQUIRE_FALSE(std::isnan(result.price));
                                REQUIRE_FALSE(std::isnan(result.price_standard_error));
                                REQUIRE_FALSE(std::isnan(result.delta));
                                REQUIRE_FALSE(std::isnan(result.delta_standard_error));
                                if (!std::isfinite(result.price) || !std::isfinite(result.delta)) {
                                    ++infinite;
                                }
                            }
                        }
                    }
                }
            }
        }

        MESSAGE("domain sweep: " << priced << " priced, " << rejected
                                 << " rejected as unrepresentable, " << infinite
                                 << " saturated at an infinity, none a NaN");
        REQUIRE(priced > 1000u);
    }

    TEST_CASE("the golden grid, priced by Monte Carlo")
    {
        const std::vector<const GoldenCase*> rows = grid_rows();
        REQUIRE_FALSE(rows.empty());

        std::vector<double> price_z;
        std::vector<std::string> price_labels;
        std::vector<double> delta_z;
        std::vector<std::string> delta_labels;
        std::vector<double> hit_z;
        std::vector<std::string> hit_labels;
        std::vector<double> deep_z;
        std::vector<std::string> deep_labels;

        std::size_t deterministic = 0;
        std::size_t unreachable = 0;
        std::size_t empty = 0;
        double unreachable_worst = 0.0;
        std::string unreachable_worst_at;
        double rare_hits = 0.0;
        double rare_expected = 0.0;
        double rare_misses = 0.0;
        double rare_misses_expected = 0.0;

        for (std::size_t index = 0; index < rows.size(); ++index) {
            const GoldenCase& row = *rows[index];

            MonteCarloSettings settings{};
            settings.seed = stream_seed(index);
            settings.paths = grid_paths;

            const MonteCarloResult mc = touchstone::monte_carlo(row.option, row.market, settings);
            const touchstone::PriceAndGreeks closed =
                touchstone::price_and_greeks(row.option, row.market);

            // --- the terminal law's own test, on every row ------------------
            //
            // How many paths finished in the money is a binomial count whose
            // probability the closed form knows: N(w d2). It is the only check
            // that reaches the rows where the price cannot be estimated at all,
            // because a row whose every path expires worthless still has a
            // right number of paths expiring worthless — namely all of them.
            const double p = in_the_money_probability(row.option, row.market);
            const double expected_hits = static_cast<double>(grid_paths) * p;
            const double expected_misses = static_cast<double>(grid_paths) - expected_hits;
            const double hits = static_cast<double>(mc.in_the_money);

            if (expected_hits >= 10.0 && expected_misses >= 10.0) {
                hit_z.push_back((hits - expected_hits) / std::sqrt(expected_hits * (1.0 - p)));
                hit_labels.push_back(describe(row));
            } else if (expected_hits < 10.0) {
                // Too few expected to standardise one row at a time. Summed
                // across rows they are Poisson, and the sum is checked below.
                rare_hits += hits;
                rare_expected += expected_hits;
            } else {
                // The mirror case: almost every path lands in the money, and it
                // is the misses that are rare.
                rare_misses += static_cast<double>(grid_paths) - hits;
                rare_misses_expected += expected_misses;
            }

            // --- the price -------------------------------------------------
            //
            // Which test a row gets is decided by its expected hit count and
            // its volatility, both of which the closed form knows before a
            // single path is drawn. Nothing here looks at what the paths
            // actually did: a row admitted because its own sample came out
            // favourably would be a row chosen by the statistic under test.
            if (row.market.vol * row.market.vol * row.option.expiry_years == 0.0) {
                // No volatility or no time: every path is the same path, and
                // the comparison is exact rather than statistical.
                ++deterministic;
                CAPTURE(describe(row));
                CHECK(mc.price_standard_error == 0.0);
                CHECK(std::abs(mc.price - closed.price)
                      <= 1e-12 * std::max(std::abs(closed.price), 1.0));
                continue;
            }

            if (expected_hits >= clt_expected_in_the_money) {
                REQUIRE(mc.price_standard_error > 0.0);
                price_z.push_back((mc.price - closed.price) / mc.price_standard_error);
                price_labels.push_back(describe(row));

                if (mc.delta_standard_error > 0.0) {
                    delta_z.push_back((mc.delta - closed.delta) / mc.delta_standard_error);
                    delta_labels.push_back(describe(row));
                }
                continue;
            }

            if (expected_hits * static_cast<double>(deep_paths)
                    / static_cast<double>(grid_paths)
                >= clt_expected_in_the_money) {
                // Too rare to be normal at this path count, but not too rare to
                // be normal at all. The answer is more paths, not a looser
                // bound, so the row is run again with thirty-two times as many.
                MonteCarloSettings deeper = settings;
                deeper.paths = deep_paths;
                deeper.seed = stream_seed(index + rows.size());
                const MonteCarloResult again =
                    touchstone::monte_carlo(row.option, row.market, deeper);

                REQUIRE(again.price_standard_error > 0.0);
                deep_z.push_back((again.price - closed.price) / again.price_standard_error);
                deep_labels.push_back(describe(row));
                continue;
            }

            // Below about one path in seventy, at a million paths, Monte Carlo
            // cannot price this row within anything this suite can afford, and
            // the reason is worth naming: the estimate and its error bar
            // collapse together. A handful of sampled payoffs from a heavy
            // right tail produce a small mean *and* a small sample spread, so
            // the z-score is large and means nothing. `golden/SCHEMA.md`
            // already calls this part of the grid numerically dead and keeps it
            // for coverage. What covers it here is the hit-count test: the
            // paths are landing in the money at the rate the closed form says,
            // which is the part of the claim Monte Carlo can still speak to.
            ++unreachable;
            if (mc.in_the_money == 0) {
                ++empty;
                CAPTURE(describe(row));
                CHECK(mc.price == 0.0);
                CHECK(mc.price_standard_error == 0.0);
            } else if (mc.price_standard_error > 0.0) {
                const double z = (mc.price - closed.price) / mc.price_standard_error;
                if (std::abs(z) > unreachable_worst) {
                    unreachable_worst = std::abs(z);
                    unreachable_worst_at = describe(row);
                }
            }
        }

        std::ostringstream census;
        census << std::fixed << std::setprecision(2);
        census << "grid sweep: " << rows.size() << " rows at " << grid_paths << " paths"
               << " (stride " << grid_stride << ")"
               << "\n    " << price_z.size() << " expecting at least "
               << clt_expected_in_the_money << " paths in the money"
               << "\n    " << deep_z.size() << " more once re-run at " << deep_paths << " paths"
               << "\n    " << unreachable << " too rare to price at either count, of which "
               << empty << " saw no path in the money at all and are priced at exactly zero"
               << "\n        worst |z| among the rest, which nothing asserts: "
               << unreachable_worst << " at " << unreachable_worst_at
               << "\n    " << deterministic << " with no randomness at all, compared exactly";
        MESSAGE(census.str());

        REQUIRE(price_z.size() > rows.size() / 2);
        check_standard_normal(price_z, price_labels, "price vs closed form");
        check_standard_normal(delta_z, delta_labels, "pathwise delta vs analytic delta");
        check_standard_normal(hit_z, hit_labels, "paths finishing in the money vs N(w d2)");
        if (deep_z.size() > 30) {
            check_standard_normal(deep_z, deep_labels, "rare rows re-run with more paths");
        } else {
            MESSAGE("rare rows re-run with more paths: " << deep_z.size()
                                                         << " rows, too few to standardise");
        }

        // The rare rows, summed: independent Poisson counts add to a Poisson
        // count, so the total has standard deviation the square root of its
        // mean. Both tails, because a row where every path lands in the money
        // is as much a claim as a row where none does.
        std::ostringstream tails;
        tails << std::fixed << std::setprecision(1) << "the tails of the grid, summed"
              << "\n    in the money on rows too rare to standardise: " << rare_hits
              << " against " << rare_expected << " expected (+/- " << std::sqrt(rare_expected)
              << ")"
              << "\n    out of the money on rows where that is the rare event: " << rare_misses
              << " against " << rare_misses_expected << " expected (+/- "
              << std::sqrt(rare_misses_expected) << ")";
        MESSAGE(tails.str());
        CHECK(std::abs(rare_hits - rare_expected)
              <= sigma_bound * std::sqrt(rare_expected) + 1.0);
        CHECK(std::abs(rare_misses - rare_misses_expected)
              <= sigma_bound * std::sqrt(rare_misses_expected) + 1.0);
    }

    TEST_CASE("the golden grid again, with antithetic sampling")
    {
        // The same grid through the other estimator, at a quarter of the rows.
        // Everything the sweep above asserts has to hold for this one too, and
        // one thing more: pairing changes what a sample is, so a standard error
        // computed from the wrong unit would show up here as a sample standard
        // deviation of z that is not one.
        const auto& file = touchstone::testing::golden_file();
        std::vector<double> z;
        std::vector<std::string> labels;
        std::size_t visited = 0;

        for (std::size_t index = 0; index < file.cases.size(); index += 4 * grid_stride) {
            ++visited;
            const GoldenCase& row = file.cases[index];

            MonteCarloSettings settings{};
            settings.seed = stream_seed(index + 3u);
            settings.paths = grid_paths;
            settings.antithetic = true;

            if (static_cast<double>(grid_paths) * in_the_money_probability(row.option, row.market)
                < clt_expected_in_the_money) {
                continue;
            }
            const MonteCarloResult mc = touchstone::monte_carlo(row.option, row.market, settings);
            REQUIRE(mc.price_standard_error > 0.0);
            z.push_back((mc.price - touchstone::price(row.option, row.market))
                        / mc.price_standard_error);
            labels.push_back(describe(row));
        }

        REQUIRE(z.size() >= 30u);
        REQUIRE(2u * z.size() >= visited);  // most of what was visited was usable
        check_standard_normal(z, labels, "antithetic price vs closed form");
    }
}
