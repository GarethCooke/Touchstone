// The seven outputs of `PriceAndGreeks`, by name and by member, in the order
// the struct declares them — for the sweeps that compare all seven at once.

#pragma once

#include <touchstone/black_scholes.hpp>

#include <array>

namespace touchstone::testing {

struct GreekField {
    const char* name;
    double PriceAndGreeks::* value;
};

inline constexpr std::array<GreekField, 7> greek_fields{{
    {"price", &PriceAndGreeks::price},
    {"delta", &PriceAndGreeks::delta},
    {"gamma", &PriceAndGreeks::gamma},
    {"vega", &PriceAndGreeks::vega},
    {"theta", &PriceAndGreeks::theta},
    {"rho", &PriceAndGreeks::rho},
    {"dividend_rho", &PriceAndGreeks::dividend_rho},
}};

}  // namespace touchstone::testing
