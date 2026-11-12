// European vanilla options under Black-Scholes-Merton: closed form and analytic Greeks.
//
// Scope is the constitution's I21 — European vanillas, one underlying, constant
// rate and volatility, dividend yield — and the formulas are the ones written
// out in `golden/SCHEMA.md`, which is also the contract this file is tested
// against. Every output is a raw partial derivative in the units that document
// states: vega per 1.00 of vol, theta per year, rho per 1.00 of rate. Scaling
// for display happens at the point of display, once, visibly.

#pragma once

#include <touchstone/contract.hpp>

namespace touchstone {

/// The market. What is observed, independent of any particular contract.
struct BlackScholesMarket {
    double spot{};            ///< S >= 0.
    double vol{};             ///< sigma >= 0, annualised, as a decimal: 0.30 is 30%.
    double rate{};            ///< r, continuously compounded. May be negative.
    double dividend_yield{};  ///< q, continuous. May be negative.
};

/// The market with the volatility left out, because that is the unknown.
///
/// A separate type rather than a `BlackScholesMarket` with a field to ignore:
/// an ignored field is a trap, and this one would be the trap of quoting a
/// volatility to a function whose job is to tell you what it is.
struct QuotedMarket {
    double spot{};
    double rate{};
    double dividend_yield{};

    [[nodiscard]] BlackScholesMarket at(double vol) const noexcept
    {
        return BlackScholesMarket{spot, vol, rate, dividend_yield};
    }
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
/// The representability half is a promise about *these expressions*, not about
/// the mathematics: floating-point multiplication does not associate, so a
/// product grouped one way overflows where the same product grouped another way
/// does not. Every quantity checked here is therefore formed by the function in
/// `touchstone/detail/scales.hpp` that the formulas themselves call, and adding a
/// product to the formulas without adding it there is the way this promise gets
/// broken. It has been broken once already, and `tests/test_associations.cpp`
/// records how.
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

// --- The evaluation behind the free functions --------------------------------
//
// Every free function above is one of these, built, read once and discarded. A
// caller that wants several outputs from one input, or one input at many
// volatilities, builds them itself and pays for the validation and the
// arithmetic once.

class ClosedForm;

/// Everything in the closed form that does not depend on the volatility: the
/// discount factors, the discounted spot and strike, the forward log-moneyness
/// and `√T`, validated and computed once.
///
/// This is the half an implied-volatility search holds fixed while it varies
/// the other: built once per solve, it makes each step of the search the
/// volatility's half of the arithmetic and nothing more.
class ClosedFormQuote {
public:
    /// Throws `std::invalid_argument` for the part of `require_valid`'s domain
    /// that does not involve the volatility.
    ClosedFormQuote(const EuropeanVanilla& option, const QuotedMarket& market);

    /// The closed form at one volatility. Throws `std::invalid_argument` if the
    /// volatility is outside the domain: negative, not finite, or large enough
    /// that `½σ²T` or `σ√T` overflows.
    [[nodiscard]] ClosedForm at(double vol) const;

    [[nodiscard]] OptionType type() const noexcept { return type_; }

    /// `S e^{-qT}`.
    [[nodiscard]] double discounted_spot() const noexcept { return discounted_spot_; }

    /// `K e^{-rT}`.
    [[nodiscard]] double discounted_strike() const noexcept { return discounted_strike_; }

    /// `ln(S/K) + (r - q)T`: positive when the forward is above the strike. Zero
    /// when the spot and the strike are both zero, where the ratio has no value
    /// and every output is zero by inspection.
    [[nodiscard]] double forward_log_moneyness() const noexcept { return log_moneyness_; }

    /// `√T`.
    [[nodiscard]] double sqrt_expiry() const noexcept { return sqrt_expiry_; }

private:
    friend class ClosedForm;

    OptionType type_{};
    double sign_{};
    double spot_{};
    double rate_{};
    double dividend_yield_{};
    double expiry_{};
    double sqrt_expiry_{};
    double spot_discount_{};    ///< e^{-qT}.
    double discounted_spot_{};
    double discounted_strike_{};
    double log_moneyness_{};
    bool nothing_against_nothing_{};  ///< S == 0 and K == 0.
};

/// The closed form at one point: validated once, computed once, and read by
/// as many of the seven outputs as the caller wants.
class ClosedForm {
public:
    /// Throws `std::invalid_argument` exactly where `require_valid` does.
    ClosedForm(const EuropeanVanilla& option, const BlackScholesMarket& market);

    [[nodiscard]] double price() const noexcept;
    [[nodiscard]] double delta() const noexcept;
    [[nodiscard]] double gamma() const noexcept;
    [[nodiscard]] double vega() const noexcept;
    [[nodiscard]] double theta() const noexcept;
    [[nodiscard]] double rho() const noexcept;
    [[nodiscard]] double dividend_rho() const noexcept;

    /// All seven.
    [[nodiscard]] PriceAndGreeks price_and_greeks() const noexcept;

private:
    friend class ClosedFormQuote;

    ClosedForm(const ClosedFormQuote& quote, double vol);

    // Everything the seven outputs are built from. Two of them are unbounded
    // somewhere on the closed domain, and both singularities live here rather
    // than in the formulas that read them: `gamma_` divides by S and by the
    // total volatility, and `decay_` — theta's diffusion term — divides by
    // sqrt(T). Keeping the limits in the constructor means the seven accessors
    // are the formulas of `golden/SCHEMA.md` verbatim, with no branch in sight.
    double sign_{};               ///< w: +1 for a call, -1 for a put.
    double expiry_{};             ///< T.
    double rate_{};               ///< r.
    double dividend_yield_{};     ///< q.
    double spot_discount_{};      ///< e^{-qT}.
    double discounted_spot_{};    ///< S e^{-qT}.
    double discounted_strike_{};  ///< K e^{-rT}.
    double n1_{};                 ///< N(w d1).
    double n2_{};                 ///< N(w d2).
    double gamma_{};              ///< d2V/dS2. Type-independent.
    double vega_{};               ///< dV/dsigma. Type-independent.
    double decay_{};              ///< -S e^{-qT} phi(d1) sigma / (2 sqrt(T)). Type-independent.
};

}  // namespace touchstone
