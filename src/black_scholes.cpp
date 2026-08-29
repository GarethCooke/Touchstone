#include <touchstone/black_scholes.hpp>

#include <touchstone/normal.hpp>

#include <cmath>
#include <limits>
#include <stdexcept>

namespace touchstone {
namespace {

/// Everything the price and all six Greeks are built from, evaluated once.
///
/// Two of the seven outputs are unbounded somewhere on the closed domain, and
/// both singularities live in this struct rather than in the formulas that use
/// it: `gamma` divides by S and by the total volatility, and `decay` — theta's
/// diffusion term — divides by sqrt(T). Keeping the limits here means the seven
/// expressions in `price_and_greeks` below are the formulas of
/// `golden/SCHEMA.md` verbatim, with no branch in sight.
struct Kernel {
    double w{};       ///< +1 for a call, -1 for a put.
    double sqrt_t{};  ///< sqrt(T).
    double df_r{};    ///< exp(-rT).
    double df_q{};    ///< exp(-qT).
    double sq{};      ///< S exp(-qT).
    double kr{};      ///< K exp(-rT).
    double n1{};      ///< N(w d1).
    double n2{};      ///< N(w d2).
    double gamma{};   ///< d2V/dS2. Type-independent.
    double vega{};    ///< dV/dsigma. Type-independent.
    double decay{};   ///< -S exp(-qT) phi(d1) sigma / (2 sqrt(T)). Type-independent.
};

Kernel make_kernel(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    require_valid(option, market);

    const double s = market.spot;
    const double k = option.strike;
    const double t = option.expiry_years;
    const double sigma = market.vol;

    Kernel kern{};
    kern.w = option_sign(option.type);

    // Nothing against nothing: ln(S/K) is 0/0 and would poison all seven outputs
    // with a NaN. Every one of them is zero by inspection. This is decided before
    // any arithmetic, because K exp(-rT) is itself 0 * inf when the strike is zero
    // and the discount factor has overflowed.
    if (s == 0.0 && k == 0.0) {
        return kern;
    }

    kern.sqrt_t = std::sqrt(t);
    kern.df_r = std::exp(-market.rate * t);
    kern.df_q = std::exp(-market.dividend_yield * t);
    kern.sq = s * kern.df_q;
    kern.kr = k * kern.df_r;

    // v is the total volatility to expiry, sigma sqrt(T) — the only scale the
    // distribution of the terminal log-price has. Everything below turns on
    // whether it is positive.
    const double v = sigma * kern.sqrt_t;

    // Log-moneyness measured against the forward: ln(S/K) + (r - q)T. Positive
    // means the forward is above the strike. It is the numerator of d1 without
    // the variance term, and both branches below decide on it, so the degenerate
    // branch and the general one cannot disagree about which side of the strike
    // the forward is on.
    const double log_moneyness = std::log(s / k) + (market.rate - market.dividend_yield) * t;

    if (v > 0.0) {
        const double d1 = (log_moneyness + 0.5 * sigma * sigma * t) / v;
        const double d2 = d1 - v;
        const double phi1 = norm_pdf(d1);

        // N(w d) is evaluated directly rather than as 1 - N(-w d): see normal.hpp.
        kern.n1 = norm_cdf(kern.w * d1);
        kern.n2 = norm_cdf(kern.w * d2);
        kern.vega = kern.sq * phi1 * kern.sqrt_t;
        // Divided rather than multiplied out: S v underflows to zero for a small
        // enough spot, and 1.5e-196 / 1e-330 is not infinity, it is 1.5e134.
        // At S = 0 the density is already zero and the quotient is 0/0; the limit
        // as S falls to zero is zero, because a worthless underlying has no
        // convexity.
        kern.gamma = (s > 0.0) ? kern.df_q * phi1 / s / v : 0.0;
        kern.decay = -kern.sq * phi1 * sigma / (2.0 * kern.sqrt_t);
        return kern;
    }

    // v == 0, so either sigma or T is zero: the terminal distribution collapses
    // to a point at the forward. N(w d1) and N(w d2) both tend to the indicator
    // of finishing in the money, and to 1/2 at the forward itself, where
    // d1 -> v/2 -> 0. Both are exact limits, not approximations.
    const bool at_the_forward = (log_moneyness == 0.0);
    const double indicator =
        (kern.w * log_moneyness > 0.0) ? 1.0 : (at_the_forward ? 0.5 : 0.0);
    kern.n1 = indicator;
    kern.n2 = indicator;

    // Away from the forward the density vanishes and gamma, vega and the decay
    // term go with it. At the forward the mass concentrates and gamma diverges:
    // at_the_forward implies a finite ln(S/K), so the spot is positive there and
    // the divergence is real rather than an artefact of dividing by zero.
    const double phi1 = at_the_forward ? norm_pdf(0.0) : 0.0;
    kern.vega = kern.sq * phi1 * kern.sqrt_t;
    kern.gamma = at_the_forward ? std::numeric_limits<double>::infinity() : 0.0;

    if (sigma == 0.0) {
        // No diffusion, so no decay from diffusion — at any T, including T = 0.
        // The double limit is order-dependent and this is the order chosen: with
        // no volatility there is no time value to lose, whatever the expiry.
        kern.decay = 0.0;
    } else if (t == 0.0) {
        // An option expiring at this instant. At the strike, the remaining time
        // value goes to zero over no remaining time.
        kern.decay = at_the_forward ? -std::numeric_limits<double>::infinity() : 0.0;
    } else {
        // sigma > 0 and T > 0, but their product underflowed. The limits above
        // are wrong here and the formula is right: it returns a very small
        // number rather than an infinity.
        kern.decay = -kern.sq * phi1 * sigma / (2.0 * kern.sqrt_t);
    }
    return kern;
}

}  // namespace

void require_valid(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    const auto priceable = [](double x) { return std::isfinite(x) && x >= 0.0; };

    if (!priceable(market.spot)) {
        throw std::invalid_argument("touchstone: spot must be finite and non-negative");
    }
    if (!priceable(option.strike)) {
        throw std::invalid_argument("touchstone: strike must be finite and non-negative");
    }
    if (!priceable(market.vol)) {
        throw std::invalid_argument("touchstone: vol must be finite and non-negative");
    }
    if (!priceable(option.expiry_years)) {
        throw std::invalid_argument("touchstone: expiry_years must be finite and non-negative");
    }
    // r and q are unconstrained in sign. A negative rate is a market state, not
    // a corner: the golden grid has one.
    if (!std::isfinite(market.rate)) {
        throw std::invalid_argument("touchstone: rate must be finite");
    }
    if (!std::isfinite(market.dividend_yield)) {
        throw std::invalid_argument("touchstone: dividend_yield must be finite");
    }

    // Representability. The closed form is evaluated in the underlying's own
    // units, so its domain is bounded by what a double can hold and not only by
    // what makes financial sense. A discount factor that overflows, a discounted
    // spot that does, or a moneyness S/K that does, makes the arithmetic
    // meaningless rather than merely inaccurate — and the failure is silent,
    // because inf - inf and 0 * inf are NaN and a NaN compares false against
    // every tolerance a caller might test it with. Rejecting these inputs is the
    // honest answer.
    //
    // Nothing plausible is excluded. The bound on the first is |r| T > 709, and
    // on the second that S or K is within a few orders of the largest double.
    const double t = option.expiry_years;
    const double df_r = std::exp(-market.rate * t);
    const double df_q = std::exp(-market.dividend_yield * t);
    if (!std::isfinite(df_r) || !std::isfinite(df_q)) {
        throw std::invalid_argument(
            "touchstone: the discount factor overflows — |rate| or |dividend_yield| times "
            "expiry_years exceeds 709");
    }
    const double discounted_spot = market.spot * df_q;
    const double discounted_strike = option.strike * df_r;
    if (!std::isfinite(discounted_spot) || !std::isfinite(discounted_strike)) {
        throw std::invalid_argument(
            "touchstone: the discounted spot or strike overflows a double");
    }
    if (!std::isfinite((market.rate - market.dividend_yield + 0.5 * market.vol * market.vol) * t)) {
        throw std::invalid_argument("touchstone: drift times expiry_years overflows a double");
    }
    // rho and dividend_rho carry a factor of T; theta's carry terms carry r and q.
    // These are the remaining products the seven formulas form, and an overflow in
    // any of them turns into inf - inf, which is a NaN, in theta.
    if (!std::isfinite(t * discounted_strike) || !std::isfinite(t * discounted_spot)) {
        throw std::invalid_argument(
            "touchstone: expiry_years times the discounted strike or spot overflows a double");
    }
    if (!std::isfinite(market.rate * discounted_strike)
        || !std::isfinite(market.dividend_yield * discounted_spot)) {
        throw std::invalid_argument(
            "touchstone: rate times the discounted strike, or dividend_yield times the discounted "
            "spot, overflows a double");
    }
    if (market.spot > 0.0 && option.strike > 0.0) {
        const double moneyness = market.spot / option.strike;
        if (!std::isfinite(moneyness) || moneyness == 0.0) {
            throw std::invalid_argument(
                "touchstone: spot over strike overflows a double, so ln(S/K) cannot be formed");
        }
    }
}

PriceAndGreeks price_and_greeks(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    const Kernel kern = make_kernel(option, market);
    const double t = option.expiry_years;

    PriceAndGreeks out{};
    out.price = kern.w * (kern.sq * kern.n1 - kern.kr * kern.n2);
    out.delta = kern.w * kern.df_q * kern.n1;
    out.gamma = kern.gamma;
    out.vega = kern.vega;
    out.theta = kern.decay - kern.w * market.rate * kern.kr * kern.n2
                + kern.w * market.dividend_yield * kern.sq * kern.n1;
    out.rho = kern.w * t * kern.kr * kern.n2;
    out.dividend_rho = -kern.w * t * kern.sq * kern.n1;
    return out;
}

double price(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    const Kernel kern = make_kernel(option, market);
    return kern.w * (kern.sq * kern.n1 - kern.kr * kern.n2);
}

double delta(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    const Kernel kern = make_kernel(option, market);
    return kern.w * kern.df_q * kern.n1;
}

double gamma(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    return make_kernel(option, market).gamma;
}

double vega(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    return make_kernel(option, market).vega;
}

double theta(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    const Kernel kern = make_kernel(option, market);
    return kern.decay - kern.w * market.rate * kern.kr * kern.n2
           + kern.w * market.dividend_yield * kern.sq * kern.n1;
}

double rho(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    const Kernel kern = make_kernel(option, market);
    return kern.w * option.expiry_years * kern.kr * kern.n2;
}

double dividend_rho(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    const Kernel kern = make_kernel(option, market);
    return -kern.w * option.expiry_years * kern.sq * kern.n1;
}

}  // namespace touchstone
