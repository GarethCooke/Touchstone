// The volatility that reproduces a price: Newton, with Brent behind it.
//
// Every other entry point in this library maps a volatility to a price. This one
// runs the map backwards, which is the direction the market actually quotes in —
// an option has a price, and the volatility is what the price is restated as so
// that two strikes can be compared. Tech-decision B3 fixes the method: Newton,
// because vega is in hand at no extra cost and Newton on a smooth monotone
// function converges quadratically; Brent behind it, because "converges
// quadratically" is a statement about the inputs Newton likes, and a solver in a
// library has to answer on the others too.
//
// The map is invertible where it is worth inverting. Price is strictly
// increasing in the volatility wherever vega is positive, from the discounted
// forward intrinsic at sigma = 0 to an asymptote at sigma = infinity, so a
// target strictly between those two has exactly one solution. Outside them there
// is none, and `require_valid` says so rather than returning a number.
//
// Where vega is small the inverse exists and is useless: an option whose price
// moves by 1e-17 across a whole volatility point has a well-defined implied
// volatility that no finite-precision price can pin down. `ImpliedVolResult`
// carries the vega it finished at so that a caller can tell the two situations
// apart, and `tests/test_implied_vol.cpp` uses it to say which rows of the
// golden file have an identifiable volatility and which only have a price.

#pragma once

#include <touchstone/black_scholes.hpp>

#include <cstddef>

namespace touchstone {

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

struct ImpliedVolSettings {
    /// Stop when `|price(vol) - target|` falls to this, **times the option's own
    /// price scale** — see `price_scale` below.
    ///
    /// Relative rather than absolute, because the closed form's price is the
    /// difference of two numbers of that scale and cannot be computed to better
    /// than a few units in its last place, whatever the price itself is. An
    /// absolute tolerance would be unreachable on a spot of 1000 and pointlessly
    /// loose on a spot of 0.01, and the first of those is a solver that never
    /// converges for a reason nothing in its output would explain.
    ///
    /// The default is about forty-five ulps of that scale: as tight as the
    /// arithmetic underneath supports, and six orders of magnitude tighter than
    /// the 1e-8 round trip the roadmap asks for.
    double price_tolerance{1e-14};

    /// The largest volatility the search will consider, and the top of Brent's
    /// bracket. A target above the price at this volatility is refused by
    /// `require_valid` with this number in the message, because the honest
    /// answer is "not within the range you gave me" rather than a silent
    /// non-convergence.
    double max_vol{10.0};

    /// Newton steps before handing over to Brent.
    ///
    /// Newton's budget alone. Brent's is fixed inside the solver at what
    /// bisection would need on `[0, max_vol]` plus room for the interpolation
    /// steps it inserts, because a fallback that can run out of budget is not a
    /// fallback: `require_valid` has already established the bracket, so Brent
    /// will find the root, and the only question is whether it is allowed to.
    /// Setting this to 1 therefore does not cripple the solver — it routes every
    /// call through Brent, which is how `tests/test_implied_vol.cpp` exercises
    /// the path that no row of the golden file reaches on its own.
    std::size_t max_iterations{64};
};

/// Which method produced the answer.
enum class ImpliedVolMethod {
    /// Newton on vega, from the Manaster-Koehler seed.
    Newton,
    /// Brent on `[0, max_vol]`, after Newton left the bracket, stalled, or ran
    /// out of vega to divide by.
    Brent,
    /// The target was exactly the price at zero volatility, which is the
    /// discounted forward intrinsic. No iteration was needed and none was run.
    Exact,
};

struct ImpliedVolResult {
    double vol{};

    /// `price(vol) - target`. Signed, and reported rather than asserted: a
    /// caller comparing implied volatilities across strikes needs to know which
    /// of them were solved to the tolerance and which were stopped by the
    /// iteration limit.
    double price_residual{};

