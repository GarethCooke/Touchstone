// European vanilla options under Black-Scholes-Merton: closed form and analytic Greeks.
//
// Scope is the constitution's I21 — European vanillas, one underlying, constant
// rate and volatility, dividend yield — and the formulas are the ones written
// out in `golden/SCHEMA.md`, which is also the contract this file is tested
// against. Every output is a raw partial derivative in the units that document
// states: vega per 1.00 of vol, theta per year, rho per 1.00 of rate. Scaling
// for display happens at the point of display, once, visibly.

#pragma once

namespace touchstone {

enum class OptionType {
    Call,
    Put,
};

/// The `w` of the formulas: +1 for a call, -1 for a put.
[[nodiscard]] constexpr double option_sign(OptionType type) noexcept
{
    return type == OptionType::Call ? 1.0 : -1.0;
}

/// The contract. What was agreed, independent of what the market is doing.
struct EuropeanVanilla {
    double strike{};        ///< K >= 0.
    double expiry_years{};  ///< T >= 0, in years on the curve's own day count.
    OptionType type{OptionType::Call};
};

/// The market. What is observed, independent of any particular contract.
struct BlackScholesMarket {
    double spot{};            ///< S >= 0.
    double vol{};             ///< sigma >= 0, annualised, as a decimal: 0.30 is 30%.
    double rate{};            ///< r, continuously compounded. May be negative.
    double dividend_yield{};  ///< q, continuous. May be negative.
};

/// All seven values from one evaluation of the closed form.
struct PriceAndGreeks {
    double price{};         ///< V.
    double delta{};         ///< dV/dS, per 1.00 of spot.
    double gamma{};         ///< d2V/dS2, per 1.00 of spot squared.
    double vega{};          ///< dV/dsigma, per 1.00 of vol.
    double theta{};         ///< dV/dt, per year. Negative for a long position that decays.
    double rho{};           ///< dV/dr, per 1.00 of rate.
    double dividend_rho{};  ///< dV/dq, per 1.00 of dividend yield.
};

/// Throws `std::invalid_argument` if the inputs are outside the domain this
/// header prices on. That domain is two things at once:
///
///   - Financial: every field finite, and K, T, S, sigma non-negative. r and q
///     may take any finite value, negative rates included — a negative rate is
///     a market state, not a corner, and the golden grid contains one.
///   - Representable: the discount factors, the discounted spot and strike, and
///     the moneyness S/K must all fit in a double. They stop fitting at |r|T
///     above 709, or at a spot or strike within a few orders of the largest
///     double — far outside anything this library is for, but reachable, and
///     silent if unchecked, because a NaN compares false against every
///     tolerance a caller might test it against.
///
/// Accepting an input is therefore a promise, and it is the promise that
/// matters rather than a tidier-sounding one: **no output will ever be NaN**,
/// and price, delta, vega, rho and dividend_rho will be finite. gamma and theta
/// may be infinite — gamma at the strike, where its limit genuinely is, and
/// either of them where the true value exceeds what a double can hold. An
/// infinity is a saturated number that compares correctly against a tolerance;
/// a NaN compares false against every test a caller could write, which is why
/// only one of the two is ruled out. `tests/test_limits.cpp` holds this to a
/// sweep of the domain including its boundary.
///
/// Every entry point below calls this first. A caller that wants to know
/// without catching can call it directly.
void require_valid(const EuropeanVanilla& option, const BlackScholesMarket& market);

/// Price and all six Greeks from a single evaluation. Prefer this to the
/// individual accessors when more than one value is wanted: the shared work —
/// two exponentials, two normal CDFs, one density — is done once.
[[nodiscard]] PriceAndGreeks price_and_greeks(const EuropeanVanilla& option,
                                              const BlackScholesMarket& market);

[[nodiscard]] double price(const EuropeanVanilla& option, const BlackScholesMarket& market);
[[nodiscard]] double delta(const EuropeanVanilla& option, const BlackScholesMarket& market);
[[nodiscard]] double gamma(const EuropeanVanilla& option, const BlackScholesMarket& market);
[[nodiscard]] double vega(const EuropeanVanilla& option, const BlackScholesMarket& market);
[[nodiscard]] double theta(const EuropeanVanilla& option, const BlackScholesMarket& market);
[[nodiscard]] double rho(const EuropeanVanilla& option, const BlackScholesMarket& market);
[[nodiscard]] double dividend_rho(const EuropeanVanilla& option, const BlackScholesMarket& market);

}  // namespace touchstone
