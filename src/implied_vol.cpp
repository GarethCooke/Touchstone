#include <touchstone/implied_vol.hpp>

#include <touchstone/normal.hpp>
#include <touchstone/root_finding.hpp>
#include <touchstone/scales.hpp>

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>

namespace touchstone {
namespace {

/// Brent's own budget, independent of `ImpliedVolSettings::max_iterations`,
/// which is Newton's.
///
/// Bisection alone separates two doubles in `[0, max_vol]` in about sixty
/// halvings, and Brent never does worse than bisection by more than the
/// interpolation steps it interleaves. Two hundred is that with room to spare.
/// It is a constant rather than a setting because a fallback with a budget a
/// caller can exhaust is not a fallback — `require_valid` has already
/// established the bracket, so the root is there to be found.
constexpr std::size_t brent_budget = 200;

/// The price at a given volatility, and its derivative. One call to the closed
/// form gives both, which is the whole reason Newton is the first choice here.
struct PriceAndVega {
    double price{};
    double vega{};
};

[[nodiscard]] PriceAndVega evaluate(const EuropeanVanilla& option,
                                    const QuotedMarket& market,
                                    double vol)
{
    const PriceAndGreeks all = price_and_greeks(option, market.at(vol));
    return PriceAndVega{all.price, all.vega};
}

}  // namespace

double price_scale(const EuropeanVanilla& option, const QuotedMarket& market)
{
    const double years = option.expiry_years;
    return std::max(market.spot * detail::discount_factor(market.dividend_yield, years),
                    option.strike * detail::discount_factor(market.rate, years));
}

namespace {

/// The absolute price tolerance these settings amount to for this option, and
/// the allowance inside which a target below the zero-volatility price is a
/// rounding rather than an arbitrage.
[[nodiscard]] double absolute_tolerance(const EuropeanVanilla& option,
                                        const QuotedMarket& market,
                                        const ImpliedVolSettings& settings)
{
    const double scale = price_scale(option, market);
    // The floor of one ulp of 1.0 keeps a tolerance for an option whose scale
    // has underflowed to zero from being zero itself, which no iteration could
    // ever reach.
    return std::max(settings.price_tolerance * scale, std::numeric_limits<double>::epsilon());
}

}  // namespace

double lowest_price(const EuropeanVanilla& option, const QuotedMarket& market)
{
    // At sigma = 0 the terminal spot is the forward with certainty, so the option
    // is worth the discounted intrinsic value of the forward. Taken from the
    // closed form itself rather than rewritten here: that limit is exact in
    // `black_scholes.cpp`, tested there, and rewriting it would be a second
    // opinion about the same thing.
    return price(option, market.at(0.0));
}

double highest_price(const EuropeanVanilla& option, const QuotedMarket& market)
{
    // As sigma grows, d1 -> +inf and d2 -> -inf, so N(w d1) -> 1 and N(w d2) -> 0
    // for a call and the other way for a put. The call tends to the discounted
    // spot and the put to the discounted strike, from below in both cases.
    const double years = option.expiry_years;
    if (option.type == OptionType::Call) {
        return market.spot * detail::discount_factor(market.dividend_yield, years);
    }
    return option.strike * detail::discount_factor(market.rate, years);
}

void require_valid(const EuropeanVanilla& option,
                   const QuotedMarket& market,
                   double target_price,
                   const ImpliedVolSettings& settings)
{
    if (!(settings.max_vol > 0.0) || !std::isfinite(settings.max_vol)) {
        throw std::invalid_argument("implied vol: max_vol must be finite and positive");
    }
    if (settings.max_iterations == 0) {
        throw std::invalid_argument("implied vol: max_iterations must be at least 1");
    }
    if (!(settings.price_tolerance > 0.0) || !std::isfinite(settings.price_tolerance)) {
        throw std::invalid_argument("implied vol: price_tolerance must be finite and positive");
    }

    // Both ends of the search must be inside the closed form's domain, because
    // both ends will be priced.
    require_valid(option, market.at(0.0));
    require_valid(option, market.at(settings.max_vol));

    if (!std::isfinite(target_price)) {
        throw std::invalid_argument("implied vol: the target price must be finite");
    }

    const double floor_price = lowest_price(option, market);
    const double ceiling_price = highest_price(option, market);

    const double allowance = absolute_tolerance(option, market, settings);
    if (target_price < floor_price - allowance) {
        throw std::invalid_argument(
            "implied vol: the target price " + std::to_string(target_price)
            + " is below the zero-volatility price " + std::to_string(floor_price)
            + "; no volatility produces it, and a quote below it is an arbitrage");
    }
    if (target_price >= ceiling_price) {
        throw std::invalid_argument(
            "implied vol: the target price " + std::to_string(target_price)
            + " is at or above the limit as volatility grows without bound, "
            + std::to_string(ceiling_price) + "; no finite volatility produces it");
    }

    const double at_max = price(option, market.at(settings.max_vol));
    if (target_price > at_max + allowance) {
        throw std::invalid_argument(
            "implied vol: the target price " + std::to_string(target_price)
            + " exceeds the price at max_vol = " + std::to_string(settings.max_vol) + ", which is "
            + std::to_string(at_max)
            + "; the solution is above the search range rather than outside the model");
    }
}

ImpliedVolResult implied_vol(const EuropeanVanilla& option,
                             const QuotedMarket& market,
                             double target_price,
                             const ImpliedVolSettings& settings)
{
    require_valid(option, market, target_price, settings);

    const double years = option.expiry_years;
    const double floor_price = lowest_price(option, market);

    ImpliedVolResult result{};

    const double tolerance = absolute_tolerance(option, market, settings);

    // A target at or below the zero-volatility price has the answer zero, and
    // Newton would divide by a vega of zero to find it. "At or below" rather
    // than "equal to" because `require_valid` has already allowed a target a few
    // ulps under the floor: deep enough in the money the price stops depending
    // on the volatility at all, and every volatility from zero upward returns
    // the same double. The zero is then the honest answer and `vega` is what
    // says so.
    if (target_price <= floor_price) {
        const PriceAndVega at_zero = evaluate(option, market, 0.0);
        result.vol = 0.0;
        result.price_residual = at_zero.price - target_price;
        result.vega = at_zero.vega;
        result.method = ImpliedVolMethod::Exact;
        result.converged = true;
        return result;
    }

    // --- the seed -----------------------------------------------------------
    //
    // Manaster and Koehler: vega is largest at sqrt(2 |ln(F/K)| / T), and from
    // there Newton on a call converges monotonically. Their expression vanishes
    // at the money, where the price is nearly proportional to the volatility;
    // Brenner and Subrahmanyam invert that proportionality directly. Taking the
    // larger of the two gives the meaningful one in each case, and a positive
    // start in both.
    const double discounted_spot = market.spot * detail::discount_factor(market.dividend_yield, years);
    const double discounted_strike =
        option.strike * detail::discount_factor(market.rate, years);
    const double log_forward_moneyness =
        (discounted_spot > 0.0 && discounted_strike > 0.0)
            ? std::log(discounted_spot / discounted_strike)
            : 0.0;
    const double sqrt_years = std::sqrt(years);

    const double manaster_koehler =
        (years > 0.0) ? std::sqrt(2.0 * std::abs(log_forward_moneyness) / years) : 0.0;
    const double at_the_money_scale = discounted_spot * norm_pdf(0.0) * sqrt_years;
    const double brenner_subrahmanyam =
        (at_the_money_scale > 0.0) ? (target_price - floor_price) / at_the_money_scale : 0.0;

    double vol = std::max(manaster_koehler, brenner_subrahmanyam);
    if (!(vol > 0.0) || !std::isfinite(vol) || vol > settings.max_vol) {
        // Nothing usable came out of either seed — a degenerate expiry, or a
        // target so close to the asymptote that the linear inversion overshoots
        // the whole search range. Start in the middle and let the iteration work.
        vol = 0.5 * settings.max_vol;
    }

    // --- Newton -------------------------------------------------------------
    //
    // The only way out of this loop with an answer is the `return` inside it.
    // Every other exit — no slope, a step outside the bracket, a residual that
    // stops shrinking, the iteration limit — falls through to Brent below, which
    // is why there is no flag to say which one happened. Deleting this loop
    // entirely would leave a correct solver, and a slower one.
    double best_residual = std::numeric_limits<double>::infinity();
    std::size_t stalls = 0;

    PriceAndVega here{};
    for (; result.iterations < settings.max_iterations; ++result.iterations) {
        here = evaluate(option, market, vol);
        const double residual = here.price - target_price;

        if (std::abs(residual) <= tolerance) {
            result.vol = vol;
            result.price_residual = residual;
            result.vega = here.vega;
            result.method = ImpliedVolMethod::Newton;
            result.converged = true;
            return result;
        }

        if (!(here.vega > 0.0) || !std::isfinite(here.vega)) {
            // No slope to step along. Common far out of the money, where vega
            // underflows long before the price does.
            break;
        }

        const double next = vol - residual / here.vega;
        if (!std::isfinite(next) || next <= 0.0 || next > settings.max_vol) {
            break;
        }

        // Newton on a function with a very small second derivative can inch
        // along without ever reaching the tolerance. Three iterations that fail
        // to improve on the best residual so far is the signal; Brent then
        // finishes in a bounded number of steps whatever the shape.
        if (std::abs(residual) < best_residual) {
            best_residual = std::abs(residual);
            stalls = 0;
        } else if (++stalls >= 3) {
            break;
        }

        vol = next;
    }

    // --- Brent --------------------------------------------------------------
    //
    // `require_valid` has already established that the target is at or above the
    // price at zero and at or below the price at max_vol, so the bracket holds a
    // sign change and Brent cannot fail to find it.
    RootSearch search{};
    search.x_tolerance = 0.0;  // let the relative term and f_tolerance decide
    search.f_tolerance = tolerance;
    search.max_iterations = brent_budget;

    const auto residual_at = [&](double sigma) {
        return price(option, market.at(sigma)) - target_price;
    };
    const RootResult root = brent(residual_at, 0.0, settings.max_vol, search);

    const PriceAndVega finished = evaluate(option, market, root.root);
    result.vol = root.root;
    result.price_residual = finished.price - target_price;
    result.vega = finished.vega;
    result.iterations += root.iterations;
    result.method = ImpliedVolMethod::Brent;
    result.converged = std::abs(result.price_residual) <= tolerance;
    return result;
}

}  // namespace touchstone
