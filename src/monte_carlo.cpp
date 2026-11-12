#include <touchstone/monte_carlo.hpp>

#include <touchstone/detail/path_generator.hpp>
#include <touchstone/detail/scales.hpp>

#include <array>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace touchstone {
namespace {

/// A contribution that is not finite, held aside rather than added.
///
/// Adding an infinity is where two of them of opposite signs could meet and
/// make a NaN — the antithetic halves of one sample, or two samples in a run —
/// and a NaN compares false against every tolerance a caller might test it
/// with, which is the failure the closed form rules out too. The first
/// non-finite contribution is kept and reported in place of the total: saturated,
/// and comparing correctly. Its sign is not a number to read anything into —
/// under Euler a step's factor goes negative whenever its normal is far enough
/// below zero, so a path's growth factor can be negative and a put's pathwise
/// delta positive — and the caller's signal is the infinite standard error
/// beside it.
class HeldAside {
public:
    /// True, and `x` held if nothing was already, when `x` is not finite.
    bool holds(double x) noexcept
    {
        if (std::isfinite(x)) {
            return false;
        }
        if (value_ == 0.0) {
            value_ = x;
        }
        return true;
    }

    [[nodiscard]] bool any() const noexcept { return value_ != 0.0; }
    [[nodiscard]] double value() const noexcept { return value_; }

private:
    double value_{0.0};
};

/// Welford's running mean and second moment, over the samples.
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
        // Left to Welford, a payoff that overflowed would become a NaN in the
        // next two lines — `inf * (inf - inf)`.
        if (overflowed_.holds(x)) {
            return;
        }
        const double delta = x - mean_;
        mean_ += delta / static_cast<double>(count_);
        m2_ += delta * (x - mean_);
    }

    [[nodiscard]] std::size_t count() const noexcept { return count_; }

    [[nodiscard]] double mean() const noexcept
    {
        return overflowed_.any() ? overflowed_.value() : mean_;
    }

    /// The standard error of the mean: `s / sqrt(n)` with `s` the sample
    /// standard deviation on `n - 1` degrees of freedom. Zero for a single
    /// sample, where nothing about the spread is known — an honest zero, and
    /// the reason `MonteCarloResult::in_the_money` is reported beside it.
    [[nodiscard]] double standard_error() const noexcept
    {
        if (overflowed_.any()) {
            return std::numeric_limits<double>::infinity();
        }
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
    HeldAside overflowed_;
};

/// One sample's total over its paths — one path, or an antithetic pair — with
/// a contribution that is not finite held aside rather than added.
class SampleTotal {
public:
    void add(double x) noexcept
    {
        if (!overflowed_.holds(x)) {
            sum_ += x;
        }
    }

    /// The sample's value: the mean over its paths, or the contribution that
    /// was held aside.
    [[nodiscard]] double value(double paths) const noexcept
    {
        return overflowed_.any() ? overflowed_.value() : sum_ / paths;
    }

private:
    double sum_{0.0};
    HeldAside overflowed_;
};

/// The risk-neutral step under `scheme`: drift `r - q`, the market's
/// volatility, the expiry in `steps` equal pieces.
[[nodiscard]] detail::GbmStep risk_neutral_step(const BlackScholesMarket& market,
                                                Scheme scheme,
                                                double expiry_years,
                                                std::size_t steps) noexcept
{
    return detail::GbmStep(scheme, detail::carry_rate(market.rate, market.dividend_yield),
                           market.vol, expiry_years / static_cast<double>(steps));
}

