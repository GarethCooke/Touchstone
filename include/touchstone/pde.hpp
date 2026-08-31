// European and American vanillas by finite differences: the third of the three
// ways they are priced.
//
// Constitution I20 wants closed form, Monte Carlo and finite differences to
// agree. T1 built the first and T2 the second; this is the third, and it is the
// least like the others. The closed form evaluates a formula. The Monte Carlo
// samples the terminal distribution. This solves the equation the option's value
// satisfies, on a grid, from expiry backwards — so it never uses `N(d)`, never
// draws a random number, and shares no arithmetic with either of them beyond the
// scale functions of `touchstone/scales.hpp`. Three methods that agree here have
// agreed about the model rather than about one implementation of it.
//
// It is also the only one of the three that can price an option the holder may
// exercise early, because early exercise is a constraint on the value function
// and a value function is what this method carries.
//
// ## The equation
//
// In the log-spot `x = ln S` and the time to expiry `tau = T - t`, the
// Black-Scholes-Merton equation has constant coefficients:
//
//     du/dtau = (sigma^2 / 2) d2u/dx2 + (r - q - sigma^2 / 2) du/dx - r u
//
// which is why the grid is in log-spot: in `S` the coefficients carry factors of
// `S` and `S^2`, the mesh must be graded to keep the accuracy uniform, and the
// scheme's error depends on where the spot happens to sit. In `x` one uniform
// grid is uniformly accurate, and the same grid serves every spot.
//
// ## The scheme
//
// Crank-Nicolson: the average of the explicit and implicit steps, second-order
// in both `dx` and `dtau`, and unconditionally stable in the von Neumann sense.
// Unconditional stability is not the same as unconditional accuracy, and a
// vanilla payoff shows the difference: its kink at the strike is not resolved by
// any grid, and Crank-Nicolson damps the resulting high-frequency error by a
// factor tending to -1 rather than to 0, so it oscillates instead of decaying.
// The standard repair is Rannacher's: run the first few steps fully implicit,
// which damps those modes hard, then switch to Crank-Nicolson. `PdeSettings`
// makes the number of them a setting, and `tests/test_pde.cpp` measures the
// convergence order with it and without.

#pragma once

#include <touchstone/black_scholes.hpp>

#include <cstddef>

namespace touchstone {

/// When the holder may exercise.
enum class Exercise {
    /// At expiry only. The closed form prices the same contract, which is what
    /// makes this the leg of I20's three-way agreement that can be checked
    /// against an exact answer.
    European,

    /// At any time up to expiry. The value function is then the solution of a
    /// linear complementarity problem — the equation above holds where holding
    /// is optimal, the value equals the payoff where exercising is, and the two
    /// regions are separated by a free boundary the solution finds for itself.
    ///
    /// v1 has no closed form for this and QuantLib is the oracle for it, as for
    /// everything else: `golden/american_vanilla.json` carries reference values
    /// from an independent lattice, and `golden/AMERICAN-SCHEMA.md` says what
    /// they are worth. Two exact statements hold it down besides — an American
    /// call on an underlying with no dividend yield is worth exactly its
    /// European counterpart, and every American value is at least its European
    /// one and at least its intrinsic value.
    American,
};

/// The grid, and how it is stepped.
///
/// The defaults are a grid good enough for one option priced once, at about
/// eight milliseconds: on the golden grid they hold every row to 3e-4 of the
/// underlying's own scale and the typical row to far less, which
/// `tests/test_pde.cpp` measures rather than claims. They are not a
/// recommendation for every input — a grid is a resolution, and what resolution
/// is enough depends on the option — and the sweeps in the tests deliberately
/// run coarser ones and state what those achieve. `PdeResult` reports the grid
/// that was actually built, and `PdeResult::resolution_in_sigmas` reports the
/// only number about it that predicts the error.
struct PdeSettings {
    /// Intervals across the log-spot domain, before it is stretched to put the
    /// spot exactly on a node. `PdeResult::space_intervals` is what was used.
    std::size_t space_intervals{1024};

    /// Steps from expiry back to today.
    std::size_t time_steps{512};

    /// Half the domain width, in units of the total volatility `sigma sqrt(T)`,
    /// measured outward from whichever of the spot, the strike and the forward
    /// is furthest out.
    ///
    /// The Dirichlet conditions at the two ends are the asymptotic values of the
    /// option, so the error they introduce is the probability of the terminal
    /// spot reaching the boundary at all, which falls like `exp(-alpha^2 / 2)`:
    /// 1.5e-8 at the default, and 3e-4 at 4, which is already larger than the
    /// discretisation error. Widening costs resolution — the domain is spread
    /// over the same number of nodes — so it is not free, and past about 6 it
    /// buys nothing. `tests/test_pde.cpp` holds the grid step fixed and widens
    /// the domain, which is the only way to see the boundary's contribution on
    /// its own rather than through the `dx` it changes.
    double half_width_sigmas{6.0};

    /// Crank-Nicolson steps replaced, at the start, by two fully implicit steps
    /// of half the size each.
    ///
    /// Two is Rannacher's prescription as Giles and Carter (2006) sharpened it,
    /// and it is the default because it is what restores second-order
    /// convergence for a payoff with a kink. Zero runs pure Crank-Nicolson,
    /// which `tests/test_pde.cpp` uses to show what the setting is for.
    std::size_t rannacher_steps{2};

