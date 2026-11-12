// Bumping the finite-difference grid: the grid as a pricer, and the bump sizes
// a pricer with a discretisation error of its own wants.
//
// `BumpSizes`' defaults are measured for a pricer accurate to machine
// precision. A grid is accurate to about 1e-6 relative, and `bump_greeks.hpp`
// works out why that moves the best bump up by several hundred times. These are
// the sizes the tests bump the grid at.

#pragma once

#include <touchstone/black_scholes.hpp>
#include <touchstone/bump_greeks.hpp>
#include <touchstone/pde.hpp>

namespace touchstone::testing {

[[nodiscard]] inline BumpSizes grid_bumps() noexcept
{
    BumpSizes wide{};
    wide.spot_relative = 1e-3;
    wide.spot_relative_for_gamma = 1e-2;
    wide.vol_absolute = 1e-3;
    wide.rate_absolute = 1e-3;
    wide.dividend_yield_absolute = 1e-3;
    wide.expiry_absolute = 1e-3;
    return wide;
}

/// The grid at `settings`, as a pricer `bump_greeks` can difference.
[[nodiscard]] inline auto grid_pricer(const PdeSettings& settings)
{
    return [settings](const EuropeanVanilla& option, const BlackScholesMarket& market) {
        return crank_nicolson(option, market, settings).price;
    };
}

}  // namespace touchstone::testing
