// Tridiagonal systems: the Thomas algorithm, and its projected form.
//
// Tech-decision B3 puts a Thomas solver at the centre of the Crank-Nicolson
// scheme and rules out a linear-algebra dependency. The whole of it is two
// sweeps over three vectors, which is `solve_tridiagonal` below; the American
// constraint costs one comparison per node in the second sweep, which is
// `solve_tridiagonal_projected`.
//
// **Thomas does not pivot.** That is what makes it O(n) rather than O(n^2), and
// it is why every function here documents the same condition: the matrix must be
// diagonally dominant. Without dominance a pivot can be zero or tiny and the
// elimination divides by it; with it, no pivot ever falls below the row's own
// diagonal excess and the algorithm is backward stable. `dominance_margin`
// measures the condition rather than assuming it, and `pde.cpp` calls it once
// per grid and reports what it found.

#pragma once

#include <cstddef>
#include <span>

namespace touchstone {

/// The bands of a tridiagonal matrix of order `n`, as three spans of length `n`.
///
/// Row `i` reads `sub[i] u[i-1] + diag[i] u[i] + sup[i] u[i+1]`. The two entries
/// that fall outside the matrix — `sub[0]` and `sup[n-1]` — are never read.
/// They are still part of the span, so that the three bands index by row and a
/// caller never has to remember an offset.
struct Tridiagonal {
    std::span<const double> sub;
    std::span<const double> diag;
    std::span<const double> sup;

    [[nodiscard]] std::size_t size() const noexcept { return diag.size(); }
};

/// `min over rows of |diag| - |sub| - |sup|`, ignoring the two entries outside
/// the matrix.
///
/// Positive means strictly diagonally dominant by rows, which is the condition
/// under which Thomas needs no pivoting: every pivot the elimination forms is at
/// least this margin away from zero, and the growth factor is bounded by 2. A
/// margin of zero is the weakly dominant boundary, where the algorithm still
/// runs but nothing is promised; a negative margin means the answer may be
/// nonsense and no exception will say so.
///
/// Returns a NaN for an empty system.
[[nodiscard]] double dominance_margin(const Tridiagonal& matrix) noexcept;

/// Solve `A u = rhs` by the Thomas algorithm.
///
/// `solution` and `scratch` are both of length `n` and are written in full;
/// `scratch` carries the eliminated superdiagonal and exists so that a time
/// -stepping loop allocates once rather than once per step. `rhs` and `solution`
/// may not alias.
///
/// Throws `std::invalid_argument` if the spans are not all the same non-zero
/// length. It does not check dominance — see `dominance_margin` — because the
/// caller that builds the matrix knows why it is dominant and this function
/// would only be guessing.
void solve_tridiagonal(const Tridiagonal& matrix,
                       std::span<const double> rhs,
                       std::span<double> solution,
                       std::span<double> scratch);

/// Which end of the index range the constraint binds on, for the projected
/// solver below.
enum class ExerciseRegion {
    /// A contiguous set of *low* indices: an American put, exercised below the
    /// free boundary, on a grid whose index increases with the spot.
    Lower,
    /// A contiguous set of *high* indices: an American call on an underlying
    /// that pays a dividend yield, exercised above the free boundary.
    Upper,
};

/// Solve the linear complementarity problem
///
///     A u >= rhs,   u >= constraint,   (A u - rhs) . (u - constraint) = 0
///
/// by Brennan and Schwartz's method: eliminate from the far end of the range,
/// then substitute *towards* it, taking `max(., constraint)` at every node as it
/// goes.
///
/// **It is exact, not approximate, on one condition:** the set of nodes where
/// the constraint binds must be contiguous and must sit at the `region` end of
/// the range. Jaillet, Lamberton and Lapeyre (1990) proved that under that
/// condition the sweep returns the LCP solution itself. The condition is the
/// standard structure of a vanilla American exercise boundary — a put is
/// exercised below a single critical spot, a call above one — and `pde.cpp`
/// chooses `region` from the option type for exactly that reason. Hand it a
/// problem whose exercise region is not one-sided and it will return something
/// plausible and wrong, which is why the condition is stated here rather than
/// checked: nothing in the bands can be inspected to find out.
///
/// The direction of the elimination is the whole trick. Substituting *away* from
/// the exercise region would apply the constraint to nodes whose neighbour had
/// not yet been constrained, and the two sweeps would disagree about where the
/// boundary is.
///
/// Same span rules and same throw as `solve_tridiagonal`.
void solve_tridiagonal_projected(const Tridiagonal& matrix,
                                 std::span<const double> rhs,
                                 std::span<const double> constraint,
                                 ExerciseRegion region,
                                 std::span<double> solution,
                                 std::span<double> scratch);

}  // namespace touchstone