    /// Start from the payoff averaged over each node's cell rather than sampled
    /// at the node itself.
    ///
    /// Both are second order, and the difference is the constant in front of the
    /// `dx^2`: the kink at the strike is where a difference operator has no
    /// accuracy at all, and averaging is what keeps its contribution on the same
    /// scale as the rest of the solution's. `tests/test_pde.cpp` measures both
    /// constants, which is the only reason this is a setting rather than simply
    /// what the solver does.
    bool smooth_payoff{true};

    Exercise exercise{Exercise::European};
};

/// The value at the spot, and what the grid says about its first two spot
/// derivatives.
struct PdeResult {
    double price{};

    /// `dV/dS` and `d2V/dS2` at the spot, from central differences in `x` at the
    /// node the spot sits on, converted out of log-space:
    ///
    ///     dV/dS   = u_x / S
    ///     d2V/dS2 = (u_xx - u_x) / S^2
    ///
    /// Both are second-order accurate in `dx`, and both are free: the solution at
    /// the two neighbouring nodes is already there. They are *not* independent of
    /// the price — the same three numbers produce all three — so they check the
    /// scheme's spatial accuracy rather than confirming the price.
    double delta{};
    double gamma{};

    // --- what was actually built ------------------------------------------

    std::size_t space_intervals{};  ///< Intervals, so `space_intervals + 1` nodes.
    std::size_t time_steps{};
    std::size_t spot_index{};     ///< The node holding the spot, exactly.
    double log_spot_step{};       ///< `dx`.
    double time_step{};           ///< `dtau`.
    double lower_log_spot{};      ///< `x` at node 0.
    double upper_log_spot{};      ///< `x` at the last node.

    /// `|nu| dx / sigma^2`, the mesh Peclet number, where `nu = r - q - sigma^2/2`.
    ///
    /// Above 2 the central difference on the first derivative overwhelms the
    /// second and the scheme's matrix stops being an M-matrix: the answer can
    /// oscillate node to node, and no assertion on the price alone would say why.
    /// It is reported rather than enforced, because a caller who has chosen a
    /// coarse grid deliberately should get their grid and the number that
    /// describes it. On the golden grid at the default settings it stays below
    /// 0.06, which `tests/test_pde.cpp` asserts.
    double mesh_peclet{};

    /// `dx / (sigma sqrt(T))`: how much of one standard deviation of the
    /// terminal log-price a single grid step covers.
    ///
    /// This, not `dx`, is the number the accuracy tracks. The scheme's error is
    /// second order in `dx`, but the constant in front of it is set by the
    /// curvature of the value function, whose only length scale is the total
    /// volatility — so a grid that is fine in log-spot and coarse in standard
    /// deviations is a coarse grid. Two rows of the golden file with the same
    /// `dx` and a tenfold difference in `sigma sqrt(T)` differ by about a
    /// hundredfold in error, and this is the number that says so in advance.
    double resolution_in_sigmas{};

    /// The strict diagonal dominance of the Crank-Nicolson matrix — the margin
    /// by which every row's diagonal exceeds its two neighbours. Positive is what
    /// makes the unpivoted Thomas sweep stable; see `touchstone/tridiagonal.hpp`.
    double dominance_margin{};
};

/// Throws `std::invalid_argument` if this grid cannot be built for these inputs.
///
/// The option and market are validated by `require_valid` in
/// `black_scholes.hpp` first, so the domain starts as the closed form's — the
/// comparison between the two is then a comparison rather than an accident — and
/// three conditions of this method's own are added to it.
///
///   - **The spot and the strike must be positive.** The grid is in `ln S`, and
///     neither `ln 0` nor a strike that is never reached is a thing a log grid
///     can represent. The closed form prices both exactly; this does not price
///     them at all.
///   - **The total volatility `sigma sqrt(T)` must be positive.** It is the
///     grid's width and its diffusion coefficient. At zero there is no equation
///     left to solve — the option is worth its discounted intrinsic value, which
///     is a limit the closed form takes exactly and a grid can only approach.
///   - **The whole domain must be representable as a spot.** The upper boundary
///     value is `exp(x_max - q tau)`, and `x_max` grows with the volatility and
///     the expiry. Beyond about 709 it overflows, and an infinite boundary
///     poisons every node inside it within one step.
///
/// Settings are checked too: at least two space intervals and one time step, a
/// positive half-width, and no more Rannacher steps than there are steps.
void require_valid(const EuropeanVanilla& option,
                   const BlackScholesMarket& market,
                   const PdeSettings& settings);

/// Price by Crank-Nicolson on a uniform log-spot grid, with a Rannacher start.
///
/// The spot lands exactly on a node, always: the domain is sized first and the
/// grid is then anchored at `ln S` and grown outward to cover it. So the price
/// is a solution value rather than an interpolation between two of them, and the
/// delta and gamma are central differences about the point they are wanted at.
/// The cost is that the node count can exceed `space_intervals` by one or two,
/// which `PdeResult::space_intervals` reports.
[[nodiscard]] PdeResult crank_nicolson(const EuropeanVanilla& option,
                                       const BlackScholesMarket& market,
                                       const PdeSettings& settings);

}  // namespace touchstone
