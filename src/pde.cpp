#include <touchstone/pde.hpp>

#include <touchstone/detail/checks.hpp>
#include <touchstone/detail/differences.hpp>
#include <touchstone/detail/grid_solver.hpp>
#include <touchstone/detail/scales.hpp>
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
template <Exercise E>
[[nodiscard]] detail::LogSpotGrid make_grid(const Vanilla<E>& option,
                                            const BlackScholesMarket& market,
                                            const PdeSettings& settings)
{
    const double years = option.expiry_years;
    const double log_spot = std::log(market.spot);
    const double log_strike = std::log(option.strike);
    const double forward =
        log_spot
        + detail::log_drift_time(detail::carry_rate(market.rate, market.dividend_yield), market.vol,
                                 years);

    const double margin = settings.half_width_sigmas * detail::total_volatility(market.vol, years);
    const double lower = std::min({log_spot, log_strike, forward}) - margin;
    const double upper = std::max({log_spot, log_strike, forward}) + margin;

    detail::LogSpotGrid grid{};
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

/// `(sigma^2 / 2) / dx^2`: the weight the second difference carries in the
/// spatial operator. The domain check guards twice it, which is the product the
/// operator's diagonal forms.
[[nodiscard]] double diffusion_coefficient(double vol, double dx) noexcept
{
    return 0.5 * detail::variance(vol) / (dx * dx);
}

/// A put is exercised, and is deep in the money, at the low end of the grid; a
/// call at the high end.
[[nodiscard]] bool in_the_money_below(OptionType type) noexcept
{
    return type == OptionType::Put;
}

/// `require_valid`, for either exercise style, returning the grid it checked so
/// that the solver builds the grid once.
template <Exercise E>
detail::LogSpotGrid validated_grid(const Vanilla<E>& option,
                                   const BlackScholesMarket& market,
                                   const PdeSettings& settings)
{
    // The closed form's domain first, so that a row this method prices is a row
    // the other two price too. The exercise style does not change the domain.
    require_valid(with_exercise<Exercise::European>(option), market);

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
    if (!detail::is_finite_positive(settings.half_width_sigmas)) {
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
    const double variance = detail::variance(market.vol);
    if (!std::isfinite(variance)) {
        throw std::invalid_argument(
            "pde: the variance vol^2 overflows a double; the diffusion coefficient of the equation "
            "cannot be formed");
    }

    const detail::LogSpotGrid grid = make_grid(option, market, settings);
    if (!detail::is_finite_positive(grid.step)) {
        throw std::invalid_argument("pde: the log-spot step underflows or overflows a double");
    }
    if (!std::isfinite(2.0 * diffusion_coefficient(market.vol, grid.step))) {
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
        grid.upper()
        + std::max(0.0, detail::log_discount(market.dividend_yield, option.expiry_years));
    if (!(highest_exponent <= max_log_spot)) {
        throw std::invalid_argument(
            "pde: the top of the log-spot grid is not representable as a spot — ln(spot) plus the "
            "domain margin exceeds 709, so exp of it overflows a double");
    }
    return grid;
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
template <Exercise E>
[[nodiscard]] double cell_average_payoff(double centre, double dx, const Vanilla<E>& option) noexcept
{
    const double half = 0.5 * dx;
    const double lo = centre - half;
    const double hi = centre + half;
    const double log_strike = std::log(option.strike);

    // The part of the cell in the money: above the strike for a call, below it
    // for a put. Over it the payoff is `w (e^y - K)`, whose average is the one
    // expression below whichever side it is.
    const bool call = (option.type == OptionType::Call);
    const double from = call ? std::max(lo, log_strike) : lo;
    const double to = call ? hi : std::min(hi, log_strike);
    if (to <= from) {
        return 0.0;
    }
    return option_sign(option.type)
           * (std::exp(from) * std::expm1(to - from) - option.strike * (to - from)) / dx;
}

/// The node's spot, from its log-spot, and what exercising there pays.
template <Exercise E>
[[nodiscard]] double payoff_at(double log_spot_node, const Vanilla<E>& option) noexcept
{
    return payoff(option, std::exp(log_spot_node));
}

template <Exercise E>
[[nodiscard]] PdeResult solve_to_today(const Vanilla<E>& option,
                                       const BlackScholesMarket& market,
                                       const PdeSettings& settings)
{
    detail::GridSolver<E> solver(option, market, settings);
    solver.solve();
    return solver.result();
}

template <Exercise E>
[[nodiscard]] PdeSurface sample_to_today(const Vanilla<E>& option,
                                         const BlackScholesMarket& market,
                                         const PdeSettings& settings,
                                         const SurfaceSampling& sampling)
{
    const std::size_t every = sampling.every_steps;
    if (every == 0) {
        throw std::invalid_argument("pde: every_steps must be at least 1");
    }

    detail::GridSolver<E> solver(option, market, settings);
    PdeSurface out;
    const std::size_t nodes = solver.values().size();
    out.log_spots.resize(nodes);
    for (std::size_t i = 0; i < nodes; ++i) {
        out.log_spots[i] = solver.grid().x(i);
    }

    const auto keep = [&] {
        out.times_to_expiry.push_back(solver.time_to_expiry());
        const auto level = solver.values();
        out.values.insert(out.values.end(), level.begin(), level.end());
    };
    keep();
    while (solver.advance()) {
        if (solver.steps_taken() % every == 0) {
            keep();
        }
    }
    if (solver.steps_taken() % every != 0) {
        keep();  // Today, which the stride stepped past.
    }
    out.result = solver.result();
    return out;
}

}  // namespace

void require_valid(const EuropeanVanilla& option,
                   const BlackScholesMarket& market,
                   const PdeSettings& settings)
{
    static_cast<void>(validated_grid(option, market, settings));
}

void require_valid(const AmericanVanilla& option,
                   const BlackScholesMarket& market,
                   const PdeSettings& settings)
{
    static_cast<void>(validated_grid(option, market, settings));
}

PdeResult crank_nicolson(const EuropeanVanilla& option,
                         const BlackScholesMarket& market,
                         const PdeSettings& settings)
{
    return solve_to_today(option, market, settings);
}

PdeResult crank_nicolson(const AmericanVanilla& option,
                         const BlackScholesMarket& market,
                         const PdeSettings& settings)
{
    return solve_to_today(option, market, settings);
}

PdeSurface crank_nicolson_surface(const EuropeanVanilla& option,
                                  const BlackScholesMarket& market,
                                  const PdeSettings& settings,
                                  const SurfaceSampling& sampling)
{
    return sample_to_today(option, market, settings, sampling);
}

PdeSurface crank_nicolson_surface(const AmericanVanilla& option,
                                  const BlackScholesMarket& market,
                                  const PdeSettings& settings,
                                  const SurfaceSampling& sampling)
{
    return sample_to_today(option, market, settings, sampling);
}

namespace detail {

template <Exercise E>
GridSolver<E>::GridSolver(const Vanilla<E>& option,
                          const BlackScholesMarket& market,
                          const PdeSettings& settings)
    : option_(option),
      market_(market),
      settings_(settings),
      grid_(validated_grid(option, market, settings)),
      dtau_(option.expiry_years / static_cast<double>(settings.time_steps))
{
    const double dx = grid_.step;

    // The spatial operator, constant in x and in tau:
    //
    //     L u = (sigma^2/2) u_xx + nu u_x - r u,     nu = r - q - sigma^2/2
    //
    // discretised with central differences into `a u_{i-1} + b u_i + c u_{i+1}`.
    // nu is the log-price's drift per unit of time.
    nu_ = detail::log_drift_time(detail::carry_rate(market.rate, market.dividend_yield), market.vol,
                                 1.0);
    const double diffusion = diffusion_coefficient(market.vol, dx);
    const double convection = nu_ / (2.0 * dx);
    a_ = diffusion - convection;
    b_ = -2.0 * diffusion - market.rate;
    c_ = diffusion + convection;

    // The two matrices, each built once: the fully implicit one at half a step
    // for the Rannacher start, and the Crank-Nicolson one for everything after.
    // Only the right-hand side changes from step to step. The dominance reported
    // is that of whichever of the two the run uses.
    implicit_ = build(1.0, 0.5 * dtau_);
    crank_ = build(0.5, dtau_);
    dominance_ = std::numeric_limits<double>::infinity();
    if (settings.rannacher_steps > 0) {
        dominance_ = std::min(dominance_, dominance_margin(implicit_.matrix()));
    }
    if (settings.rannacher_steps < settings.time_steps) {
        dominance_ = std::min(dominance_, dominance_margin(crank_.matrix()));
    }

    const std::size_t nodes = grid_.intervals + 1;
    const std::size_t interior = grid_.intervals - 1;
    value_.assign(nodes, 0.0);
    rhs_.assign(interior, 0.0);
    solution_.assign(interior, 0.0);
    scratch_.assign(interior, 0.0);
    if constexpr (E == Exercise::American) {
        constraint_.assign(interior, 0.0);
    }

    for (std::size_t i = 0; i < nodes; ++i) {
        const double x = grid_.x(i);
        const double at_node = payoff_at(x, option);
        // The payoff at tau = 0, either sampled at the node or averaged over its
        // cell. The two boundary nodes keep the sampled value: they are Dirichlet
        // and are overwritten by `boundary_value` on the first step anyway, and a
        // half-cell average there would be an average of a cell half outside the
        // domain.
        const bool inner = (i > 0 && i < grid_.intervals);
        value_[i] = (settings.smooth_payoff && inner) ? cell_average_payoff(x, dx, option) : at_node;
        if constexpr (E == Exercise::American) {
            if (inner) {
                constraint_[i - 1] = at_node;
            }
        }
    }
}

template <Exercise E>
typename GridSolver<E>::Stepping GridSolver<E>::build(double theta, double dt) const
{
    const std::size_t interior = grid_.intervals - 1;
    Stepping stepping{};
    stepping.theta = theta;
    stepping.dt = dt;
    stepping.lower_weight = theta * dt * a_;
    stepping.upper_weight = theta * dt * c_;
    stepping.sub.assign(interior, -stepping.lower_weight);
    stepping.diag.assign(interior, 1.0 - theta * dt * b_);
    stepping.sup.assign(interior, -stepping.upper_weight);
    return stepping;
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
template <Exercise E>
double GridSolver<E>::boundary_value(double log_spot_node, bool deep_in_the_money, double tau) const
{
    double value = 0.0;
    if (deep_in_the_money) {
        value = option_sign(option_.type)
                * (std::exp(log_spot_node + detail::log_discount(market_.dividend_yield, tau))
                   - option_.strike * detail::discount_factor(market_.rate, tau));
    }
    if constexpr (E == Exercise::American) {
        value = std::fmax(value, payoff_at(log_spot_node, option_));
    }
    return value;
}

/// One step of `(I - theta dt L) u_new = (I + (1 - theta) dt L) u_old`, with the
/// two known boundary values at the new time level moved to the right-hand side.
template <Exercise E>
void GridSolver<E>::step(const Stepping& stepping, double tau_new)
{
    const double theta = stepping.theta;
    const double dt = stepping.dt;
    const std::size_t interior = grid_.intervals - 1;

    const bool below = in_the_money_below(option_.type);
    const double lower_new = boundary_value(grid_.lower(), below, tau_new);
    const double upper_new = boundary_value(grid_.upper(), !below, tau_new);

    const double explicit_weight = (1.0 - theta) * dt;
    for (std::size_t j = 0; j < interior; ++j) {
        const std::size_t i = j + 1;
        rhs_[j] = value_[i]
                  + explicit_weight * (a_ * value_[i - 1] + b_ * value_[i] + c_ * value_[i + 1]);
    }
    rhs_[0] += stepping.lower_weight * lower_new;
    rhs_[interior - 1] += stepping.upper_weight * upper_new;

    if constexpr (E == Exercise::American) {
        const ExerciseRegion region = below ? ExerciseRegion::Lower : ExerciseRegion::Upper;
        solve_tridiagonal_projected(stepping.matrix(), rhs_, constraint_, region, solution_,
                                    scratch_);
    } else {
        solve_tridiagonal(stepping.matrix(), rhs_, solution_, scratch_);
    }

    value_[0] = lower_new;
    value_[grid_.intervals] = upper_new;
    std::copy(solution_.begin(), solution_.end(), value_.begin() + 1);
    tau_ = tau_new;
}

template <Exercise E>
bool GridSolver<E>::advance()
{
    if (taken_ >= settings_.time_steps) {
        return false;
    }
    if (taken_ < settings_.rannacher_steps) {
        // Rannacher's start: the first `rannacher_steps` steps run fully
        // implicit, at half the step size, twice each. Backward Euler damps the
        // modes the payoff's kink excites by a factor tending to zero, where
        // Crank-Nicolson damps them by a factor tending to minus one — which is
        // stable, and oscillates. Half steps keep the local truncation error of
        // the start comparable to the second-order steps that follow it, which is
        // what leaves the whole scheme second order rather than merely
        // non-oscillatory.
        const double tau_at = static_cast<double>(taken_) * dtau_;
        step(implicit_, tau_at + 0.5 * dtau_);
        step(implicit_, tau_at + dtau_);
    } else {
        // The last step lands on T exactly rather than on the accumulated sum of
        // `time_steps` copies of `dtau`, which is a different number.
        const bool last = (taken_ + 1 == settings_.time_steps);
        const double tau_new =
            last ? option_.expiry_years : static_cast<double>(taken_ + 1) * dtau_;
        step(crank_, tau_new);
    }
    ++taken_;
    return true;
}

template <Exercise E>
void GridSolver<E>::solve()
{
    while (advance()) {
    }
}

template <Exercise E>
PdeResult GridSolver<E>::result() const
{
    const double dx = grid_.step;
    const std::size_t i0 = grid_.spot_index;
    const double u_x = detail::central_first(value_[i0 + 1], value_[i0 - 1], dx);
    const double u_xx = detail::central_second(value_[i0 + 1], value_[i0], value_[i0 - 1], dx);

    PdeResult out{};
    out.price = value_[i0];
    // Out of log-space: dV/dS = u_x / S, and d2V/dS2 = (u_xx - u_x) / S^2.
    out.delta = u_x / market_.spot;
    out.gamma = (u_xx - u_x) / (market_.spot * market_.spot);
    out.space_intervals = grid_.intervals;
    out.time_steps = settings_.time_steps;
    out.spot_index = i0;
    out.log_spot_step = dx;
    out.time_step = dtau_;
    out.lower_log_spot = grid_.lower();
    out.upper_log_spot = grid_.upper();
    out.mesh_peclet = std::abs(nu_) * dx / detail::variance(market_.vol);
    out.resolution_in_sigmas =
        dx / detail::total_volatility(market_.vol, option_.expiry_years);
    out.dominance_margin = dominance_;
    return out;
}

template class GridSolver<Exercise::European>;
template class GridSolver<Exercise::American>;

}  // namespace detail
}  // namespace touchstone