    /// `dV/dsigma` at the answer. The identifiability of the result, in one
    /// number: the volatility is pinned down to about
    /// `price_tolerance / vega`, so a vega of 1e-16 means the price says
    /// nothing about the volatility, however small the residual is.
    double vega{};

    std::size_t iterations{};
    ImpliedVolMethod method{ImpliedVolMethod::Newton};

    /// Whether the residual reached `price_tolerance`. False means the answer is
    /// the best the iteration limit allowed, not that it is wrong.
    bool converged{};
};

/// `max(S e^{-qT}, K e^{-rT})` — the scale at which this option's price is
/// computed, and therefore the scale at which it is accurate.
///
/// The closed form is `w (S e^{-qT} N(w d1) - K e^{-rT} N(w d2))`: a difference
/// of two numbers of this size, so a few units in the last place of *this* is
/// the resolution of any price, including a price of 1e-19. It is what
/// `ImpliedVolSettings::price_tolerance` is measured in, and what decides
/// whether a target below the zero-volatility price is an arbitrage or a
/// rounding.
[[nodiscard]] double price_scale(const EuropeanVanilla& option, const QuotedMarket& market);

/// The price at zero volatility: `max(w (S e^{-qT} - K e^{-rT}), 0)`, the
/// discounted intrinsic value of the forward, and the lower end of the range of
/// prices any volatility can produce.
[[nodiscard]] double lowest_price(const EuropeanVanilla& option, const QuotedMarket& market);

/// The price as the volatility grows without bound: `S e^{-qT}` for a call,
/// `K e^{-rT}` for a put. Approached, never reached — a target equal to it has
/// no finite solution.
[[nodiscard]] double highest_price(const EuropeanVanilla& option, const QuotedMarket& market);

/// Throws `std::invalid_argument` if this price cannot be inverted.
///
/// The option and market are validated by `require_valid` in `black_scholes.hpp`
/// at a volatility of zero and again at `max_vol`, so the domain is the closed
/// form's at both ends of the search. Then:
///
///   - the target must be finite;
///   - it must be at least `lowest_price`, give or take a few ulps of
///     `price_scale` — below that it is an arbitrage, not a quote, and no
///     volatility produces it. The allowance is not slack: for an option deep
///     enough in the money, the price at a volatility of 30% and the price at
///     zero are the *same double*, and which side of the other a given rounding
///     lands on says nothing. A target inside the allowance is answered with a
///     volatility of zero and a vega that shows the answer for what it is;
///   - it must be below `highest_price` — at or above that, no finite volatility
///     produces it either;
///   - and it must be at most the price at `max_vol`, which is a statement about
///     the search rather than about the market, and says so.
void require_valid(const EuropeanVanilla& option,
                   const QuotedMarket& market,
                   double target_price,
                   const ImpliedVolSettings& settings);

/// Solve `price(vol) = target_price`.
///
/// Newton is seeded at Manaster and Koehler's (1982) starting point,
/// `sqrt(2 |ln(F/K)| / T)` with `F` the forward — the volatility at which vega
/// is largest, and from which they proved Newton converges monotonically for a
/// call. At the money that expression is zero, where their argument does not
/// apply and the price is nearly linear in the volatility anyway; there the seed
/// is Brenner and Subrahmanyam's (1988) inversion of that linear relation,
/// `target / (0.3989 S e^{-qT} sqrt(T))`. The seed is the larger of the two,
/// which is the one that is meaningful in each case.
///
/// Newton hands over to Brent on `[0, max_vol]` if a step leaves that interval,
/// if vega is not positive and finite, or if the residual stops shrinking. Brent
/// always finishes, because `require_valid` has already established that the
/// target is bracketed there.
[[nodiscard]] ImpliedVolResult implied_vol(const EuropeanVanilla& option,
                                           const QuotedMarket& market,
                                           double target_price,
                                           const ImpliedVolSettings& settings = {});

}  // namespace touchstone
