#include <touchstone/implied_vol.hpp>

#include <touchstone/detail/checks.hpp>
#include <touchstone/normal.hpp>
#include <touchstone/root_finding.hpp>

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

// --- What both solvers share ------------------------------------------------

/// The price at zero volatility: the discounted intrinsic value of the forward.
/// Taken from the closed form itself rather than rewritten here: that limit is
/// exact in `black_scholes.cpp`, tested there, and rewriting it would be a
/// second opinion about the same thing.
[[nodiscard]] double floor_of(const ClosedFormQuote& quote)
{
    return quote.at(0.0).price();
}

/// The limit as the volatility grows without bound. d1 -> +inf and d2 -> -inf,
/// so N(w d1) -> 1 and N(w d2) -> 0 for a call and the other way for a put: the
/// call tends to the discounted spot and the put to the discounted strike, from
/// below in both cases.
[[nodiscard]] double ceiling_of(const ClosedFormQuote& quote) noexcept
{
    return quote.type() == OptionType::Call ? quote.discounted_spot()
                                             : quote.discounted_strike();
}

[[nodiscard]] double scale_of(const ClosedFormQuote& quote) noexcept
{
    return std::max(quote.discounted_spot(), quote.discounted_strike());
}

/// A budget and a tolerance a search can run on.
void require_valid_budget(std::size_t max_iterations, double price_tolerance)
{
    if (max_iterations == 0) {
        throw std::invalid_argument("implied vol: max_iterations must be at least 1");
    }
    if (!detail::is_finite_positive(price_tolerance)) {
        throw std::invalid_argument("implied vol: price_tolerance must be finite and positive");
    }
}

void require_valid_target(double target_price)
{
    if (!std::isfinite(target_price)) {
        throw std::invalid_argument("implied vol: the target price must be finite");
    }
}

/// The volatility-free half of the closed form, and the closed form at both
/// ends of a search. Both ends are priced, so both must be inside the closed
/// form's domain, and then every volatility between them is too.
struct Bracket {
    ClosedFormQuote quote;
    ClosedForm low;
    ClosedForm high;
};

[[nodiscard]] Bracket bracket_of(const EuropeanVanilla& option,
                                 const QuotedMarket& market,
                                 double low_vol,
                                 double high_vol)
{
    const ClosedFormQuote quote(option, market);
    return Bracket{quote, quote.at(low_vol), quote.at(high_vol)};
}

/// The answer at a volatility: the volatility, the price there less the
/// target, and the vega there. Both solvers' results carry these three.
template <class Result>
void answer(Result& result, double vol, const ClosedForm& there, double target_price) noexcept
{
    result.vol = vol;
    result.price_residual = there.price() - target_price;
    result.vega = there.vega();
}

// --- Newton-Brent -----------------------------------------------------------

/// The settings, the option and the target, validated once, with everything
/// the solve reads from them computed once.
struct NewtonBrentSearch {
    ClosedFormQuote quote;
    double floor_price{};
    /// The absolute price tolerance the settings amount to for this option, and
    /// the allowance inside which a target below the zero-volatility price is a
    /// rounding rather than an arbitrage.
    double tolerance{};
};

[[nodiscard]] NewtonBrentSearch validated_search(const EuropeanVanilla& option,
                                                 const QuotedMarket& market,
                                                 double target_price,
                                                 const ImpliedVolSettings& settings)
{
    if (!detail::is_finite_positive(settings.max_vol)) {
        throw std::invalid_argument("implied vol: max_vol must be finite and positive");
    }
    require_valid_budget(settings.max_iterations, settings.price_tolerance);

    const Bracket bracket = bracket_of(option, market, 0.0, settings.max_vol);
    const double floor_price = bracket.low.price();
    const double at_max = bracket.high.price();

    require_valid_target(target_price);

    const double ceiling_price = ceiling_of(bracket.quote);

    // The floor of one ulp of 1.0 keeps a tolerance for an option whose scale
    // has underflowed to zero from being zero itself, which no iteration could
    // ever reach.
    const double allowance = std::max(settings.price_tolerance * scale_of(bracket.quote),
                                      std::numeric_limits<double>::epsilon());
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
    if (target_price > at_max + allowance) {
        throw std::invalid_argument(
            "implied vol: the target price " + std::to_string(target_price)
            + " exceeds the price at max_vol = " + std::to_string(settings.max_vol) + ", which is "
            + std::to_string(at_max)
            + "; the solution is above the search range rather than outside the model");
    }
    return NewtonBrentSearch{bracket.quote, floor_price, allowance};
}

}  // namespace

double price_scale(const EuropeanVanilla& option, const QuotedMarket& market)
{
    return scale_of(ClosedFormQuote(option, market));
}

