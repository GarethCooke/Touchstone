// The scalar quantities every pricing method in this library forms from a
// market and an expiry — each written once, in one association.
//
// Floating-point addition and multiplication are not associative, so `0.5 σ² T`
// grouped as `((0.5 σ) σ) T` and grouped as `(0.5 σ) (σ T)` are two different
// numbers at the edges of the range, and two different domains: one overflows
// where the other does not. That matters twice over.
//
//   - **A domain check is only as good as its association.** `require_valid` in
//     `black_scholes.cpp` promises that an accepted input never produces a NaN.
//     It keeps that promise by checking that each product the formulas form is
//     representable — which is a promise about *these expressions*, not about
//     the mathematics. A check that formed the same quantity a different way
//     would guard a different set of inputs than the one the formulas actually
//     use, and the gap between the two is silent: `inf - inf` is a NaN, and a
//     NaN compares false against every tolerance a caller might test it with.
//     T2's review found exactly that gap and left it for T3; the file below is
//     the repair, and `tests/test_associations.cpp` is what holds it shut.
//
//   - **Three methods must agree (I20).** The closed form, the Monte Carlo and
//     the finite-difference grid are only comparable if they are pricing the
//     same option, and at the last few digits that means forming the same
//     `σ√T` from the same two doubles by the same route. Two roundings of one
//     quantity are two quantities.
//
// Nothing here validates. These are the expressions themselves, so that the
// code that checks them and the code that uses them cannot drift apart; every
// one may return an infinity or a NaN for an input outside the domain, and
// deciding what to do about that is `require_valid`'s job, not this file's.

#pragma once

#include <cmath>

namespace touchstone::detail {

/// `σ√T` — the total volatility to expiry, and the only scale the terminal
/// log-price distribution has.
///
/// The volatility is scaled by the square root of the time rather than the
/// variance by the time: `(σ√T)²` survives a volatility above 1.3e154 that
/// `σ² T` does not, and every method in the library reads its width from this.
[[nodiscard]] inline double total_volatility(double vol, double years) noexcept
{
    return vol * std::sqrt(years);
}

/// `½ σ² T` — the convexity correction in `d₁`, and the Itô term in the drift
/// of the log-price. Associated as `((0.5 σ) σ) T`, which is what
/// `black_scholes.cpp` writes and therefore what its domain check must guard.
[[nodiscard]] inline double half_variance_time(double vol, double years) noexcept
{
    return 0.5 * vol * vol * years;
}

/// `(r − q) T` — the cost of carry over the life of the option.
[[nodiscard]] inline double carry_time(double rate, double dividend_yield, double years) noexcept
{
    return (rate - dividend_yield) * years;
}

/// `e^{−rT}`. Also the dividend discount `e^{−qT}`, which is the same function
/// of a different rate.
[[nodiscard]] inline double discount_factor(double rate, double years) noexcept
{
    return std::exp(-rate * years);
}

/// `ln(S/K) + (r − q) T` — log-moneyness measured against the forward, which is
/// the numerator of `d₁` without its variance term. Positive means the forward
/// is above the strike.
///
/// The two terms are formed and added separately, exactly as written. A check
/// that instead formed `(r − q + ½σ²)` first and multiplied by `T` afterwards
/// would accept inputs on which these two terms are `+∞` and `−∞`; their sum is
/// then a NaN, and the check would have said the input was fine.
[[nodiscard]] inline double forward_log_moneyness(double spot,
                                                  double strike,
                                                  double rate,
                                                  double dividend_yield,
                                                  double years) noexcept
{
    return std::log(spot / strike) + carry_time(rate, dividend_yield, years);
}

}  // namespace touchstone::detail
