#include <touchstone/bump_greeks.hpp>

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace touchstone {

void require_valid(const EuropeanVanilla& option,
                   const BlackScholesMarket& market,
                   const BumpSizes& sizes)
{
    require_valid(option, market);

    const auto positive = [](double x) { return std::isfinite(x) && x > 0.0; };
    if (!positive(sizes.spot_relative) || !positive(sizes.spot_relative_for_gamma)
        || !positive(sizes.vol_absolute) || !positive(sizes.rate_absolute)
        || !positive(sizes.dividend_yield_absolute) || !positive(sizes.expiry_absolute)) {
        throw std::invalid_argument("bump greeks: every bump size must be finite and positive");
    }

    if (!(market.spot > 0.0)) {
        throw std::invalid_argument(
            "bump greeks: the spot bump is relative, so a spot of zero has no bump; the closed "
            "form's delta and gamma are exact there");
    }
    if (market.vol < sizes.vol_absolute) {
        throw std::invalid_argument(
            "bump greeks: the volatility is smaller than its own bump, so the down bump would be "
            "negative; shrink vol_absolute or take vega from the closed form");
    }
    if (option.expiry_years < sizes.expiry_absolute) {
        throw std::invalid_argument(
            "bump greeks: the expiry is shorter than its own bump, so the down bump would be "
            "negative; shrink expiry_absolute or take theta from the closed form");
    }

    // Every bumped point is priced, so every bumped point has to be priceable.
    // Checked here rather than discovered thirteen calls later, where the
    // exception would name a market the caller never constructed.
    const double spot_bump =
        std::max(sizes.spot_relative, sizes.spot_relative_for_gamma) * market.spot;
    const auto also = [&](const EuropeanVanilla& contract, const BlackScholesMarket& state) {
        require_valid(contract, state);
    };
    also(option, BlackScholesMarket{market.spot + spot_bump, market.vol, market.rate,
                                    market.dividend_yield});
    also(option, BlackScholesMarket{market.spot - spot_bump, market.vol, market.rate,
                                    market.dividend_yield});
    also(option, BlackScholesMarket{market.spot, market.vol + sizes.vol_absolute, market.rate,
                                    market.dividend_yield});
    also(option, BlackScholesMarket{market.spot, market.vol - sizes.vol_absolute, market.rate,
                                    market.dividend_yield});
    also(option, BlackScholesMarket{market.spot, market.vol, market.rate + sizes.rate_absolute,
                                    market.dividend_yield});
    also(option, BlackScholesMarket{market.spot, market.vol, market.rate - sizes.rate_absolute,
                                    market.dividend_yield});
    also(option, BlackScholesMarket{market.spot, market.vol, market.rate,
                                    market.dividend_yield + sizes.dividend_yield_absolute});
    also(option, BlackScholesMarket{market.spot, market.vol, market.rate,
                                    market.dividend_yield - sizes.dividend_yield_absolute});
    also(EuropeanVanilla{option.strike, option.expiry_years + sizes.expiry_absolute, option.type},
         market);
    also(EuropeanVanilla{option.strike, option.expiry_years - sizes.expiry_absolute, option.type},
         market);
}

PriceAndGreeks bump_greeks(const EuropeanVanilla& option,
                           const BlackScholesMarket& market,
                           const BumpSizes& sizes)
{
    return bump_greeks(option, market, sizes,
                       [](const EuropeanVanilla& contract, const BlackScholesMarket& state) {
                           return price(contract, state);
                       });
}

}  // namespace touchstone
