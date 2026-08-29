// Standard normal density and distribution.
//
// Shared by everything that follows: the closed form here at T1, the inverse
// transform the Monte Carlo will need at T2, the implied-vol solver at T3.

#pragma once

#include <cmath>

namespace touchstone {

/// phi(x) — the standard normal probability density.
[[nodiscard]] inline double norm_pdf(double x) noexcept
{
    constexpr double inv_sqrt_two_pi = 0.3989422804014326779399460599344;  // 1/sqrt(2*pi)
    return inv_sqrt_two_pi * std::exp(-0.5 * x * x);
}

/// N(x) — the standard normal cumulative distribution, as 0.5 * erfc(-x/sqrt(2)).
///
/// The route is `std::erfc` by decision B3, and the reason is the left tail.
/// Computing N(-x) as 1 - N(x) subtracts two numbers that agree in every digit
/// that matters: at x = -10 the true value is 7.6e-24 and the subtraction
/// returns exactly zero. erfc exists precisely to keep that tail, so a deep
/// out-of-the-money option gets a small number rather than nothing at all.
/// `golden/SCHEMA.md` states the same thing about reproducing the golden file.
[[nodiscard]] inline double norm_cdf(double x) noexcept
{
    constexpr double inv_sqrt_two = 0.7071067811865475244008443621048;  // 1/sqrt(2)
    return 0.5 * std::erfc(-x * inv_sqrt_two);
}

}  // namespace touchstone