double lowest_price(const EuropeanVanilla& option, const QuotedMarket& market)
{
    return floor_of(ClosedFormQuote(option, market));
}

double highest_price(const EuropeanVanilla& option, const QuotedMarket& market)
{
    return ceiling_of(ClosedFormQuote(option, market));
}

void require_valid(const EuropeanVanilla& option,
                   const QuotedMarket& market,
                   double target_price,
                   const ImpliedVolSettings& settings)
{
    static_cast<void>(validated_search(option, market, target_price, settings));
}

ImpliedVolResult implied_vol(const EuropeanVanilla& option,
                             const QuotedMarket& market,
                             double target_price,
                             const ImpliedVolSettings& settings)
{
    const NewtonBrentSearch search = validated_search(option, market, target_price, settings);
    const ClosedFormQuote& quote = search.quote;
    const double tolerance = search.tolerance;

    ImpliedVolResult result{};

    // A target at or below the zero-volatility price has the answer zero, and
    // Newton would divide by a vega of zero to find it. "At or below" rather
    // than "equal to" because the search has already allowed a target a few
    // ulps under the floor: deep enough in the money the price stops depending
    // on the volatility at all, and every volatility from zero upward returns
    // the same double. The zero is then the honest answer and `vega` is what
    // says so.
    if (target_price <= search.floor_price) {
        answer(result, 0.0, quote.at(0.0), target_price);
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
    const double years = option.expiry_years;
    const double discounted_spot = quote.discounted_spot();
    const double log_forward_moneyness =
        (discounted_spot > 0.0 && quote.discounted_strike() > 0.0) ? quote.forward_log_moneyness()
                                                                   : 0.0;
    const double manaster_koehler =
        (years > 0.0) ? std::sqrt(2.0 * std::abs(log_forward_moneyness) / years) : 0.0;
    const double at_the_money_scale = discounted_spot * norm_pdf(0.0) * quote.sqrt_expiry();
    const double brenner_subrahmanyam =
        (at_the_money_scale > 0.0) ? (target_price - search.floor_price) / at_the_money_scale
                                   : 0.0;

    double vol = std::max(manaster_koehler, brenner_subrahmanyam);
    if (!detail::is_finite_positive(vol) || vol > settings.max_vol) {
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

    for (; result.iterations < settings.max_iterations; ++result.iterations) {
        const ClosedForm here = quote.at(vol);
        const double residual = here.price() - target_price;

        if (std::abs(residual) <= tolerance) {
            answer(result, vol, here, target_price);
            result.method = ImpliedVolMethod::Newton;
            result.converged = true;
            return result;
        }

        // No slope to step along. Common far out of the money, where vega
        // underflows long before the price does.
        const double vega = here.vega();
        if (!detail::is_finite_positive(vega)) {
            break;
        }

        const double next = vol - residual / vega;
        if (!detail::is_finite_positive(next) || next > settings.max_vol) {
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
    // The search has already established that the target is at or above the
    // price at zero and at or below the price at max_vol, so the bracket holds a
    // sign change and Brent cannot fail to find it.
    RootSearch brent_search{};
    brent_search.x_tolerance = 0.0;  // let the relative term and f_tolerance decide
    brent_search.f_tolerance = tolerance;
    brent_search.max_iterations = brent_budget;

    const auto residual_at = [&](double sigma) { return quote.at(sigma).price() - target_price; };
    const RootResult root = brent(residual_at, 0.0, settings.max_vol, brent_search);

    answer(result, root.root, quote.at(root.root), target_price);
    result.iterations += root.iterations;
    result.method = ImpliedVolMethod::Brent;
    result.converged = std::abs(result.price_residual) <= tolerance;
    return result;
}

// --- Newton with a bisection guard ------------------------------------------

namespace {

/// The settings, the option and the target, validated, with the closed form's
/// volatility-free half and both ends of the bracket computed once.
[[nodiscard]] Bracket validated_bracket(const EuropeanVanilla& option,
                                        const QuotedMarket& market,
                                        double target_price,
                                        const SafeguardedSettings& settings)
{
    if (!detail::is_finite_non_negative(settings.min_vol)
        || !detail::is_finite_positive(settings.max_vol) || !(settings.min_vol < settings.max_vol)) {
        throw std::invalid_argument(
            "implied vol: the bracket needs 0 <= min_vol < max_vol, both finite");
    }
    if (!std::isfinite(settings.initial_vol)) {
        throw std::invalid_argument("implied vol: initial_vol must be finite");
    }
    if (!detail::is_finite_non_negative(settings.vol_tolerance)) {
        throw std::invalid_argument("implied vol: vol_tolerance must be finite and non-negative");
    }
    require_valid_budget(settings.max_iterations, settings.price_tolerance);

    Bracket bracket = bracket_of(option, market, settings.min_vol, settings.max_vol);
    require_valid_target(target_price);
    return bracket;
}

}  // namespace

const char* to_string(SafeguardedStatus status) noexcept
{
    switch (status) {
        case SafeguardedStatus::Converged:
            return "converged";
        case SafeguardedStatus::BelowLowerBound:
            return "below_lower_bound";
        case SafeguardedStatus::AboveUpperBound:
            return "above_upper_bound";
        case SafeguardedStatus::BelowSigmaLo:
            return "below_sigma_lo";
        case SafeguardedStatus::AboveSigmaHi:
            return "above_sigma_hi";
        case SafeguardedStatus::MaxIter:
            return "max_iter";
    }
    return "unknown";
}

void require_valid(const EuropeanVanilla& option,
                   const QuotedMarket& market,
                   double target_price,
                   const SafeguardedSettings& settings)
{
    static_cast<void>(validated_bracket(option, market, target_price, settings));
}

SafeguardedResult implied_vol_safeguarded(const EuropeanVanilla& option,
                                          const QuotedMarket& market,
                                          double target_price,
                                          const SafeguardedSettings& settings)
{
    const Bracket bracket = validated_bracket(option, market, target_price, settings);
    const ClosedFormQuote& quote = bracket.quote;

    SafeguardedResult result{};
    const auto finish = [&](SafeguardedStatus status, double vol, const ClosedForm& there) {
        result.status = status;
        result.converged = (status == SafeguardedStatus::Converged);
        answer(result, vol, there, target_price);
    };

    // Stop at a price error within this: relative to the price above one and
    // absolute below it, which is the golden file's comparison rule.
    const double tolerance = settings.price_tolerance * std::max(1.0, std::abs(target_price));

    // A price outside the bounds has no implied volatility, and is answered
    // with a status rather than a number pretending to be one. The volatility
    // reported is the nearest the model comes — zero, where the price is the
    // lower bound, or the infinite volatility the upper bound is the limit at —
    // and the residual is the distance to that bound.
    const double upper = ceiling_of(quote);
    if (target_price < floor_of(quote) - tolerance) {
        finish(SafeguardedStatus::BelowLowerBound, 0.0, quote.at(0.0));
        return result;
    }
    if (target_price > upper + tolerance) {
        result.status = SafeguardedStatus::AboveUpperBound;
        result.converged = false;
        result.vol = std::numeric_limits<double>::infinity();
        result.price_residual = upper - target_price;
        result.vega = 0.0;
        return result;
    }

    // Inside the bounds but outside the prices at the ends of the bracket: the
    // answer exists and is outside the search interval.
    if (target_price < bracket.low.price() - tolerance) {
        finish(SafeguardedStatus::BelowSigmaLo, settings.min_vol, bracket.low);
        return result;
    }
    if (target_price > bracket.high.price() + tolerance) {
        finish(SafeguardedStatus::AboveSigmaHi, settings.max_vol, bracket.high);
        return result;
    }

    // The bracket: price(a) <= target <= price(b), the price increasing in the
    // volatility.
    double a = settings.min_vol;
    double b = settings.max_vol;
    double vol = std::min(std::max(settings.initial_vol, a), b);

    for (std::size_t iteration = 1; iteration <= settings.max_iterations; ++iteration) {
        const ClosedForm here = quote.at(vol);
        const double error = here.price() - target_price;
        if (settings.record_steps) {
            result.steps.push_back(SafeguardedStep{iteration, vol, here.price(), error});
        }
        result.iterations = iteration;
        if (std::abs(error) <= tolerance) {
            finish(SafeguardedStatus::Converged, vol, here);
            return result;
        }

        // The sign of the error says which side of the answer this volatility
        // is, and the bracket closes on that side.
        if (error > 0.0) {
            b = vol;
        } else {
            a = vol;
        }

        // Newton's step if there is a slope to follow and the step stays
        // strictly inside the bracket; a bisection otherwise.
        const double vega = here.vega();
        double next = 0.5 * (a + b);
        bool bisected = true;
        if (vega > 0.0) {
            const double newton = vol - error / vega;
            if (std::isfinite(newton) && a < newton && newton < b) {
                next = newton;
                bisected = false;
            }
        }
        if (bisected) {
            ++result.bisections;
        }
        vol = next;

        if (b - a < settings.vol_tolerance) {
            finish(SafeguardedStatus::Converged, vol, quote.at(vol));
            return result;
        }
    }

    finish(SafeguardedStatus::MaxIter, vol, quote.at(vol));
    return result;
}

}  // namespace touchstone
