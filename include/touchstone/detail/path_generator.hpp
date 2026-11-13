// The generator behind `touchstone/paths.hpp` and `monte_carlo`: the shared
// random-number generator and one scheme's step, held together.
//
// A path API and a Monte Carlo engine both turn a stream of normals into
// geometric Brownian motion, and this is the one place that does it. The step
// is a factor `S_(k+1) / S_k` computed from one normal; a path is those factors
// multiplied up from a starting value; and a Monte Carlo sample is the same
// thing read only at its end, from a starting value of one — the growth factor,
// which the pathwise delta needs — and, under Euler, from the discount factor
// alongside it, both carried through one walk; then replayed with its normals
// negated for an antithetic partner.
//
// Internal rather than public: the public face is `touchstone/paths.hpp` and the
// per-path functions of `touchstone/monte_carlo.hpp`.

#pragma once

#include <touchstone/detail/scales.hpp>
#include <touchstone/paths.hpp>
#include <touchstone/rng.hpp>

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <span>

namespace touchstone::detail {

/// One step of geometric Brownian motion under one scheme: the factor the value
/// is multiplied by, from one standard normal.
///
/// Defined here, in the header, because `factor` is the body of every walk's
/// loop: a definition in a source file is a call across translation units at
/// every step, which the compiler can neither inline nor lift the scheme's test
/// out of.
class GbmStep {
public:
    /// `drift` is `mu`, `vol` is `sigma`, `dt` the step. Nothing is checked: the
    /// callers' `require_valid` has established that `mu dt` and
    /// `(sigma sqrt(dt))^2` are representable.
    GbmStep(Scheme scheme, double drift, double vol, double dt) noexcept
        : scheme_(scheme),
          dt_(dt),
          drift_term_(scheme == Scheme::ExactTerminal ? log_drift_time(drift, vol, dt)
                                                      : drift_time(drift, dt)),
          diffusion_(total_volatility(vol, dt))
    {
    }

    /// `exp((mu - sigma^2/2) dt + sigma sqrt(dt) z)` exactly, or
    /// `1 + mu dt + sigma sqrt(dt) z` under Euler-Maruyama.
    [[nodiscard]] double factor(double z) const noexcept
    {
        if (scheme_ == Scheme::ExactTerminal) {
            return std::exp(drift_term_ + diffusion_ * z);
        }
        return 1.0 + drift_term_ + diffusion_ * z;
    }

    /// The step's length.
    [[nodiscard]] double dt() const noexcept { return dt_; }

private:
    Scheme scheme_;
    double dt_;
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

/// `values`, each advanced by the same factor at every step, one step per
/// normal, each normal multiplied by `sign`, with `visit(k, values)` called on
/// the values after the k-th step. The one walk behind a path written out, a
/// path read only at its end, and a Monte Carlo path that carries its growth
/// factor and its discounted growth factor together: a step's factor is formed
/// once, however many values it moves, and each value is multiplied by it in
/// the order the values are given. The antithetic partner of a path is the same
/// path with `sign = -1`, which is why the sign is here rather than in a second
/// buffer holding the negated draws.
template <std::size_t N, class Visit>
std::array<double, N> walk(const GbmStep& step,
                           std::array<double, N> values,
                           std::span<const double> normals,
                           double sign,
                           Visit visit) noexcept
{
    for (std::size_t k = 0; k < normals.size(); ++k) {
        const double factor = step.factor(sign * normals[k]);
        for (double& value : values) {
            value = advance(value, factor);
        }
        visit(k, values);
    }
    return values;
}

/// The values at the end of the walk, and nothing along the way.
template <std::size_t N>
[[nodiscard]] std::array<double, N> grow(const GbmStep& step,
                                         const std::array<double, N>& from,
                                         std::span<const double> normals,
                                         double sign) noexcept
{
    return walk(step, from, normals, sign, [](std::size_t, const std::array<double, N>&) {});
}

/// The shared generator, and the scheme its normals are stepped by.
class PathGenerator {
public:
    PathGenerator(std::uint32_t seed, const GbmStep& step) noexcept;

    /// The next `normals.size()` normals of the stream, in order. In the header
    /// for the reason `GbmStep::factor` is: under the exact scheme a path is
    /// one normal, so this is called once for every step.
    void draw(std::span<double> normals) noexcept
    {
        for (double& z : normals) {
            z = rng_.next_normal();
        }
    }

    /// `from` grown through the steps these normals describe. See `grow`.
    template <std::size_t N>
    [[nodiscard]] std::array<double, N> grow(const std::array<double, N>& from,
                                             std::span<const double> normals,
                                             double sign) const noexcept
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
