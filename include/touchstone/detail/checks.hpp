// The two shapes of domain check every entry point in the library makes on a
// scalar input, written once.
//
// Both are true only for a finite number, so a NaN fails them as it should:
// every comparison with a NaN is false, and `std::isfinite` rules out the
// infinities that would otherwise pass `x >= 0`.

#pragma once

#include <cmath>

namespace touchstone::detail {

/// Finite and `>= 0`: a spot, a strike, a volatility, an expiry.
[[nodiscard]] inline bool is_finite_non_negative(double x) noexcept
{
    return std::isfinite(x) && x >= 0.0;
}

/// Finite and `> 0`: a bump size, a tolerance, the top of a search range.
[[nodiscard]] inline bool is_finite_positive(double x) noexcept
{
    return std::isfinite(x) && x > 0.0;
}

}  // namespace touchstone::detail
