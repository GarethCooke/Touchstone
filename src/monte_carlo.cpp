#include <touchstone/monte_carlo.hpp>

#include <touchstone/rng.hpp>

#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

namespace touchstone {
namespace {

/// Welford's running mean and second moment.
///
/// The textbook alternative — accumulate the sum and the sum of squares, then
/// subtract — loses the variance to cancellation exactly where it is wanted:
/// a deep in-the-money option's payoffs are large numbers with a small spread,
/// and `E[X^2] - E[X]^2` between two numbers agreeing in twelve digits returns
/// noise, sometimes negative. This form never subtracts two large numbers.
class Accumulator {
public:
    void add(double x) noexcept
    {
        ++count_;
        const double delta = x - mean_;
        mean_ += delta / static_cast<double>(count_);
        m2_ += delta * (x - mean_);
    }

    [[nodiscard]] std::size_t count() const noexcept { return count_; }
    [[nodiscard]] double mean() const noexcept { return mean_; }

    /// The standard error of the mean: `s / sqrt(n)` with `s` the sample
    /// standard deviation on `n - 1` degrees of freedom. Zero for a single
    /// sample, where nothing about the spread is known — an honest zero, and
    /// the reason `MonteCarloResult::in_the_money` is reported beside it.
    [[nodiscard]] double standard_error() const noexcept
    {
        if (count_ < 2) {
            return 0.0;
        }
        const double n = static_cast<double>(count_);
        return std::sqrt(m2_ / (n - 1.0) / n);
    }

private:
    std::size_t count_{0};
    double mean_{0.0};
    double m2_{0.0};
};

/// Euler-Maruyama with every normal multiplied by `sign`. The antithetic
/// partner is the same path with `sign = -1`, which is why this exists rather
/// than a second buffer holding the negated draws.
[[nodiscard]] double euler_terminal(const BlackScholesMarket& market,
                                    double expiry_years,
                                    std::span<const double> normals,
                                    double sign) noexcept
{
    const std::size_t steps = normals.size();
    if (steps == 0) {
        return market.spot;
    }

    const double dt = expiry_years / static_cast<double>(steps);
    const double drift = (market.rate - market.dividend_yield) * dt;
    const double diffusion = market.vol * std::sqrt(dt);

    double spot = market.spot;
    for (const double z : normals) {
        spot *= 1.0 + drift + diffusion * sign * z;
    }
    return spot;
}

}  // namespace

void require_valid(const MonteCarloSettings& settings)
{
    if (settings.paths == 0) {
        throw std::invalid_argument("monte carlo: paths must be at least 1");
    }
    if (settings.antithetic && (settings.paths % 2 != 0)) {
        throw std::invalid_argument("monte carlo: antithetic sampling needs an even path count, got "
                                    + std::to_string(settings.paths)
                                    + "; a partner without its path is not a sample");
    }
    if (settings.scheme == Scheme::EulerMaruyama && settings.steps == 0) {
        throw std::invalid_argument("monte carlo: Euler-Maruyama needs at least one step");
    }
}

double terminal_spot_exact(const BlackScholesMarket& market, double expiry_years, double z) noexcept
{
    const double variance = market.vol * market.vol * expiry_years;
    const double drift = (market.rate - market.dividend_yield) * expiry_years - 0.5 * variance;
    return market.spot * std::exp(drift + std::sqrt(variance) * z);
}

double terminal_spot_euler(const BlackScholesMarket& market,
                           double expiry_years,
                           std::span<const double> normals) noexcept
{
    return euler_terminal(market, expiry_years, normals, 1.0);
}

double payoff(const EuropeanVanilla& option, double terminal_spot) noexcept
{
    const double intrinsic = option_sign(option.type) * (terminal_spot - option.strike);
    return intrinsic > 0.0 ? intrinsic : 0.0;
}

double pathwise_payoff_delta(const EuropeanVanilla& option,
                             double spot,
                             double terminal_spot) noexcept
{
    const double w = option_sign(option.type);
    if (w * (terminal_spot - option.strike) <= 0.0) {
        return 0.0;
    }
    return w * terminal_spot / spot;
}

MonteCarloResult monte_carlo(const EuropeanVanilla& option,
                             const BlackScholesMarket& market,
                             const MonteCarloSettings& settings)
{
    require_valid(option, market);
    require_valid(settings);

    const double expiry = option.expiry_years;
    const double discount = std::exp(-market.rate * expiry);

    Xoshiro128SS rng(settings.seed);

    const std::size_t paths_per_sample = settings.antithetic ? 2u : 1u;
    const std::size_t samples = settings.paths / paths_per_sample;
    const std::size_t steps = (settings.scheme == Scheme::EulerMaruyama) ? settings.steps : 1u;

    // One buffer, reused. Under the exact scheme a path is one normal and the
    // buffer holds it; under Euler it holds the whole path, because the
    // antithetic partner needs the same draws again with the sign flipped.
    std::vector<double> normals(steps, 0.0);

    Accumulator price_of_sample;
    Accumulator delta_of_sample;
    std::size_t in_the_money = 0;

    for (std::size_t sample = 0; sample < samples; ++sample) {
        for (double& z : normals) {
            z = rng.next_normal();
        }

        double price_sum = 0.0;
        double delta_sum = 0.0;

        for (std::size_t path = 0; path < paths_per_sample; ++path) {
            const double sign = (path == 0) ? 1.0 : -1.0;

            const double terminal = (settings.scheme == Scheme::ExactTerminal)
                                        ? terminal_spot_exact(market, expiry, sign * normals[0])
                                        : euler_terminal(market, expiry, normals, sign);

            const double path_payoff = payoff(option, terminal);
            if (path_payoff > 0.0) {
                ++in_the_money;
            }

            price_sum += discount * path_payoff;
            delta_sum += discount * pathwise_payoff_delta(option, market.spot, terminal);
        }

        // The sample is the pair, not the path. Averaging here and accumulating
        // once is what makes the standard error below the standard error of the
        // estimator that is actually being reported.
        const double per_path = static_cast<double>(paths_per_sample);
        price_of_sample.add(price_sum / per_path);
        delta_of_sample.add(delta_sum / per_path);
    }

    MonteCarloResult result{};
    result.price = price_of_sample.mean();
    result.price_standard_error = price_of_sample.standard_error();
    result.delta = delta_of_sample.mean();
    result.delta_standard_error = delta_of_sample.standard_error();
    result.paths = samples * paths_per_sample;
    result.samples = price_of_sample.count();
    result.in_the_money = in_the_money;
    return result;
}

}  // namespace touchstone
