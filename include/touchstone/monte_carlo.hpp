// European vanillas by Monte Carlo: the second of the three ways they are priced.
//
// Constitution I20 wants closed form, Monte Carlo and finite differences to
// agree. T1 built the first; this is the second, and the point of it is not
// that it is a better way to price a European call — it is not, the closed form
// is exact — but that it is an independent one. A discretisation, a discount
// factor or a payoff misread the same way twice is a bug two agreeing methods
// would hide; misread once, it shows up here as a disagreement in standard
// errors, which is a number rather than an opinion.
//
// Every path is drawn from the shared generator of `docs/rng.md`, so a demo in
// the browser and a test here can price the same option from the same seed and
// get the same number.

#pragma once

#include <touchstone/black_scholes.hpp>

#include <cstddef>
#include <cstdint>
#include <span>

namespace touchstone {

/// How the terminal spot is produced from the normals.
enum class Scheme {
    /// The terminal law itself, sampled exactly: one normal per path, and
    /// `S_T = S exp((r - q - sigma^2/2) T + sigma sqrt(T) Z)`. There is no
    /// discretisation error at all — the only error is sampling error, which
    /// the standard error measures.
    ExactTerminal,

    /// The SDE stepped in `steps` equal pieces:
    /// `S_(k+1) = S_k (1 + (r - q) dt + sigma sqrt(dt) Z_k)`. Wrong on purpose,
    /// by an amount that shrinks with dt at a rate the tests pin down. This is
    /// the scheme the tutorial's D4 shows next to the exact one, and the reason
    /// it is in the library rather than only in the demo is that the rate it
    /// converges at is a claim, and claims need tests (I1).
    EulerMaruyama,
};

/// What to run. Defaults price a European vanilla to about a cent of standard
/// error at typical parameters.
struct MonteCarloSettings {
    /// Seed for `Xoshiro128SS`. Same seed, same result, always (I6).
    std::uint32_t seed{1};

    /// Total paths, including antithetic partners. Must be even when
    /// `antithetic` is set, because a partner without its path is not a sample.
    std::size_t paths{1u << 15};

    Scheme scheme{Scheme::ExactTerminal};

    /// Steps per path. Read only by `EulerMaruyama`.
    std::size_t steps{1};

    /// Draw each path's normals once and use them again negated. The estimator
    /// stays unbiased — `-Z` is as standard normal as `Z` — and for a payoff
    /// that is monotone in the terminal spot, which a vanilla's is, the two
    /// halves are negatively correlated, so the pair mean varies less than two
    /// independent paths would.
    ///
    /// The sampling unit is then the *pair*, not the path, and the standard
    /// error is computed from pair means. Computing it from the paths instead
    /// would ignore the very correlation the technique creates and report an
    /// error bar that is too small — the failure mode where a variance
    /// reduction makes the answer look better than it is.
    bool antithetic{false};
};

/// The estimate and what is known about how good it is.
struct MonteCarloResult {
    /// Mean discounted payoff.
    ///
    /// Never a NaN, for any input `monte_carlo` accepts — the promise
    /// `black_scholes.hpp` makes for the closed form, kept here too, with the
    /// one extra condition on the domain that `monte_carlo` states below.
    ///
    /// It may be infinite, which is a different thing: a path whose discounted
    /// payoff overflows a double saturates the estimate, and the standard error
    /// beside it is infinite too. An infinity is a number that compares
    /// correctly against a tolerance, where a NaN compares false against every
    /// test a caller could write. What reaches one is a growth factor
    /// `exp((r - q) T + sigma sqrt(T) z)` that overflows — driven by `(r - q) T`
    /// above about 709, or by a total volatility large enough that an ordinary
    /// draw of `z` gets there — on a spot large enough to carry it.
    double price{};

    double price_standard_error{};   ///< Standard error of that mean. Never hidden (I20).
    double delta{};                  ///< Pathwise dV/dS, per 1.00 of spot. Never a NaN either.
    double delta_standard_error{};   ///< Standard error of the delta.

    std::size_t paths{};             ///< Paths run, partners included.
    std::size_t samples{};           ///< Independent sampling units: pairs when antithetic, else paths.

