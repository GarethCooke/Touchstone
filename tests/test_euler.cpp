// Euler-Maruyama's error, and the rate it shrinks at.
//
// The exact sampler has no discretisation error, so pointing the two schemes at
// the same Brownian path isolates Euler's mistake exactly: the difference
// between them *is* the error, with no sampling noise standing in front of it.
// That is what makes a rate measurable here rather than merely plausible.
//
// Two rates, because there are two errors and they are not the same number.
// Path by path, Euler is wrong by O(sqrt(dt)) — it drops Milstein's
// (sigma^2/2)(Z^2 - 1) dt term, whose omissions accumulate like a random walk
// over T/dt steps. In expectation, those omissions are mean-zero and cancel,
// and what survives in a price is O(dt). A suite that measured only one of them
// would pass on an implementation that had the other badly wrong, and the
// tutorial's D4 shows the path picture while its D6 uses the price, so both
// claims are made on the site and both have to be tested here (I1).

#include <touchstone/black_scholes.hpp>
#include <touchstone/monte_carlo.hpp>
#include <touchstone/rng.hpp>

#include <doctest/doctest.h>

// See `CMakeLists.txt`, where the option is declared: one by default, higher in
// CI's sanitizer job, where the point is to walk every line rather than to
// measure a rate precisely.
#ifndef TOUCHSTONE_SWEEP_SCALE
#define TOUCHSTONE_SWEEP_SCALE 1
#endif

#include <cmath>
#include <cstddef>
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>

namespace {

using touchstone::BlackScholesMarket;
using touchstone::EuropeanVanilla;
using touchstone::MonteCarloResult;
using touchstone::MonteCarloSettings;
using touchstone::OptionType;
using touchstone::Scheme;
using touchstone::Xoshiro128SS;

/// A straight-line fit of log(error) against log(dt). The slope is the order of
/// convergence; the residual says whether a straight line was the right shape.
struct Fit {
    double slope{};
    double intercept{};
    double worst_residual{};
    double slope_error{};   ///< Set only when the points carry standard errors.
    double worst_scatter{}; ///< Largest relative standard error among the points.
};

Fit fit_log_log(const std::vector<double>& dt, const std::vector<double>& error)
{
    const double n = static_cast<double>(dt.size());
    double mean_x = 0.0;
    double mean_y = 0.0;
    for (std::size_t i = 0; i < dt.size(); ++i) {
        mean_x += std::log(dt[i]) / n;
        mean_y += std::log(error[i]) / n;
    }

    double covariance = 0.0;
    double variance = 0.0;
    for (std::size_t i = 0; i < dt.size(); ++i) {
        const double dx = std::log(dt[i]) - mean_x;
        covariance += dx * (std::log(error[i]) - mean_y);
        variance += dx * dx;
    }

    Fit fit{};
    fit.slope = covariance / variance;
    fit.intercept = mean_y - fit.slope * mean_x;
    for (std::size_t i = 0; i < dt.size(); ++i) {
        const double predicted = fit.intercept + fit.slope * std::log(dt[i]);
        fit.worst_residual =
            std::max(fit.worst_residual, std::abs(std::log(error[i]) - predicted));
    }
    return fit;
}

/// The same fit, with the standard error each point carries propagated into the
/// slope. A measured rate is worth a tolerance only if the measurement's own
/// uncertainty is known: `d log(bias) = d(bias) / bias`, and an ordinary least
/// squares slope is a fixed linear combination of the y values, so its variance
/// is the same combination of theirs.
Fit fit_log_log_with_errors(const std::vector<double>& dt,
                            const std::vector<double>& value,
                            const std::vector<double>& value_error)
{
    Fit fit = fit_log_log(dt, value);

    const double n = static_cast<double>(dt.size());
    double mean_x = 0.0;
    for (const double step : dt) {
        mean_x += std::log(step) / n;
    }
    double variance_x = 0.0;
    for (const double step : dt) {
        const double dx = std::log(step) - mean_x;
        variance_x += dx * dx;
    }

    double variance_slope = 0.0;
    for (std::size_t i = 0; i < dt.size(); ++i) {
        const double dx = std::log(dt[i]) - mean_x;
        const double sigma_y = value_error[i] / value[i];
        variance_slope += (dx * sigma_y) * (dx * sigma_y);
        fit.worst_scatter = std::max(fit.worst_scatter, sigma_y);
    }
    fit.slope_error = std::sqrt(variance_slope) / variance_x;
    return fit;
}

const BlackScholesMarket market{100.0, 0.3, 0.05, 0.02};
constexpr double expiry = 1.0;

constexpr std::size_t sweep_scale = TOUCHSTONE_SWEEP_SCALE;
constexpr bool full_sweep = (sweep_scale == 1);

}  // namespace