/// The exact step of the *discounted* spot over the whole expiry: `e^{-rT}`
/// times the growth factor, with the r cancelling inside the exponent, so that
/// the discounted spot grows at -q.
[[nodiscard]] detail::GbmStep discounted_exact_step(const BlackScholesMarket& market,
                                                    double expiry_years) noexcept
{
    return detail::GbmStep(Scheme::ExactTerminal, -market.dividend_yield, market.vol,
                           expiry_years);
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

double terminal_growth_exact(const BlackScholesMarket& market,
                             double expiry_years,
                             double z) noexcept
{
    return risk_neutral_step(market, Scheme::ExactTerminal, expiry_years, 1).factor(z);
}

double discounted_growth_exact(const BlackScholesMarket& market,
                               double expiry_years,
                               double z) noexcept
{
    return discounted_exact_step(market, expiry_years).factor(z);
}

double terminal_growth_euler(const BlackScholesMarket& market,
                             double expiry_years,
                             std::span<const double> normals) noexcept
{
    if (normals.empty()) {
        return 1.0;
    }
    return detail::grow(
        risk_neutral_step(market, Scheme::EulerMaruyama, expiry_years, normals.size()),
        std::array{1.0}, normals, 1.0)[0];
}

double terminal_spot(const BlackScholesMarket& market, double growth) noexcept
{
    // Zero is an absorbing state: a process that starts at zero stays there,
    // whatever the growth factor. Taken as a case rather than as a
    // multiplication because the one input where the growth factor overflows
    // would otherwise give `0 * inf`, which is a NaN.
    return (market.spot == 0.0) ? 0.0 : market.spot * growth;
}

double terminal_spot_exact(const BlackScholesMarket& market, double expiry_years, double z) noexcept
{
    return terminal_spot(market, terminal_growth_exact(market, expiry_years, z));
}

double terminal_spot_euler(const BlackScholesMarket& market,
                           double expiry_years,
                           std::span<const double> normals) noexcept
{
    return terminal_spot(market, terminal_growth_euler(market, expiry_years, normals));
}

double pathwise_payoff_delta(const EuropeanVanilla& option,
                             double terminal_spot,
                             double growth) noexcept
{
    return payoff(option, terminal_spot) > 0.0 ? option_sign(option.type) * growth : 0.0;
}

MonteCarloResult monte_carlo(const EuropeanVanilla& option,
                             const BlackScholesMarket& market,
                             const MonteCarloSettings& settings)
{
    // The closed form's domain, through its volatility-free half, which also
    // carries the discount factor and the discounted strike this needs.
    const ClosedFormQuote quote(option, QuotedMarket::of(market));
    quote.require_valid(market.vol);
    require_valid(settings);

    const double expiry = option.expiry_years;

    // One condition beyond the closed form's, and it is the closed form's own
    // arithmetic that makes it necessary rather than any sloppiness here: the
    // total variance must be representable. The closed form guards
    // `0.5 * sigma * sigma`, which C++ groups as `(0.5 sigma) sigma` and which
    // therefore survives a volatility that `sigma sqrt(T)` squared does not, by
    // a factor of the square root of two. Between those two bounds every path
    // would be `exp(-inf + inf)`, which is a NaN, and one NaN in a mean is a
    // NaN out. Rejected rather than returned: a NaN compares false against every
    // tolerance a caller might test it with.
    if (!std::isfinite(detail::total_variance(market.vol, expiry))) {
        throw std::invalid_argument(
            "monte carlo: the total variance sigma^2 T is not representable, so a path cannot be "
            "drawn; the closed form prices this input and this does not");
    }

    const double discount = quote.discount_factor();
    const bool exact = (settings.scheme == Scheme::ExactTerminal);

    // A path is one step of the whole expiry under the exact scheme, and
    // `settings.steps` steps under Euler, in growth units: from one, so that the
    // value at the end is the factor the spot grows by, which the pathwise
    // delta needs.
    const std::size_t steps = exact ? 1u : settings.steps;
    detail::PathGenerator generator(settings.seed,
                                    risk_neutral_step(market, settings.scheme, expiry, steps));
    const detail::GbmStep discounted_exact = discounted_exact_step(market, expiry);

    const std::size_t paths_per_sample = settings.antithetic ? 2u : 1u;
    const std::size_t samples = settings.paths / paths_per_sample;

    // One buffer, reused. The antithetic partner needs the same draws again
    // with the sign flipped, so a sample's normals are drawn once and kept.
    std::vector<double> normals(steps, 0.0);

    Accumulator price_of_sample;
    Accumulator delta_of_sample;
    std::size_t in_the_money = 0;

    for (std::size_t sample = 0; sample < samples; ++sample) {
        generator.draw(normals);

        SampleTotal price_total;
        SampleTotal delta_total;

        for (std::size_t path = 0; path < paths_per_sample; ++path) {
            const double sign = (path == 0) ? 1.0 : -1.0;

            // The growth factor, and the same factor discounted. Both, because
            // the two are not reliably one multiplication apart: a terminal spot
            // far enough into the right tail overflows a double while its
            // discount factor underflows to zero, and `0 * inf` is a NaN.
            //
            // Under Euler the discounted factor is grown alongside, in the same
            // walk, from the discount rather than from one, which keeps every
            // partial product on the scale it will finish at. Under the exact
            // scheme it is one multiplication, and a second exponential — the
            // discount taken inside the exponent — only where that
            // multiplication is not finite, which on the golden grid is never.
            double growth = 0.0;
            double discounted_growth = 0.0;
            if (exact) {
                growth = generator.grow(std::array{1.0}, normals, sign)[0];
                discounted_growth = growth * discount;
                if (!std::isfinite(discounted_growth)) {
                    discounted_growth = discounted_exact.factor(sign * normals[0]);
                }
            } else {
                const std::array<double, 2> grown =
                    generator.grow(std::array{1.0, discount}, normals, sign);
                growth = grown[0];
                discounted_growth = grown[1];
            }
            const double terminal = terminal_spot(market, growth);

            const double path_payoff = payoff(option, terminal);
            if (path_payoff > 0.0) {
                ++in_the_money;
            }

            double discounted_payoff = discount * path_payoff;
            if (!std::isfinite(discounted_payoff)) {
                // The payoff overflowed. Not necessarily the discounted payoff:
                // where the discount is small the product is an infinity that
                // had a perfectly good finite value, and where the discount
                // underflowed to zero it is a NaN. Both are recovered the same
                // way, by taking the discount inside:
                // w (S e^{-rT} S_T/S - K e^{-rT}), whose second term the
                // closed form's domain has already guaranteed is representable.
                discounted_payoff =
                    option_sign(option.type)
                    * (terminal_spot(market, discounted_growth) - quote.discounted_strike());
            }

            // The discounted growth factor goes in where the raw one would, so
            // the discounted derivative is one multiplication rather than two —
            // and never the one multiplication that is `0 * inf`.
            price_total.add(discounted_payoff);
            delta_total.add(pathwise_payoff_delta(option, terminal, discounted_growth));
        }

        // The sample is the pair, not the path. Averaging here and accumulating
        // once is what makes the standard error below the standard error of the
        // estimator that is actually being reported.
        const double per_path = static_cast<double>(paths_per_sample);
        price_of_sample.add(price_total.value(per_path));
        delta_of_sample.add(delta_total.value(per_path));
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
