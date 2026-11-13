// The contract: what was agreed, independent of what the market is doing.
//
// A vanilla option is a strike, an expiry and a direction, and it is one of two
// contracts according to when the holder may exercise it. The exercise style is
// part of the *type*, not a field and not a solver setting, because the two are
// different contracts with different values: a function that can only price one
// of them should refuse the other at compile time rather than price it as the
// wrong thing. Every method in the library prices a European vanilla; only the
// finite-difference grid prices an American one.
//
// The fields are written once, in `Vanilla`, and both contracts are that
// template. Converting one to the other is possible and deliberately explicit —
// `with_exercise` — so that it is something a caller writes rather than
// something that happens to them.

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

/// When the holder may exercise.
enum class Exercise {
    /// At expiry only. The closed form prices this contract, which is what makes
    /// it the one every method in the library can be checked against exactly.
    European,

    /// At any time up to expiry. The value function is then the solution of a
    /// linear complementarity problem — the pricing equation holds where holding
    /// is optimal, the value equals the payoff where exercising is, and the two
    /// regions are separated by a free boundary the solution finds for itself.
    ///
    /// There is no closed form for this, and QuantLib is the oracle for it as for
    /// everything else: `golden/american_vanilla.json` carries reference values
    /// from an independent lattice, and `golden/AMERICAN-SCHEMA.md` says what
    /// they are worth. Two exact statements hold it down besides — an American
    /// call on an underlying with no dividend yield and a non-negative rate is
    /// worth exactly its European counterpart, and every American value is at
    /// least its European one and at least its intrinsic value.
    American,
};

/// A vanilla option with exercise style `E`.
template <Exercise E>
struct Vanilla {
    double strike{};        ///< K >= 0.
    double expiry_years{};  ///< T >= 0, in years on the curve's own day count.
    OptionType type{OptionType::Call};
};

using EuropeanVanilla = Vanilla<Exercise::European>;
using AmericanVanilla = Vanilla<Exercise::American>;

/// The same strike, expiry and direction under the other exercise style.
///
/// For the comparisons that make an American price checkable at all — against
/// its European counterpart, which it can never be worth less than — and for
/// validating an American contract against the domain the European one is
/// priced on, which the exercise style does not change.
template <Exercise To, Exercise From>
[[nodiscard]] constexpr Vanilla<To> with_exercise(const Vanilla<From>& option) noexcept
{
    return Vanilla<To>{option.strike, option.expiry_years, option.type};
}

/// `max(w (S - K), 0)`: what exercising at spot `S` pays, undiscounted.
///
/// The one definition of the payoff. The Monte Carlo applies it to a terminal
/// spot, the grid to every node at expiry and, for an American contract, to
/// every node at every step as the value early exercise guarantees.
///
/// A negative spot is not rejected: an Euler-Maruyama path can end below zero,
/// and a put there is worth `K - S` like anywhere else.
template <Exercise E>
[[nodiscard]] constexpr double payoff(const Vanilla<E>& option, double spot) noexcept
{
    const double intrinsic = option_sign(option.type) * (spot - option.strike);
    return intrinsic > 0.0 ? intrinsic : 0.0;
}

}  // namespace touchstone
