// Greeks by bumping and revaluing: the derivative as a difference quotient.
//
// The library has Greeks two ways, analytic and by bump-and-revalue, and this is
// the second of them. It is the slow one, the inaccurate one, and the one that
// works: it needs nothing from the pricer but a price, so it gives a vega for a
// method that has no formula for vega, and it is how the finite-difference
// grid's sensitivities and the Monte Carlo's are obtained at all.
//
// That makes it two things at once. As a tool it extends every pricer in the
// library. As a test it is an independent second opinion on the analytic Greeks
// of `black_scholes.hpp`, which are seven hand-transcribed formulas and
// therefore seven chances to have transcribed one wrongly — a difference quotient
// of the *price* cannot repeat a mistake made in a derivative.
//
// ## Choosing the bump
//
// A central difference has two errors pulling in opposite directions. Truncation
// falls as the bump shrinks:
//
//     (f(x+h) - f(x-h)) / 2h  =  f'(x) + (h^2 / 6) f'''(x) + ...
//
// Cancellation grows as it shrinks, because the two prices agree in more and
// more digits and the subtraction keeps only what is left: about `eps |f| / h`.
// Balancing them puts the best bump at `h ~ eps^(1/3)`, about 6e-6 in relative
// terms, for an accuracy of about `eps^(2/3)`, or 4e-11 relative.
//
// The second difference balances differently. Its truncation is `(h^2/12) f''''`
// and its cancellation is `4 eps |f| / h^2`, so the best bump is
// `h ~ eps^(1/4)`, about 1.2e-4, and the best accuracy only `eps^(1/2)`, about
// 1.5e-8 relative. **Gamma therefore wants a bump much larger than delta's**,
// and using one bump for both costs an order of magnitude in one of them. Hence
// two spot bumps below, and hence `BumpSizes` at all: these numbers are a
// property of the arithmetic, not of the option, and they should be visible
// rather than buried.
//
// The defaults are not the theory's numbers but measured ones. Each bump was
// swept over four decades against the analytic Greek across a grid of 864
// options — `tests/test_bump_greeks.cpp` reruns a coarser version of that sweep
// and asserts the shape — and set to the size where the worst scaled error over
// the grid was smallest. The two errors are visible on either side of each
// optimum: below it the worst error grows as the bump shrinks, above it as
// `h^2`. The floors reached are 3e-10 for delta, 2e-8 for gamma and 1e-8 for
// vega, which is roughly the `eps^(2/3)` and `eps^(1/2)` the analysis predicts.
//
// **These sizes are for a pricer accurate to machine precision.** A pricer whose
// own error is `d` — a finite-difference grid at around 1e-6 relative, a Monte
// Carlo at 1e-3 — has that in place of `eps` in the balance above, so its best
// bump is `d^(1/3)` rather than `eps^(1/3)`: several hundred times larger for the
// grid, and larger again for the Monte Carlo.
//
// Where that bites is the **second** difference, and only there. A first
// difference divides by `h`, so a pricer whose error varies smoothly with the
// input — which the grid's does, because it rebuilds itself around each bumped
// spot — loses almost nothing: the same bias appears in both legs and subtracts
// out, and `tests/test_bump_greeks.cpp` measures delta off the grid as flat to
// within a factor of five across four decades of bump size. Gamma divides by
// `h^2`, and there the same measurement shows a relative error of 26,000 at a
// bump of 1e-9, falling to 2e-5 at 1e-2. Nine orders of magnitude, on the same
// pricer, from the bump size alone.

#pragma once

#include <touchstone/black_scholes.hpp>
#include <touchstone/detail/callable.hpp>
#include <touchstone/detail/differences.hpp>

#include <array>
#include <cstddef>

namespace touchstone {

/// Anything that prices a European vanilla in a market: callable as
/// `double(const EuropeanVanilla&, const BlackScholesMarket&)`, or as anything
/// whose result converts to `double`.
template <class P>
concept VanillaPricer = detail::returns_double<P, const EuropeanVanilla&, const BlackScholesMarket&>;

/// How far to move each input. Relative for the spot, which ranges over orders
/// of magnitude; absolute for the rest, which are rates and times of order one
/// and can legitimately be zero.
struct BumpSizes {
    /// `dS = spot_relative * S`, for delta. Measured optimum; `eps^(1/3)` is 6e-6.
    double spot_relative{1e-6};

    /// `dS = spot_relative_for_gamma * S`, for gamma. Measured optimum;
    /// `eps^(1/4)` is 1.2e-4.
    double spot_relative_for_gamma{3e-5};