TEST_SUITE("euler")
{
    TEST_CASE("path by path, Euler's error shrinks as the square root of dt")
    {
        constexpr std::size_t paths = 20000 / sweep_scale;
        const std::vector<std::size_t> levels{1, 2, 4, 8, 16, 32, 64, 128, 256};

        // A convergence rate is a statement about small dt, so the fit is taken
        // over the small end and the coarse levels are reported rather than
        // fitted. They are not noise — at half a year a step, Euler is simply
        // not approximating anything yet, and the successive ratios below show
        // where it starts to: they climb toward sqrt(2) and settle.
        constexpr double asymptotic_below = 0.13;

        std::vector<double> dt;
        std::vector<double> error;
        std::vector<double> error_of_error;
        std::ostringstream table;
        table << "strong error: mean |S_T Euler - S_T exact| on shared Brownian paths"
              << "\n    steps        dt      mean error        SE     ratio   fitted";

        double previous = 0.0;
        for (const std::size_t steps : levels) {
            Xoshiro128SS rng(4000u + static_cast<std::uint32_t>(steps));
            std::vector<double> normals(steps, 0.0);

            double mean = 0.0;
            double m2 = 0.0;
            std::size_t seen = 0;

            for (std::size_t path = 0; path < paths; ++path) {
                double sum = 0.0;
                for (double& z : normals) {
                    z = rng.next_normal();
                    sum += z;
                }
                // The same Brownian increment, given to both schemes: the exact
                // sampler needs W_T / sqrt(T), which is the sum of the steps'
                // normals divided by the square root of their number.
                const double shared = sum / std::sqrt(static_cast<double>(steps));

                const double stepped = touchstone::terminal_spot_euler(market, expiry, normals);
                const double exact = touchstone::terminal_spot_exact(market, expiry, shared);
                const double gap = std::abs(stepped - exact);

                ++seen;
                const double delta = gap - mean;
                mean += delta / static_cast<double>(seen);
                m2 += delta * (gap - mean);
            }

            const double n = static_cast<double>(seen);
            const double standard_error = std::sqrt(m2 / (n - 1.0) / n);
            const double step = expiry / static_cast<double>(steps);
            const bool fitted = step < asymptotic_below;

            table << "\n    " << std::setw(5) << steps << std::fixed << std::setprecision(6)
                  << std::setw(11) << step << std::setw(14) << std::setprecision(6) << mean
                  << std::setw(11) << std::setprecision(6) << standard_error;
            if (previous > 0.0) {
                table << std::setw(10) << std::setprecision(3) << previous / mean;
            } else {
                table << std::setw(10) << "-";
            }
            table << std::setw(9) << (fitted ? "yes" : "no");
            previous = mean;

            if (fitted) {
                dt.push_back(step);
                error.push_back(mean);
                error_of_error.push_back(standard_error);
            }
        }

        const Fit fit = fit_log_log_with_errors(dt, error, error_of_error);
        table << "\n    slope over dt < " << std::fixed << std::setprecision(2)
              << asymptotic_below << ": " << std::setprecision(4) << fit.slope << " +/- "
              << fit.slope_error << " (0.5 expected), worst residual " << fit.worst_residual;
        MESSAGE(table.str());

        // Euler-Maruyama is strong order one half on multiplicative noise. Half,
        // not one: the term it drops is (sigma^2/2)(Z^2 - 1) S dt per step, mean
        // zero, so over T/dt steps the omissions add like a random walk to
        // sqrt(T/dt) * dt = sqrt(T dt). Milstein's correction is exactly that
        // term, and adding it would make this slope 1 — which is the honest way
        // to say what the scheme is missing.
        //
        // The bound is the fit's own uncertainty five times over, widened by
        // 0.02 for the curvature dt = 1/8 still carries.
        CHECK(std::abs(fit.slope - 0.5) <= 5.0 * fit.slope_error + 0.02);

        // And a straight line was the right shape: no point sits further off it
        // than its own noise, five times over, plus the 0.01 of curvature that
        // dt = 1/8 still carries.
        CHECK(fit.worst_residual <= 5.0 * fit.worst_scatter + 0.01);
    }

    TEST_CASE("in a price, Euler's error shrinks as dt itself")
    {
        // The same paths again, through a payoff and a discount factor. The two
        // estimates share every normal, so their difference carries a fraction
        // of the noise either of them has alone and the bias is visible at path
        // counts a direct comparison would need thousands of times more of.
        //
        // Even so, this is the expensive measurement, and the reason is in the
        // two rates being tested: the bias falls like dt while the noise on it
        // falls only like sqrt(dt), so resolving the bias at half the step size
        // costs twice the paths on twice the steps. That is what fixes the
        // sweep's fine end at dt = 1/64.
        //
        // Its coarse end is reported and not fitted, for the same reason as in
        // the strong test and more visibly: bias/dt below is 0.07 at half a
        // year a step and climbs to about a third, which is the constant the
        // first-order term has. A fit taken across the whole range would
        // measure that climb and return a slope near a half, and the mistake
        // would be the fit's rather than the scheme's.
        constexpr std::size_t paths = 1000000 / sweep_scale;
        const std::vector<std::size_t> levels{2, 4, 8, 16, 32, 64};
        constexpr double asymptotic_below = 0.13;
        const EuropeanVanilla option{100.0, expiry, OptionType::Call};
        const double discount = std::exp(-market.rate * expiry);
        const double reference = touchstone::price(option, market);

        std::vector<double> dt;
        std::vector<double> bias;
        std::vector<double> bias_error;
        std::ostringstream table;
        table << "weak error: E[discounted payoff, Euler] - E[same, exact], common random numbers"
              << "\n    closed form " << std::fixed << std::setprecision(6) << reference
              << "\n    steps        dt          bias         SE   bias/SE   bias/dt";

        for (const std::size_t steps : levels) {
            Xoshiro128SS rng(7000u + static_cast<std::uint32_t>(steps));
            std::vector<double> normals(steps, 0.0);

            double mean = 0.0;
            double m2 = 0.0;
            std::size_t seen = 0;

            for (std::size_t path = 0; path < paths; ++path) {
                double sum = 0.0;
                for (double& z : normals) {
                    z = rng.next_normal();
                    sum += z;
                }
                const double shared = sum / std::sqrt(static_cast<double>(steps));

                const double stepped = touchstone::terminal_spot_euler(market, expiry, normals);
                const double exact = touchstone::terminal_spot_exact(market, expiry, shared);
                const double difference =
                    discount
                    * (touchstone::payoff(option, stepped) - touchstone::payoff(option, exact));

                ++seen;
                const double delta = difference - mean;
                mean += delta / static_cast<double>(seen);
                m2 += delta * (difference - mean);
            }

            const double n = static_cast<double>(seen);
            const double standard_error = std::sqrt(m2 / (n - 1.0) / n);
            const double step = expiry / static_cast<double>(steps);

            dt.push_back(step);
            bias.push_back(std::abs(mean));
            bias_error.push_back(standard_error);

            table << "\n    " << std::setw(5) << steps << std::fixed << std::setprecision(6)
                  << std::setw(11) << step << std::setw(13) << mean << std::setw(11)
                  << standard_error << std::setw(10) << std::setprecision(1)
                  << std::abs(mean) / standard_error << std::setw(10) << std::setprecision(4)
                  << std::abs(mean) / step;

            // Every level's bias is resolved: what is being fitted is a
            // measurement, not noise. This is the one assertion in the suite
            // that a reduced sweep cannot make — the bias falls like dt while
            // the noise on it falls only like sqrt(dt), so resolution is bought
            // with paths and nothing else. At reduced scale it stands aside and
            // says so; the slope check below stays, on a bound that widens with
            // the measurement's own uncertainty.
            CAPTURE(steps);
            if (full_sweep) {
                CHECK(std::abs(mean) > 6.0 * standard_error);
            }
        }

        // The fit, over the levels where bias/dt has settled.
        std::vector<double> fine_dt;
        std::vector<double> fine_bias;
        std::vector<double> fine_error;
        for (std::size_t i = 0; i < dt.size(); ++i) {
            if (dt[i] < asymptotic_below) {
                fine_dt.push_back(dt[i]);
                fine_bias.push_back(bias[i]);
                fine_error.push_back(bias_error[i]);
            }
        }
        REQUIRE(fine_dt.size() >= 3u);

        const Fit fit = fit_log_log_with_errors(fine_dt, fine_bias, fine_error);
        table << "\n    slope over dt < " << std::fixed << std::setprecision(2)
              << asymptotic_below << ": " << std::setprecision(4) << fit.slope << " +/- "
              << fit.slope_error << " (1.0 expected)";
        if (!full_sweep) {
            table << "\n    reduced sweep (scale " << sweep_scale
                  << "): the bias is not resolved and is not asserted to be";
        }
        MESSAGE(table.str());

        // The bound is the measurement's own uncertainty, five times over,
        // widened by 0.05 for the curvature that remains at dt = 1/8: the bias
        // is C dt + O(dt^2), and the second term is still worth about that much
        // of slope at the coarse end of what is fitted.
        CHECK(std::abs(fit.slope - 1.0) <= 5.0 * fit.slope_error + 0.05);
    }

    TEST_CASE("with enough steps, the Euler price is the closed form")
    {
        // The practical statement the demo makes, made once with the engine
        // rather than with the pieces: at 512 steps the discretisation error is
        // small next to the sampling error, and the estimate lands where the
        // closed form is.
        const EuropeanVanilla option{100.0, expiry, OptionType::Call};
        const double reference = touchstone::price(option, market);

        MonteCarloSettings settings{};
        settings.seed = 555u;
        settings.paths = 400000 / sweep_scale;
        settings.scheme = Scheme::EulerMaruyama;
        settings.steps = 512;
        settings.antithetic = true;

        const MonteCarloResult result = touchstone::monte_carlo(option, market, settings);

        // The bias left at 512 steps, from the fit above: about 0.0009 on a
        // price of 13.3, against a standard error of about 0.02. It is inside
        // the noise, which is the point, and the bound below has room for both.
        std::ostringstream report;
        report << std::fixed << std::setprecision(5) << "Euler at 512 steps: " << result.price
               << " +/- " << result.price_standard_error << " against closed form " << reference;
        MESSAGE(report.str());

        CHECK(std::abs(result.price - reference) <= 4.0 * result.price_standard_error);
    }

    TEST_CASE("with no volatility, Euler is compound interest")
    {
        // A step multiplies by 1 + (r - q) dt, so n steps multiply by
        // (1 + (r - q) T / n)^n — the discrete compounding that tends to the
        // exact sampler's e^{(r-q)T} from below. The gap is the whole of the
        // discretisation error when there is no diffusion to hide it, and it
        // halves as the steps double.
        const BlackScholesMarket still{100.0, 0.0, 0.05, 0.02};
        const double continuous =
            touchstone::terminal_spot_exact(still, expiry, 0.0);  // 100 e^{0.03}

        double previous_gap = 0.0;
        for (const std::size_t steps : {1u, 2u, 4u, 8u, 16u, 32u}) {
            const std::vector<double> normals(steps, 12.5);  // ignored: vol is zero
            const double stepped = touchstone::terminal_spot_euler(still, expiry, normals);
            const double expected =
                still.spot
                * std::pow(1.0 + 0.03 * expiry / static_cast<double>(steps),
                           static_cast<double>(steps));

            CAPTURE(steps);
            CHECK(stepped == doctest::Approx(expected).epsilon(1e-14));
            CHECK(stepped < continuous);

            const double gap = continuous - stepped;
            if (previous_gap > 0.0) {
                // Halving, to the accuracy a first-order statement has.
                CHECK(previous_gap / gap == doctest::Approx(2.0).epsilon(0.02));
            }
            previous_gap = gap;
        }
    }
}
