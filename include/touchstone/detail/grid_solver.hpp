// The finite-difference grid behind `crank_nicolson`, as an object that can be
// stepped and read.
//
// `crank_nicolson` builds one of these, runs it to today and reads three numbers
// off it. The class is here for the callers that want more than three numbers:
// the solution at every node, after any number of steps, is the surface a
// heatmap of the method draws, and stepping it one level at a time is how that
// surface is read without storing all of it.
//
// Internal rather than public: the public face is `touchstone/pde.hpp`. Nothing
// here validates beyond what the constructor does by calling `require_valid`.

#pragma once

#include <touchstone/pde.hpp>
#include <touchstone/tridiagonal.hpp>

#include <cstddef>
#include <span>
#include <vector>

namespace touchstone::detail {

/// A uniform grid in `x = ln S`, anchored so that the spot is a node.
struct LogSpotGrid {
    std::size_t intervals{};   ///< `n`: nodes are 0..n.
    std::size_t spot_index{};  ///< `i0`, with `x(i0) == ln S` exactly.
    double step{};             ///< `dx`.
    double log_spot{};         ///< `ln S`.

    [[nodiscard]] double x(std::size_t i) const noexcept
    {
        // Written as an offset from the anchor rather than from node zero, so
        // that x(spot_index) is ln S to the last bit and the price is a solution
        // value rather than an interpolation.
        return log_spot + (static_cast<double>(i) - static_cast<double>(spot_index)) * step;
    }

    [[nodiscard]] double lower() const noexcept { return x(0); }
    [[nodiscard]] double upper() const noexcept { return x(intervals); }
};

/// Crank-Nicolson on a uniform log-spot grid with a Rannacher start, for a
/// European or an American vanilla. The two share every line that is not early
/// exercise itself: the projected sweep in place of the plain one, and the
/// boundary values raised to what immediate exercise pays.
template <Exercise E>
class GridSolver {
public:
    /// Validates by `require_valid` in `touchstone/pde.hpp`, then builds the
    /// grid, the payoff at expiry and both of the scheme's matrices — the fully
    /// implicit one for the Rannacher start and the Crank-Nicolson one for every
    /// step after it. Neither is built again.
    GridSolver(const Vanilla<E>& option, const BlackScholesMarket& market, const PdeSettings& settings);

    /// One time step back towards today: two implicit half-steps while the
    /// Rannacher start lasts, one Crank-Nicolson step after it. Returns false,
    /// and does nothing, once the solution has reached today.
    bool advance();

    /// Every remaining step.
    void solve();

    /// Time steps taken so far, out of `PdeSettings::time_steps`.
    [[nodiscard]] std::size_t steps_taken() const noexcept { return taken_; }

    /// The time to expiry the solution currently describes: zero before the
    /// first step, the option's expiry after the last.
    [[nodiscard]] double time_to_expiry() const noexcept { return tau_; }

    /// The solution at every node, `x(0)` first, at `time_to_expiry()`.
    [[nodiscard]] std::span<const double> values() const noexcept { return value_; }

    [[nodiscard]] const LogSpotGrid& grid() const noexcept { return grid_; }

    /// The price, delta and gamma at the spot, read off the solution as it
    /// stands, and the description of the grid that produced them. The price is
    /// today's once `advance` has returned false.
    [[nodiscard]] PdeResult result() const;

private:
    /// One of the scheme's two matrices, `I - theta dt L`, and the step it takes.
    struct Stepping {
        double theta{};
        double dt{};
        std::vector<double> sub;
        std::vector<double> diag;
        std::vector<double> sup;

        [[nodiscard]] Tridiagonal matrix() const noexcept { return Tridiagonal{sub, diag, sup}; }
    };

    [[nodiscard]] Stepping build(double theta, double dt) const;
    [[nodiscard]] double boundary_value(double log_spot_node, bool deep_in_the_money, double tau) const;
    void step(const Stepping& stepping, double tau_new);

    Vanilla<E> option_;
    BlackScholesMarket market_;
    PdeSettings settings_;
    LogSpotGrid grid_;
    double dtau_{};

    // The spatial operator `L u = a u_{i-1} + b u_i + c u_{i+1}`, constant in x
    // and in tau.
    double nu_{};  ///< `r - q - sigma^2/2`.
    double a_{};
    double b_{};
    double c_{};

    Stepping implicit_;  ///< Backward Euler at half a step, for the Rannacher start.
    Stepping crank_;     ///< Crank-Nicolson at a whole step.
    double dominance_{};

    std::vector<double> value_;
    std::vector<double> constraint_;  ///< The payoff at interior nodes. American only.
    std::vector<double> rhs_;
    std::vector<double> solution_;
    std::vector<double> scratch_;

    std::size_t taken_{0};
    double tau_{0.0};
};

extern template class GridSolver<Exercise::European>;
extern template class GridSolver<Exercise::American>;

}  // namespace touchstone::detail
