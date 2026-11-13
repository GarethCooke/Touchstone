// A long forward contract's value and sensitivities, written out from its
// definition rather than from the closed form.
//
// Two tests need it. Put-call parity says a call less a put is this contract,
// field by field; and with no volatility or no time left, an option collapses
// to it, exercised or not. Both are second opinions on the closed form, so the
// contract is written from what it is: pay K at T for something worth
// F = S e^{-qT} today, with D = K e^{-rT}.

#pragma once

#include <touchstone/black_scholes.hpp>

#include <cmath>

namespace touchstone::testing {

///     price         F - D
///     delta         e^{-qT}
///     gamma         0
///     vega          0
///     theta         q F - r D
///     rho           T D
///     dividend_rho  -T F
[[nodiscard]] inline PriceAndGreeks forward_contract(const EuropeanVanilla& option,
                                                     const BlackScholesMarket& market)
{
    const double t = option.expiry_years;
    const double discounted_spot = market.spot * std::exp(-market.dividend_yield * t);
    const double discounted_strike = option.strike * std::exp(-market.rate * t);
    return PriceAndGreeks{
        discounted_spot - discounted_strike,
        std::exp(-market.dividend_yield * t),
        0.0,
        0.0,
        market.dividend_yield * discounted_spot - market.rate * discounted_strike,
        t * discounted_strike,
        -t * discounted_spot,
    };
}

}  // namespace touchstone::testing