    /// Paths that finished with a payoff above zero. The honest reader of a
    /// standard error: a deep out-of-the-money option whose every path expired
    /// worthless has an estimate of zero and a standard error of zero, and
    /// neither number means what it appears to. The tests use this to decide
    /// where a t-statistic is worth computing.
    std::size_t in_the_money{};
};

/// Throws `std::invalid_argument` if the settings cannot be run: no paths, an
/// odd path count with antithetics, or no steps under Euler-Maruyama.
void require_valid(const MonteCarloSettings& settings);

/// Price, standard error, pathwise delta and its standard error, from one sweep.
///
/// The option and market are validated by `require_valid` in
/// `black_scholes.hpp` — the same domain the closed form prices on, so that a
/// comparison between the two is a comparison and not an accident — and by one
/// condition of this header's own: the total variance `(sigma sqrt(T))^2` must
/// be representable. The closed form never forms it, so it does not check it,
/// and between the two bounds every path would be `exp(-inf + inf)`. Throws
/// `std::invalid_argument` on an input inside the closed form's domain and
/// outside this one, rather than returning the NaN that would result.
[[nodiscard]] MonteCarloResult monte_carlo(const EuropeanVanilla& option,
                                           const BlackScholesMarket& market,
                                           const MonteCarloSettings& settings);

// --- The pieces, one path at a time -----------------------------------------
//
// Public because the tests drive both schemes from the *same* normals to
// measure the discretisation error alone, which is impossible from the outside
// if the only entry point runs a whole sweep and owns its generator.

/// `exp((r - q - sigma^2/2) T + sigma sqrt(T) z)` — the factor the spot grows by
/// along one path, for one standard normal `z`. It does not depend on the spot,
/// which is the fact the pathwise delta below is built on.
[[nodiscard]] double terminal_growth_exact(const BlackScholesMarket& market,
                                           double expiry_years,
                                           double z) noexcept;

/// The same growth factor under Euler-Maruyama, over `normals.size()` equal
/// steps of `T / n`: the product of `1 + (r - q) dt + sigma sqrt(dt) Z` over the
/// steps.
///
/// It may be negative, and is not clipped. A step's factor is negative whenever
/// its `Z` is far enough below zero, and a scheme that quietly floored the spot
/// at zero would converge at a different rate than the one the tests claim. The
/// payoff handles a negative spot correctly, so the honest thing is to let it
/// through.
[[nodiscard]] double terminal_growth_euler(const BlackScholesMarket& market,
                                           double expiry_years,
                                           std::span<const double> normals) noexcept;

/// `S` times the growth factor: the terminal spot itself. Zero spot in, zero
/// spot out — zero is an absorbing state for geometric Brownian motion, and
/// taking it as a special case rather than as a multiplication keeps the one
/// input where the growth factor can overflow from returning `0 * inf`.
[[nodiscard]] double terminal_spot(const BlackScholesMarket& market, double growth) noexcept;

/// `S exp((r - q - sigma^2/2) T + sigma sqrt(T) z)`, the exact terminal spot for
/// one standard normal. Exact in the sense that matters: the law of the result
/// is the law of `S_T`, with no discretisation between them.
[[nodiscard]] double terminal_spot_exact(const BlackScholesMarket& market,
                                         double expiry_years,
                                         double z) noexcept;

/// The same, under Euler-Maruyama.
[[nodiscard]] double terminal_spot_euler(const BlackScholesMarket& market,
                                         double expiry_years,
                                         std::span<const double> normals) noexcept;

/// `max(w (S_T - K), 0)`, undiscounted.
[[nodiscard]] double payoff(const EuropeanVanilla& option, double terminal_spot) noexcept;

/// The pathwise derivative of the payoff with respect to the *initial* spot,
/// undiscounted: `w 1{w (S_T - K) > 0} dS_T/dS`, where `dS_T/dS` is the growth
/// factor the path was built from.
///
/// It is that simple because the terminal spot is proportional to the initial
/// one under both schemes — every path is `S` times a factor that does not
/// depend on `S` — so differentiating the path and then the payoff is legal
/// wherever the payoff is differentiable, which is everywhere except the single
/// point `S_T = K`. That point has probability zero, so the estimator is
/// unbiased; what it is not is a difference of two prices, which is why it
/// carries no bump size and no cancellation.
///
/// The derivative is the growth factor rather than `S_T / S`, which is the same
/// number wherever `S` is positive and is defined where `S` is not. At a spot of
/// zero — inside the domain the closed form prices on, and a row
/// `tests/test_limits.cpp` sweeps — the ratio is `0 / 0`, and a put there has a
/// perfectly good delta of `-e^{-qT}` that the ratio returns a NaN for.
///
/// Pass a discounted growth factor and the result is the discounted derivative,
/// since the discount goes through the indicator untouched. That is how
/// `monte_carlo` uses it, and it is not a trick: `e^{-rT}` times a growth factor
/// that has overflowed is `0 * inf`, while the two combined in one exponent —
/// `exp(-qT - sigma^2 T/2 + sigma sqrt(T) z)` — is an ordinary number.
[[nodiscard]] double pathwise_payoff_delta(const EuropeanVanilla& option,
                                           double terminal_spot,
                                           double growth) noexcept;

/// The growth factor with the discount folded into its exponent: `e^{-rT}` times
/// what `terminal_growth_exact` returns, computed as one exponential rather than
/// as a product of two numbers that can be zero and infinity.
[[nodiscard]] double discounted_growth_exact(const BlackScholesMarket& market,
                                             double expiry_years,
                                             double z) noexcept;

}  // namespace touchstone
