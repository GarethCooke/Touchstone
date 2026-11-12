// The generator behind `touchstone/paths.hpp` and `monte_carlo`: the shared
// random-number generator and one scheme's step, held together.
//
// A path API and a Monte Carlo engine both turn a stream of normals into
// geometric Brownian motion, and this is the one place that does it. The step
// is a factor `S_(k+1) / S_k` computed from one normal; a path is those factors
// multiplied up from a starting value; and a Monte Carlo sample is the same
// thing read only at its end, from a starting value of one — the growth factor,
// which the pathwise delta needs — and replayed with its normals negated for an
// antithetic partner.
//
// Internal rather than public: the public face is `touchstone/paths.hpp` and the
// per-path functions of `touchstone/monte_carlo.hpp`.

#pragma once

#include <touchstone/paths.hpp>
#include <touchstone/rng.hpp>

#include <cstdint>
#include <span>

namespace touchstone::detail {

/// One step of geometric Brownian motion under one scheme: the factor the value
/// is multiplied by, from one standard normal.
class GbmStep {
public:
    /// `drift` is `mu`, `vol` is `sigma`, `dt` the step. Nothing is checked: the
    /// callers' `require_valid` has established that `mu dt` and
    /// `(sigma sqrt(dt))^2` are representable.
    GbmStep(Scheme scheme, double drift, double vol, double dt) noexcept;

    /// `exp((mu - sigma^2/2) dt + sigma sqrt(dt) z)` exactly, or
    /// `1 + mu dt + sigma sqrt(dt) z` under Euler-Maruyama.
    [[nodiscard]] double factor(double z) const noexcept;

private:
    Scheme scheme_;
    double drift_term_;  ///< `mu dt - (sigma sqrt(dt))^2 / 2` exactly; `mu dt` under Euler.
    double diffusion_;   ///< `sigma sqrt(dt)`.
};

/// The next value of a path: this one times a step's factor, except that zero is
/// absorbing. A process at zero stays there, and a factor of zero takes it there
/// whatever it was — which is also the one product, an infinity times a zero,
/// that would otherwise be a NaN.
[[nodiscard]] inline double advance(double current, double factor) noexcept
{
    return (current == 0.0 || factor == 0.0) ? 0.0 : current * factor;
}

/// `from`, advanced by one step per normal, each normal multiplied by `sign` —
/// the antithetic partner of a path is the same path with `sign = -1`, which is
/// why this exists rather than a second buffer holding the negated draws.
[[nodiscard]] double grow(const GbmStep& step,
                          double from,
                          std::span<const double> normals,
                          double sign) noexcept;

/// The shared generator, and the scheme its normals are stepped by.
class PathGenerator {
public:
    PathGenerator(std::uint32_t seed, Scheme scheme, double drift, double vol, double dt) noexcept;

    /// The next `normals.size()` normals of the stream, in order.
    void draw(std::span<double> normals) noexcept;

    /// `from` grown through the steps these normals describe. See `grow`.
    [[nodiscard]] double grow(double from, std::span<const double> normals, double sign) const noexcept
    {
        return detail::grow(step_, from, normals, sign);
    }

    /// `W`: `path[0] = 0`, then one normal per step, times `sqrt(dt)`. The
    /// scheme and the process play no part.
    void write_brownian(std::span<double> path) noexcept;

    /// `S` from `path[0] = spot`, one normal per step through the scheme.
    void write_gbm(double spot, std::span<double> path) noexcept;

private:
    Xoshiro128SS rng_;
    GbmStep step_;
    double sqrt_dt_;
};

}  // namespace touchstone::detail
