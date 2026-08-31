#include <touchstone/pde.hpp>

#include <touchstone/scales.hpp>
#include <touchstone/tridiagonal.hpp>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <vector>

namespace touchstone {
namespace {

/// The largest `x` with `exp(x)` finite is 709.782712893384; the round number
/// below it is the bound this file enforces, so that the message can say 709 and
/// mean it.
constexpr double max_log_spot = 709.0;

/// A uniform grid in `x = ln S`, anchored so that the spot is a node.
struct Grid {
    std::size_t intervals{};   ///< `n`: nodes are 0..n.
    std::size_t spot_index{};  ///< `i0`, with `x(i0) == ln S` exactly.
    double step{};             ///< `dx`.
    double log_spot{};         ///< `ln S`.

    [[nodiscard]] double x(std::size_t i) const noexcept
    {
        // Written as an offset from the anchor rather than from node zero, so
        // that x(spot_index) is ln S to the last bit and the price is a solution
        // value rather than an interpolation.
        return log_spot
               + (static_cast<double>(i) - static_cast<double>(spot_index)) * step;
    }

    [[nodiscard]] double lower() const noexcept { return x(0); }
    [[nodiscard]] double upper() const noexcept { return x(intervals); }
};

/// Size the domain, then anchor it on the spot and grow it outward to cover what
/// was sized.
///
/// The domain has to hold three points before any margin is added: the spot,
/// because that is where the answer is read; the strike, because otherwise the
/// payoff is a constant across the whole grid and the option has no kink in it;
/// and the forward log-price `ln S + (r - q - sigma^2/2) T`, because that is
/// where the terminal distribution's mass actually sits, and with a large carry
/// or a long expiry it can be a long way from the spot. Every intermediate
/// forward lies between the spot and that one, so covering both covers all of
/// them, and the margin then reaches `alpha` total volatilities beyond the
/// furthest.
[[nodiscard]] Grid make_grid(const EuropeanVanilla& option,
                             const BlackScholesMarket& market,
                             const PdeSettings& settings)
{
    const double years = option.expiry_years;
    const double log_spot = std::log(market.spot);
    const double log_strike = std::log(option.strike);
    const double forward = log_spot + detail::carry_time(market.rate, market.dividend_yield, years)
                           - detail::half_variance_time(market.vol, years);

    const double margin = settings.half_width_sigmas * detail::total_volatility(market.vol, years);
    const double lower = std::min({log_spot, log_strike, forward}) - margin;
    const double upper = std::max({log_spot, log_strike, forward}) + margin;

    Grid grid{};
    grid.log_spot = log_spot;
    grid.step = (upper - lower) / static_cast<double>(settings.space_intervals);

    // Whole numbers of steps out to each end, rounded up, so the anchored grid
    // covers everything the sizing above asked for. This is why the node count
    // can exceed `space_intervals`, by at most two.
    const double below = std::ceil((log_spot - lower) / grid.step);
    const double above = std::ceil((upper - log_spot) / grid.step);
    grid.spot_index = static_cast<std::size_t>(below);
    grid.intervals = static_cast<std::size_t>(below + above);
    return grid;
}

/// `max(w (S - K), 0)` at a node, from the node's log-spot.
[[nodiscard]] double intrinsic_at(double log_spot_node, const EuropeanVanilla& option) noexcept
{
    const double value = option_sign(option.type) * (std::exp(log_spot_node) - option.strike);
    return value > 0.0 ? value : 0.0;
}

/// The average of the payoff over the cell of width `dx` centred on a node.
///
/// The initial data has a kink at the strike, and a kink is not a function a
/// difference operator has any accuracy on: the fourth derivative the truncation
/// error is proportional to is a delta function there. Sampling the payoff at the
/// nodes carries that straight into the first step, and it survives to the end as
/// an `O(dx^2)` error with a constant an order of magnitude larger than the
/// smooth part of the solution contributes. Projecting the payoff onto cell
/// averages instead — the finite-volume reading of the same grid, and the
/// smoothing Pooley, Vetzal and Forsyth (2003) recommend for exactly this — puts
/// the kink's contribution back on the same scale as everything else.
///
/// The integral is exact, not quadrature. For a call, over the part of the cell
/// above the strike:
///
///     (1/dx) integral of (e^y - K) dy  =  (e^hi - e^lo - K (hi - lo)) / dx
///
/// written with `expm1` because at the strike the two exponentials agree in every
/// digit that matters and their difference is the whole answer.
[[nodiscard]] double cell_average_payoff(double centre,
                                         double dx,
                                         const EuropeanVanilla& option) noexcept
{
    const double half = 0.5 * dx;
    const double lo = centre - half;
    const double hi = centre + half;
    const double log_strike = std::log(option.strike);

    if (option.type == OptionType::Call) {
        if (hi <= log_strike) {
            return 0.0;
        }
        const double from = std::max(lo, log_strike);
        return (std::exp(from) * std::expm1(hi - from) - option.strike * (hi - from)) / dx;
    }

    if (lo >= log_strike) {
        return 0.0;
    }
    const double to = std::min(hi, log_strike);
    return (option.strike * (to - lo) - std::exp(lo) * std::expm1(to - lo)) / dx;
}

/// The Dirichlet value at one end of the domain, at time-to-expiry `tau`.
///
/// Deep out of the money the option is worth nothing; deep in the money it is
/// worth the discounted forward intrinsic `w (S e^{-q tau} - K e^{-r tau})`,
/// which is what a European vanilla tends to once the probability of finishing
/// on the other side of the strike has gone. The exponential is formed as one
/// `exp(x - q tau)` rather than as `exp(x)` times a discount, because the two
/// factors are individually large and small at the ends of a wide grid.
///
/// American: the same, raised to immediate exercise where that is worth more.
/// At the exercise end that is the whole of the boundary condition — an American
/// put deep in the money is worth `K - S`, not its discounted counterpart.
[[nodiscard]] double boundary_value(double log_spot_node,
                                    bool deep_in_the_money,
                                    const EuropeanVanilla& option,
                                    const BlackScholesMarket& market,
                                    double tau,
                                    Exercise exercise) noexcept
{
    double value = 0.0;
    if (deep_in_the_money) {
        value = option_sign(option.type)
                * (std::exp(log_spot_node - market.dividend_yield * tau)
                   - option.strike * detail::discount_factor(market.rate, tau));
    }
    if (exercise == Exercise::American) {
        value = std::fmax(value, intrinsic_at(log_spot_node, option));
    }
    return value;
}

}  // namespace

void require_valid(const EuropeanVanilla& option,
                   const BlackScholesMarket& market,
                   const PdeSettings& settings)
{
    // The closed form's domain first, so that a row this method prices is a row
    // the other two price too.
    require_valid(option, market);

    if (settings.space_intervals < 2) {
        throw std::invalid_argument("pde: space_intervals must be at least 2");
    }
    if (settings.time_steps < 1) {
        throw std::invalid_argument("pde: time_steps must be at least 1");
    }
    if (settings.rannacher_steps > settings.time_steps) {
        throw std::invalid_argument(
            "pde: rannacher_steps cannot exceed time_steps; there would be nothing left to run "
            "Crank-Nicolson on");
    }
    if (!(settings.half_width_sigmas > 0.0) || !std::isfinite(settings.half_width_sigmas)) {
        throw std::invalid_argument("pde: half_width_sigmas must be finite and positive");
    }

    if (!(market.spot > 0.0)) {
        throw std::invalid_argument(
            "pde: the grid is in ln(spot), so the spot must be positive; the closed form prices a "
            "spot of zero exactly and this cannot price it at all");
    }
    if (!(option.strike > 0.0)) {
        throw std::invalid_argument(
            "pde: the grid is in ln(spot), so the strike must be positive; a strike of zero has no "
            "kink for the grid to resolve and the closed form prices it exactly");
    }

    const double total_vol = detail::total_volatility(market.vol, option.expiry_years);
    if (!(total_vol > 0.0)) {
        throw std::invalid_argument(
            "pde: the total volatility vol * sqrt(expiry_years) must be positive; at zero there is "
            "no diffusion to discretise and the option is worth its discounted intrinsic value, "
            "which the closed form returns exactly");
    }

    // sigma^2 appears undivided in the diffusion coefficient, so unlike the
    // closed form — which only ever forms half of it, times T — this method has
    // to be able to represent it. Each method checks the products it forms.
    const double variance = market.vol * market.vol;
    if (!std::isfinite(variance)) {
        throw std::invalid_argument(
            "pde: the variance vol^2 overflows a double; the diffusion coefficient of the equation "
            "cannot be formed");
    }

    const Grid grid = make_grid(option, market, settings);
    if (!(grid.step > 0.0) || !std::isfinite(grid.step)) {
        throw std::invalid_argument("pde: the log-spot step underflows or overflows a double");
    }
    if (!std::isfinite(variance / (grid.step * grid.step))) {
        throw std::invalid_argument(
            "pde: vol^2 divided by the squared log-spot step overflows a double; the grid is too "
            "fine for this volatility");
    }
    if (grid.intervals < 2 || grid.spot_index == 0 || grid.spot_index >= grid.intervals) {
        throw std::invalid_argument(
            "pde: the anchored grid has no interior node either side of the spot");
    }

    // The upper boundary is exp(x_max - q tau), largest at tau = 0 when the
    // yield is positive and at tau = T when it is negative. An infinity there
    // reaches every node inside it within one step.
    const double highest_exponent =
        grid.upper() + std::max(0.0, -market.dividend_yield * option.expiry_years);
    if (!(highest_exponent <= max_log_spot)) {
        throw std::invalid_argument(
            "pde: the top of the log-spot grid is not representable as a spot — ln(spot) plus the "
            "domain margin exceeds 709, so exp of it overflows a double");
    }
}

PdeResult crank_nicolson(const EuropeanVanilla& option,
                         const BlackScholesMarket& market,
                         const PdeSettings& settings)
{
    require_valid(option, market, settings);

    const Grid grid = make_grid(option, market, settings);
    const std::size_t nodes = grid.intervals + 1;
    const std::size_t interior = grid.intervals - 1;

    const double years = option.expiry_years;
    const double variance = market.vol * market.vol;
    const double dx = grid.step;
    const double dtau = years / static_cast<double>(settings.time_steps);

    // The spatial operator, constant in x and in tau:
    //
    //     L u = (sigma^2/2) u_xx + nu u_x - r u,     nu = r - q - sigma^2/2
    //
    // discretised with central differences into `a u_{i-1} + b u_i + c u_{i+1}`.
    const double nu = market.rate - market.dividend_yield - 0.5 * variance;
    const double diffusion = 0.5 * variance / (dx * dx);
    const double convection = nu / (2.0 * dx);
    const double a = diffusion - convection;
    const double b = -2.0 * diffusion - market.rate;
    const double c = diffusion + convection;

    std::vector<double> value(nodes, 0.0);
    std::vector<double> intrinsic(nodes, 0.0);
    for (std::size_t i = 0; i < nodes; ++i) {
        const double x = grid.x(i);
        intrinsic[i] = intrinsic_at(x, option);
        // The payoff at tau = 0, either sampled at the node or averaged over its
        // cell. The two boundary nodes keep the sampled value: they are Dirichlet
        // and are overwritten by `boundary_value` on the first step anyway, and a
        // half-cell average there would be an average of a cell half outside the
        // domain.
        const bool inner = (i > 0 && i < grid.intervals);
        value[i] = (settings.smooth_payoff && inner) ? cell_average_payoff(x, dx, option)
                                                     : intrinsic[i];
    }

    // Two matrices, each built once: the fully implicit one for the Rannacher
    // start, at half a step, and the Crank-Nicolson one for everything after.
    // Only the right-hand side changes from step to step.
    std::vector<double> sub(interior, 0.0);
    std::vector<double> diag(interior, 0.0);
    std::vector<double> sup(interior, 0.0);
    std::vector<double> rhs(interior, 0.0);
    std::vector<double> solution(interior, 0.0);
    std::vector<double> scratch(interior, 0.0);
    std::vector<double> constraint(interior, 0.0);
    for (std::size_t j = 0; j < interior; ++j) {
        constraint[j] = intrinsic[j + 1];
    }

    const ExerciseRegion region = (option.type == OptionType::Put) ? ExerciseRegion::Lower
                                                                  : ExerciseRegion::Upper;

    double worst_margin = std::numeric_limits<double>::infinity();

    /// One step of `(I - theta dt L) u_new = (I + (1 - theta) dt L) u_old`, with
    /// the two known boundary values at the new time level moved to the
    /// right-hand side.
    const auto step = [&](double theta, double dt, double tau_new) {
        for (std::size_t j = 0; j < interior; ++j) {
            sub[j] = -theta * dt * a;
            diag[j] = 1.0 - theta * dt * b;
            sup[j] = -theta * dt * c;
        }
        const Tridiagonal matrix{sub, diag, sup};
        worst_margin = std::min(worst_margin, dominance_margin(matrix));

        const double lower_new =
            boundary_value(grid.lower(), option.type == OptionType::Put, option, market, tau_new,
                           settings.exercise);
        const double upper_new =
            boundary_value(grid.upper(), option.type == OptionType::Call, option, market, tau_new,
                           settings.exercise);

        const double explicit_weight = (1.0 - theta) * dt;
        for (std::size_t j = 0; j < interior; ++j) {
            const std::size_t i = j + 1;
            rhs[j] = value[i]
                     + explicit_weight * (a * value[i - 1] + b * value[i] + c * value[i + 1]);
        }
        rhs[0] += theta * dt * a * lower_new;
        rhs[interior - 1] += theta * dt * c * upper_new;

        if (settings.exercise == Exercise::American) {
            solve_tridiagonal_projected(matrix, rhs, constraint, region, solution, scratch);
        } else {
            solve_tridiagonal(matrix, rhs, solution, scratch);
        }

        value[0] = lower_new;
        value[grid.intervals] = upper_new;
        for (std::size_t j = 0; j < interior; ++j) {
            value[j + 1] = solution[j];
        }
    };

    // Rannacher's start: the first `rannacher_steps` steps run fully implicit, at
    // half the step size, twice each. Backward Euler damps the modes the payoff's
    // kink excites by a factor tending to zero, where Crank-Nicolson damps them
    // by a factor tending to minus one — which is stable, and oscillates. Half
    // steps keep the local truncation error of the start comparable to the
    // second-order steps that follow it, which is what leaves the whole scheme
    // second order rather than merely non-oscillatory.
    std::size_t taken = 0;
    for (; taken < settings.rannacher_steps; ++taken) {
        const double tau_at = static_cast<double>(taken) * dtau;
        step(1.0, 0.5 * dtau, tau_at + 0.5 * dtau);
        step(1.0, 0.5 * dtau, tau_at + dtau);
    }
    for (; taken < settings.time_steps; ++taken) {
        // The last step lands on T exactly rather than on the accumulated sum of
        // `time_steps` copies of `dtau`, which is a different number.
        const bool last = (taken + 1 == settings.time_steps);
        const double tau_new = last ? years : static_cast<double>(taken + 1) * dtau;
        step(0.5, dtau, tau_new);
    }

    const std::size_t i0 = grid.spot_index;
    const double u_x = (value[i0 + 1] - value[i0 - 1]) / (2.0 * dx);
    const double u_xx = (value[i0 + 1] - 2.0 * value[i0] + value[i0 - 1]) / (dx * dx);

    PdeResult result{};
    result.price = value[i0];
    // Out of log-space: dV/dS = u_x / S, and d2V/dS2 = (u_xx - u_x) / S^2.
    result.delta = u_x / market.spot;
    result.gamma = (u_xx - u_x) / (market.spot * market.spot);
    result.space_intervals = grid.intervals;
    result.time_steps = settings.time_steps;
    result.spot_index = i0;
    result.log_spot_step = dx;
    result.time_step = dtau;
    result.lower_log_spot = grid.lower();
    result.upper_log_spot = grid.upper();
    result.mesh_peclet = std::abs(nu) * dx / variance;
    result.resolution_in_sigmas = dx / detail::total_volatility(market.vol, years);
    result.dominance_margin = worst_margin;
    return result;
}

}  // namespace touchstone
