#include <touchstone/bump_greeks.hpp>

#include <touchstone/detail/checks.hpp>

#include <stdexcept>

namespace touchstone {
namespace detail {

Bumps bumps(const EuropeanVanilla& option,
            const BlackScholesMarket& market,
            const BumpSizes& sizes) noexcept
{
    Bumps out{};
    out.delta_spot = sizes.spot_relative * market.spot;
    out.gamma_spot = sizes.spot_relative_for_gamma * market.spot;

    const auto in_market = [&](auto field, double by) {
        BlackScholesMarket moved = market;
        moved.*field += by;
        return BumpedPoint{option, moved};
    };
    const auto in_expiry = [&](double by) {
        EuropeanVanilla moved = option;
        moved.expiry_years += by;
        return BumpedPoint{moved, market};
    };

    out.points[DeltaUp] = in_market(&BlackScholesMarket::spot, out.delta_spot);
    out.points[DeltaDown] = in_market(&BlackScholesMarket::spot, -out.delta_spot);
    out.points[GammaUp] = in_market(&BlackScholesMarket::spot, out.gamma_spot);
    out.points[GammaDown] = in_market(&BlackScholesMarket::spot, -out.gamma_spot);
    out.points[VolUp] = in_market(&BlackScholesMarket::vol, sizes.vol_absolute);
    out.points[VolDown] = in_market(&BlackScholesMarket::vol, -sizes.vol_absolute);
    out.points[RateUp] = in_market(&BlackScholesMarket::rate, sizes.rate_absolute);
    out.points[RateDown] = in_market(&BlackScholesMarket::rate, -sizes.rate_absolute);
    out.points[YieldUp] =
        in_market(&BlackScholesMarket::dividend_yield, sizes.dividend_yield_absolute);
    out.points[YieldDown] =
        in_market(&BlackScholesMarket::dividend_yield, -sizes.dividend_yield_absolute);
    out.points[Longer] = in_expiry(sizes.expiry_absolute);
    out.points[Shorter] = in_expiry(-sizes.expiry_absolute);
    return out;
}

}  // namespace detail

void require_valid(const EuropeanVanilla& option,
                   const BlackScholesMarket& market,
                   const BumpSizes& sizes)
{
    require_valid(option, market);

    if (!detail::is_finite_positive(sizes.spot_relative)
        || !detail::is_finite_positive(sizes.spot_relative_for_gamma)
        || !detail::is_finite_positive(sizes.vol_absolute)
        || !detail::is_finite_positive(sizes.rate_absolute)
        || !detail::is_finite_positive(sizes.dividend_yield_absolute)
        || !detail::is_finite_positive(sizes.expiry_absolute)) {
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
    for (const detail::BumpedPoint& point : detail::bumps(option, market, sizes).points) {
        require_valid(point.option, point.market);
    }
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
