#include <touchstone/monte_carlo.hpp>

#include <touchstone/rng.hpp>
#include <touchstone/scales.hpp>

#include <cmath>
#include <limits>
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
        if (!std::isfinite(x)) {
            // A payoff that overflowed a double. Left to Welford, the next two
            // lines would turn it into a NaN — `inf * (inf - inf)` — and a NaN
            // compares false against every tolerance a caller might test it
            // with, which is the failure mode T1 ruled out for the closed form.
            // The infinity is kept instead and reported as both the mean and an
            // infinite standard error: saturated, and comparing correctly.
            //
            // Whichever arrived last. Two infinities of opposite signs can
            // reach the same accumulator — under Euler a step's factor goes
            // negative whenever its normal is far enough below zero, so a
            // path's growth factor can be negative and a put's pathwise delta
            // positive — and adding them would give back the NaN this exists to
            // prevent. The caller's signal is the infinite standard error
            // beside it; the sign of a saturated estimate is not a number to
            // read anything into.
            overflowed_ = x;
            return;
        }
        const double delta = x - mean_;
        mean_ += delta / static_cast<double>(count_);
        m2_ += delta * (x - mean_);
    }

    [[nodiscard]] std::size_t count() const noexcept { return count_; }

    [[nodiscard]] double mean() const noexcept
    {
        return (overflowed_ == 0.0) ? mean_ : overflowed_;
    }

    /// The standard error of the mean: `s / sqrt(n)` with `s` the sample
    /// standard deviation on `n - 1` degrees of freedom. Zero for a single
    /// sample, where nothing about the spread is known — an honest zero, and
    /// the reason `MonteCarloResult::in_the_money` is reported beside it.
    [[nodiscard]] double standard_error() const noexcept
    {
        if (overflowed_ != 0.0) {
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
    double overflowed_{0.0};  ///< The first non-finite sample seen, if any.
};

/// One path's growth factor, and the same factor discounted.
///
/// Both, because the two are not reliably one multiplication apart. A terminal
/// spot far enough into the right tail overflows a double while its discount
/// factor underflows to zero, and `0 * inf` is a NaN — which would be the worst
/// of the three possible answers, since a NaN compares false against every
/// tolerance a caller might test it with.
struct PathGrowth {
    double growth{};             ///< S_T / S.
    double discounted_growth{};  ///< e^{-rT} S_T / S.
};

/// Euler-Maruyama's growth factors with every normal multiplied by `sign`. The
/// antithetic partner is the same path with `sign = -1`, which is why this
/// exists rather than a second buffer holding the negated draws.
///
/// The discounted factor is accumulated alongside rather than applied at the
/// end: starting the product at `e^{-rT}` keeps every partial product on the
/// scale it will finish at.
[[nodiscard]] PathGrowth euler_growth(const BlackScholesMarket& market,
                                      double expiry_years,
                                      std::span<const double> normals,
                                      double sign,
                                      double discount) noexcept
{
    PathGrowth result{1.0, discount};

    const std::size_t steps = normals.size();
    if (steps == 0) {
        return result;
    }

    const double dt = expiry_years / static_cast<double>(steps);
    const double drift = (market.rate - market.dividend_yield) * dt;
    const double diffusion = market.vol * std::sqrt(dt);

    for (const double z : normals) {
        const double factor = 1.0 + drift + diffusion * sign * z;
        result.growth *= factor;
        result.discounted_growth *= factor;
    }
    return result;
}

/// The exact scheme's two factors. The discounted one costs a second `exp` only
/// where the single multiplication would not have been finite, which on the
/// golden grid is never.
[[nodiscard]] PathGrowth exact_growth(const BlackScholesMarket& market,
                                      double expiry_years,
                                      double z,
                                      double discount) noexcept
{
    PathGrowth result{};
    result.growth = terminal_growth_exact(market, expiry_years, z);
    result.discounted_growth = result.growth * discount;
    if (!std::isfinite(result.discounted_growth)) {
        result.discounted_growth = discounted_growth_exact(market, expiry_years, z);
    }
    return result;
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

/// sigma sqrt(T), the total volatility to expiry.
///
/// One line, forwarding to `touchstone/scales.hpp`, because the association
/// matters and belongs in one place: the volatility is scaled by the square root
/// of the time rather than the variance by the time, which is how
/// `black_scholes.cpp` forms it, and two routes to the same quantity that round
/// differently are two quantities. It also has more room — `sigma^2 T` overflows
/// for a volatility above 1.3e154 however short the expiry, where
/// `(sigma sqrt(T))^2` does not. T3 moved the expression itself into
/// `scales.hpp`; this signature stays because the callers below read better
/// with it.
[[nodiscard]] double total_volatility(const BlackScholesMarket& market, double expiry_years) noexcept
{
    return detail::total_volatility(market.vol, expiry_years);
}

double terminal_growth_exact(const BlackScholesMarket& market,
                             double expiry_years,
                             double z) noexcept
{
    const double total_vol = total_volatility(market, expiry_years);
    const double variance = total_vol * total_vol;
    const double drift = (market.rate - market.dividend_yield) * expiry_years - 0.5 * variance;
    return std::exp(drift + total_vol * z);
}

double terminal_growth_euler(const BlackScholesMarket& market,
                             double expiry_years,
                             std::span<const double> normals) noexcept
{
    return euler_growth(market, expiry_years, normals, 1.0, 1.0).growth;
}

double discounted_growth_exact(const BlackScholesMarket& market,
                               double expiry_years,
                               double z) noexcept
{
    // e^{-rT} times the growth factor, with the r cancelling inside the
    // exponent: exp(-qT - sigma^2 T / 2 + sigma sqrt(T) z).
    const double total_vol = total_volatility(market, expiry_years);
    const double variance = total_vol * total_vol;
    const double drift = -market.dividend_yield * expiry_years - 0.5 * variance;
    return std::exp(drift + total_vol * z);
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

double payoff(const EuropeanVanilla& option, double terminal_spot) noexcept
{
    const double intrinsic = option_sign(option.type) * (terminal_spot - option.strike);
    return intrinsic > 0.0 ? intrinsic : 0.0;
}

double pathwise_payoff_delta(const EuropeanVanilla& option,
                             double terminal_spot,
                             double growth) noexcept
{
    const double w = option_sign(option.type);
    if (w * (terminal_spot - option.strike) <= 0.0) {
        return 0.0;
    }
    return w * growth;
}

MonteCarloResult monte_carlo(const EuropeanVanilla& option,
                             const BlackScholesMarket& market,
                             const MonteCarloSettings& settings)
{
    require_valid(option, market);
    require_valid(settings);

    // One condition beyond the closed form's, and it is the closed form's own
    // arithmetic that makes it necessary rather than any sloppiness here: the
    // total variance must be representable. `require_valid` guards
    // `0.5 * sigma * sigma`, which C++ groups as `(0.5 sigma) sigma` and which
    // therefore survives a volatility that `sigma sqrt(T)` squared does not, by
    // a factor of the square root of two. Between those two bounds every path
    // would be `exp(-inf + inf)`, which is a NaN, and one NaN in a mean is a
    // NaN out. Rejected rather than returned, for T1's reason: a NaN compares
    // false against every tolerance a caller might test it with.
    const double total_vol = total_volatility(market, option.expiry_years);
    if (!std::isfinite(total_vol * total_vol)) {
        throw std::invalid_argument(
            "monte carlo: the total variance sigma^2 T is not representable, so a path cannot be "
            "drawn; the closed form prices this input and this does not");
    }

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
        double price_overflow = 0.0;
        double delta_overflow = 0.0;

        for (std::size_t path = 0; path < paths_per_sample; ++path) {
            const double sign = (path == 0) ? 1.0 : -1.0;

            const PathGrowth path_growth =
                (settings.scheme == Scheme::ExactTerminal)
                    ? exact_growth(market, expiry, sign * normals[0], discount)
                    : euler_growth(market, expiry, normals, sign, discount);
            const double terminal = terminal_spot(market, path_growth.growth);

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
                // w (S e^{-rT} S_T/S - K e^{-rT}), whose second term
                // `require_valid` has already guaranteed is representable.
                discounted_payoff =
                    option_sign(option.type)
                    * (terminal_spot(market, path_growth.discounted_growth)
                       - option.strike * discount);
            }

            // The discounted growth factor goes in where the raw one would, so
            // the discounted derivative is one multiplication rather than two —
            // and never the one multiplication that is `0 * inf`.
            const double discounted_delta =
                pathwise_payoff_delta(option, terminal, path_growth.discounted_growth);

            // A path whose contribution is not finite is held aside rather than
            // added. Adding is where the two halves of an antithetic pair could
            // be an infinity each, of opposite signs, and their sum a NaN — the
            // one case the accumulator's own guard is too late to see.
            if (std::isfinite(discounted_payoff)) {
                price_sum += discounted_payoff;
            } else if (price_overflow == 0.0) {
                price_overflow = discounted_payoff;
            }
            if (std::isfinite(discounted_delta)) {
                delta_sum += discounted_delta;
            } else if (delta_overflow == 0.0) {
                delta_overflow = discounted_delta;
            }
        }

        // The sample is the pair, not the path. Averaging here and accumulating
        // once is what makes the standard error below the standard error of the
        // estimator that is actually being reported.
        const double per_path = static_cast<double>(paths_per_sample);
        price_of_sample.add(price_overflow != 0.0 ? price_overflow : price_sum / per_path);
        delta_of_sample.add(delta_overflow != 0.0 ? delta_overflow : delta_sum / per_path);
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
