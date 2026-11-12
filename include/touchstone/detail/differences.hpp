// Central differences, written once: the bumped Greeks take them across bumped
// prices and the grid across neighbouring nodes.

#pragma once

namespace touchstone::detail {

/// `(f(x + h) - f(x - h)) / 2h`.
[[nodiscard]] inline double central_first(double up, double down, double h) noexcept
{
    return (up - down) / (2.0 * h);
}

/// `(f(x + h) - 2 f(x) + f(x - h)) / h^2`.
[[nodiscard]] inline double central_second(double up, double mid, double down, double h) noexcept
{
    return (up - 2.0 * mid + down) / (h * h);
}

}  // namespace touchstone::detail