    double vol_absolute{1e-6};             ///< For vega.
    double rate_absolute{1e-6};            ///< For rho.
    double dividend_yield_absolute{1e-6};  ///< For dividend_rho.
    double expiry_absolute{1e-5};          ///< For theta, in years — about five minutes.
};

namespace detail {

/// The twelve points besides the base that a set of bump Greeks prices, in up-
/// and-down pairs. Delta and gamma each have their own pair, because they want
/// different spot bumps — see the note at the top of this file.
enum Bumped : std::size_t {
    DeltaUp,
    DeltaDown,
    GammaUp,
    GammaDown,
    VolUp,
    VolDown,
    RateUp,
    RateDown,
    YieldUp,
    YieldDown,
    Longer,
    Shorter,
    bumped_count,
};

struct BumpedPoint {
    EuropeanVanilla option;
    BlackScholesMarket market;
};

/// The bumped points, written once: `require_valid` checks every one of them
/// and `bump_greeks` prices every one of them, so the two cannot disagree about
/// which points those are.
struct Bumps {
    double delta_spot{};  ///< The absolute spot bump for delta.
    double gamma_spot{};  ///< The absolute spot bump for gamma.
    std::array<BumpedPoint, bumped_count> points{};
};

[[nodiscard]] Bumps bumps(const EuropeanVanilla& option,
                          const BlackScholesMarket& market,
                          const BumpSizes& sizes) noexcept;

}  // namespace detail

/// Throws `std::invalid_argument` if these bumps cannot be taken here.
///
/// Every bump is two-sided, so every bumped point has to be inside the closed
/// form's domain: a volatility or an expiry smaller than its own bump would go
/// negative, and a spot of zero has no relative bump at all. A one-sided
/// difference at those points is not offered, deliberately — it is first order,
/// its error is a hundred thousand times larger, and returning it under the same
/// name as the central difference would make the accuracy of the answer depend
/// on the input in a way nothing in the result would record.
void require_valid(const EuropeanVanilla& option,
                   const BlackScholesMarket& market,
                   const BumpSizes& sizes);

/// Price and all six Greeks, by central differences of `pricer`.
///
/// Thirteen calls: the base price, two for each of the six sensitivities, and
/// one extra pair for gamma's wider bump.
///
/// The domain checked is the closed form's. A `pricer` with a narrower one — the
/// finite-difference grid, which needs a positive spot and a positive total
/// volatility — must accept the bumped points itself; bumping is a small
/// perturbation, so in practice that means staying clear of its boundary.
///
/// `theta` is `dV/dt`, so it is minus the derivative with respect to the time
/// remaining: an option with more time left is worth more, and theta is
/// negative for the long position that watches it run out.
template <VanillaPricer Pricer>
[[nodiscard]] PriceAndGreeks bump_greeks(const EuropeanVanilla& option,
                                         const BlackScholesMarket& market,
                                         const BumpSizes& sizes,
                                         Pricer&& pricer)
{
    require_valid(option, market, sizes);

    const auto at = [&](const EuropeanVanilla& contract, const BlackScholesMarket& state) {
        return static_cast<double>(pricer(contract, state));
    };

    const double base = at(option, market);
    const detail::Bumps bumped = detail::bumps(option, market, sizes);
    std::array<double, detail::bumped_count> value{};
    for (std::size_t i = 0; i < value.size(); ++i) {
        value[i] = at(bumped.points[i].option, bumped.points[i].market);
    }

    const auto central = [&](detail::Bumped up, detail::Bumped down, double width) {
        return detail::central_first(value[up], value[down], width);
    };

    PriceAndGreeks out{};
    out.price = base;
    // Delta and gamma, from two bumps of different sizes. Sharing a bump would
    // cost an order of magnitude on one of them.
    out.delta = central(detail::DeltaUp, detail::DeltaDown, bumped.delta_spot);
    out.gamma = detail::central_second(value[detail::GammaUp], base, value[detail::GammaDown],
                                       bumped.gamma_spot);
    out.vega = central(detail::VolUp, detail::VolDown, sizes.vol_absolute);
    out.rho = central(detail::RateUp, detail::RateDown, sizes.rate_absolute);
    out.dividend_rho = central(detail::YieldUp, detail::YieldDown, sizes.dividend_yield_absolute);
    // Minus, because theta is the derivative with respect to time passing and
    // the bump is on time remaining.
    out.theta = -central(detail::Longer, detail::Shorter, sizes.expiry_absolute);
    return out;
}

/// The same, over the closed form — which is the comparison `tests/test_bump_greeks.cpp`
/// makes against the analytic Greeks, and the cheapest way to ask for a bumped
/// Greek at all.
[[nodiscard]] PriceAndGreeks bump_greeks(const EuropeanVanilla& option,
                                         const BlackScholesMarket& market,
                                         const BumpSizes& sizes = {});

}  // namespace touchstone
