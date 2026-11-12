#include <touchstone/black_scholes.hpp>

#include <touchstone/detail/checks.hpp>
#include <touchstone/detail/scales.hpp>
#include <touchstone/normal.hpp>

#include <cmath>
#include <limits>
#include <stdexcept>

namespace touchstone {

ClosedFormQuote::ClosedFormQuote(const EuropeanVanilla& option, const QuotedMarket& market)
    : type_(option.type),
      sign_(option_sign(option.type)),
      spot_(market.spot),
      rate_(market.rate),
      dividend_yield_(market.dividend_yield),
      expiry_(option.expiry_years)
{
    if (!detail::is_finite_non_negative(market.spot)) {
        throw std::invalid_argument("touchstone: spot must be finite and non-negative");
    }
    if (!detail::is_finite_non_negative(option.strike)) {
        throw std::invalid_argument("touchstone: strike must be finite and non-negative");
    }
    if (!detail::is_finite_non_negative(option.expiry_years)) {
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
    strike_discount_ = detail::discount_factor(market.rate, t);
    spot_discount_ = detail::discount_factor(market.dividend_yield, t);
    if (!std::isfinite(strike_discount_) || !std::isfinite(spot_discount_)) {
        throw std::invalid_argument(
            "touchstone: the discount factor overflows — |rate| or |dividend_yield| times "
            "expiry_years exceeds 709");
    }
    discounted_spot_ = market.spot * spot_discount_;
    discounted_strike_ = option.strike * strike_discount_;
    if (!std::isfinite(discounted_spot_) || !std::isfinite(discounted_strike_)) {
        throw std::invalid_argument(
            "touchstone: the discounted spot or strike overflows a double");
    }
    // The carry half of the log-price's drift; `require_valid(vol)` has the other
    // half, and says why they are checked apart.
    if (!std::isfinite(detail::carry_time(market.rate, market.dividend_yield, t))) {
        throw std::invalid_argument(
            "touchstone: the carry (rate - dividend_yield) times expiry_years overflows a double");
    }
    // rho and dividend_rho carry a factor of T; theta's carry terms carry r and q.
    // These are the remaining products the seven formulas form, and an overflow in
    // any of them turns into inf - inf, which is a NaN, in theta.
    if (!std::isfinite(t * discounted_strike_) || !std::isfinite(t * discounted_spot_)) {
        throw std::invalid_argument(
            "touchstone: expiry_years times the discounted strike or spot overflows a double");
    }
    if (!std::isfinite(market.rate * discounted_strike_)
        || !std::isfinite(market.dividend_yield * discounted_spot_)) {
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

    // Nothing against nothing: ln(S/K) is 0/0 and would poison all seven outputs
    // with a NaN. Every one of them is zero by inspection, and `ClosedForm`
    // returns exactly that.
    nothing_against_nothing_ = (market.spot == 0.0 && option.strike == 0.0);
    if (nothing_against_nothing_) {
        return;
    }
    sqrt_expiry_ = std::sqrt(t);
    // Log-moneyness measured against the forward. It is the numerator of d1
    // without the variance term, and both of `ClosedForm`'s branches decide on
    // it, so the degenerate branch and the general one cannot disagree about
    // which side of the strike the forward is on.
    log_moneyness_ = detail::forward_log_moneyness(
        market.spot, option.strike, market.rate, market.dividend_yield, t);
}

void ClosedFormQuote::require_valid(double vol) const
{
    if (!detail::is_finite_non_negative(vol)) {
        throw std::invalid_argument("touchstone: vol must be finite and non-negative");
    }
    // The drift of the log-price is two products, and the kernel forms and adds
    // them separately: `(r - q) T` inside the log-moneyness, and `0.5 sigma^2 T`
    // beside it in d1. They are therefore checked separately, through the same
    // functions the kernel calls, so that the domain this guards and the
    // expressions it is guarding cannot drift apart.
    //
    // Checking their sum instead — `(r - q + 0.5 sigma^2) T` — is a different
    // domain, by more than an ulp. Put q = 0.5 sigma^2 with r = 0 and the sum is
    // exactly zero, so every expiry passes; the two terms themselves are -inf
    // and +inf, and d1's numerator is `-inf + inf`, which is a NaN.
    // sigma = sqrt(2e300), q = 1e300, T = 1e10 is such an input, and
    // `tests/test_associations.cpp` pins it along with the boundary of every
    // other check here. The carry half is in the constructor.
    if (!std::isfinite(detail::half_variance_time(vol, expiry_))) {
        throw std::invalid_argument(
            "touchstone: half the variance, 0.5 vol^2 times expiry_years, overflows a double");
    }
    // Implied by the line above — `sigma sqrt(T)` is the square root of twice it,
    // to within a rounding — and checked anyway, because a guarantee that holds
    // by derivation is one refactor away from not holding at all, and this is the
    // quantity `d1` divides by and every other method in the library measures its
    // width in.
    if (!std::isfinite(detail::total_volatility(vol, expiry_))) {
        throw std::invalid_argument(
            "touchstone: the total volatility vol times sqrt(expiry_years) overflows a double");
    }
}

ClosedForm ClosedFormQuote::at(double vol) const
{
    return ClosedForm(*this, vol);
}

ClosedForm::ClosedForm(const EuropeanVanilla& option, const BlackScholesMarket& market)
    : ClosedForm(ClosedFormQuote(option, QuotedMarket::of(market)), market.vol)
{
}

ClosedForm::ClosedForm(const ClosedFormQuote& quote, double vol)
    : quote_(quote)
{
    quote_.require_valid(vol);

    // Every output zero: N(w d1) and N(w d2) stay at zero, and so do the
    // discounted spot and strike, so the seven formulas return signed zeros
    // and nothing else.
    if (quote_.nothing_against_nothing_) {
        return;
    }

    const double t = quote_.expiry_;
    const double s = quote_.spot_;
    const double w = quote_.sign_;
    const double sqrt_t = quote_.sqrt_expiry_;
    const double log_moneyness = quote_.log_moneyness_;
    const double discounted_spot = quote_.discounted_spot_;

    // Theta's diffusion term, from the density at d1.
    const auto decay_at = [&](double phi1) {
        return -discounted_spot * phi1 * vol / (2.0 * sqrt_t);
    };

    // v is the total volatility to expiry, sigma sqrt(T) — the only scale the
    // distribution of the terminal log-price has. Everything below turns on
    // whether it is positive.
    const double v = detail::total_volatility(vol, t);

    double phi1 = 0.0;
    if (v > 0.0) {
        const double d1 = (log_moneyness + detail::half_variance_time(vol, t)) / v;
        const double d2 = d1 - v;
        phi1 = norm_pdf(d1);

        // N(w d) is evaluated directly rather than as 1 - N(-w d): see normal.hpp.
        n1_ = norm_cdf(w * d1);
        n2_ = norm_cdf(w * d2);
        // Divided rather than multiplied out: S v underflows to zero for a small
        // enough spot, and 1.5e-196 / 1e-330 is not infinity, it is 1.5e134.
        // At S = 0 the density is already zero and the quotient is 0/0; the limit
        // as S falls to zero is zero, because a worthless underlying has no
        // convexity.
        gamma_ = (s > 0.0) ? quote_.spot_discount_ * phi1 / s / v : 0.0;
        decay_ = decay_at(phi1);
    } else {
        // v == 0, so either sigma or T is zero: the terminal distribution
        // collapses to a point at the forward. N(w d1) and N(w d2) both tend to
        // the indicator of finishing in the money, and to 1/2 at the forward
        // itself, where d1 -> v/2 -> 0. Both are exact limits, not approximations.
        const bool at_the_forward = (log_moneyness == 0.0);
        const double indicator =
            (w * log_moneyness > 0.0) ? 1.0 : (at_the_forward ? 0.5 : 0.0);
        n1_ = indicator;
        n2_ = indicator;

        // Away from the forward the density vanishes and gamma, vega and the
        // decay term go with it. At the forward the mass concentrates and gamma
        // diverges: at_the_forward implies a finite ln(S/K), so the spot is
        // positive there and the divergence is real rather than an artefact of
        // dividing by zero.
        phi1 = at_the_forward ? norm_pdf(0.0) : 0.0;
        gamma_ = at_the_forward ? std::numeric_limits<double>::infinity() : 0.0;

        if (vol == 0.0) {
            // No diffusion, so no decay from diffusion — at any T, including
            // T = 0. The double limit is order-dependent and this is the order
            // chosen: with no volatility there is no time value to lose,
            // whatever the expiry.
            decay_ = 0.0;
        } else if (t == 0.0) {
            // An option expiring at this instant. At the strike, the remaining
            // time value goes to zero over no remaining time.
            decay_ = at_the_forward ? -std::numeric_limits<double>::infinity() : 0.0;
        } else {
            // sigma > 0 and T > 0, but their product underflowed. The limits
            // above are wrong here and the formula is right: it returns a very
            // small number rather than an infinity.
            decay_ = decay_at(phi1);
        }
    }
    vega_ = discounted_spot * phi1 * sqrt_t;
}

double ClosedForm::price() const noexcept
{
    return quote_.sign_ * (quote_.discounted_spot_ * n1_ - quote_.discounted_strike_ * n2_);
}

double ClosedForm::delta() const noexcept
{
    return quote_.sign_ * quote_.spot_discount_ * n1_;
}

double ClosedForm::gamma() const noexcept
{
    return gamma_;
}

double ClosedForm::vega() const noexcept
{
    return vega_;
}

double ClosedForm::theta() const noexcept
{
    const ClosedFormQuote& q = quote_;
    return decay_ - q.sign_ * q.rate_ * q.discounted_strike_ * n2_
           + q.sign_ * q.dividend_yield_ * q.discounted_spot_ * n1_;
}

double ClosedForm::rho() const noexcept
{
    return quote_.sign_ * quote_.expiry_ * quote_.discounted_strike_ * n2_;
}

double ClosedForm::dividend_rho() const noexcept
{
    return -quote_.sign_ * quote_.expiry_ * quote_.discounted_spot_ * n1_;
}

PriceAndGreeks ClosedForm::price_and_greeks() const noexcept
{
    return PriceAndGreeks{price(), delta(), gamma(), vega(), theta(), rho(), dividend_rho()};
}

void require_valid(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    ClosedFormQuote(option, QuotedMarket::of(market)).require_valid(market.vol);
}

PriceAndGreeks price_and_greeks(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    return ClosedForm(option, market).price_and_greeks();
}

double price(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    return ClosedForm(option, market).price();
}

double delta(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    return ClosedForm(option, market).delta();
}

double gamma(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    return ClosedForm(option, market).gamma();
}

double vega(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    return ClosedForm(option, market).vega();
}

double theta(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    return ClosedForm(option, market).theta();
}

double rho(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    return ClosedForm(option, market).rho();
}

double dividend_rho(const EuropeanVanilla& option, const BlackScholesMarket& market)
{
    return ClosedForm(option, market).dividend_rho();
}

}  // namespace touchstone
