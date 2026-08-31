#include <touchstone/tridiagonal.hpp>

#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>

namespace touchstone {
namespace {

/// Every span the same non-zero length, and no aliasing between the two the
/// algorithm reads and writes in the same sweep.
void require_conformable(const Tridiagonal& matrix,
                         std::span<const double> rhs,
                         std::span<double> solution,
                         std::span<double> scratch)
{
    const std::size_t n = matrix.diag.size();
    if (n == 0) {
        throw std::invalid_argument("tridiagonal: the system is empty");
    }
    const auto same = [n](std::size_t other) { return other == n; };
    if (!same(matrix.sub.size()) || !same(matrix.sup.size()) || !same(rhs.size())
        || !same(solution.size()) || !same(scratch.size())) {
        throw std::invalid_argument(
            "tridiagonal: sub, diag, sup, rhs, solution and scratch must all have length "
            + std::to_string(n));
    }
}

}  // namespace

double dominance_margin(const Tridiagonal& matrix) noexcept
{
    const std::size_t n = matrix.diag.size();
    if (n == 0 || matrix.sub.size() != n || matrix.sup.size() != n) {
        return std::numeric_limits<double>::quiet_NaN();
    }

    double margin = std::numeric_limits<double>::infinity();
    for (std::size_t i = 0; i < n; ++i) {
        // The two entries outside the matrix contribute nothing: row 0 has no
        // subdiagonal and row n-1 no superdiagonal.
        const double below = (i == 0) ? 0.0 : std::abs(matrix.sub[i]);
        const double above = (i + 1 == n) ? 0.0 : std::abs(matrix.sup[i]);
        const double row = std::abs(matrix.diag[i]) - below - above;
        if (row < margin) {
            margin = row;
        }
    }
    return margin;
}

void solve_tridiagonal(const Tridiagonal& matrix,
                       std::span<const double> rhs,
                       std::span<double> solution,
                       std::span<double> scratch)
{
    require_conformable(matrix, rhs, solution, scratch);
    const std::size_t n = matrix.diag.size();

    // Forward elimination. `scratch` holds the eliminated superdiagonal and
    // `solution` the eliminated right-hand side, which the back substitution
    // then overwrites in place, reading each entry exactly once before it does.
    scratch[0] = matrix.sup[0] / matrix.diag[0];
    solution[0] = rhs[0] / matrix.diag[0];
    for (std::size_t i = 1; i < n; ++i) {
        const double pivot = matrix.diag[i] - matrix.sub[i] * scratch[i - 1];
        scratch[i] = matrix.sup[i] / pivot;
        solution[i] = (rhs[i] - matrix.sub[i] * solution[i - 1]) / pivot;
    }

    // Back substitution. solution[n-1] is already the answer there.
    for (std::size_t i = n - 1; i-- > 0;) {
        solution[i] -= scratch[i] * solution[i + 1];
    }
}

void solve_tridiagonal_projected(const Tridiagonal& matrix,
                                 std::span<const double> rhs,
                                 std::span<const double> constraint,
                                 ExerciseRegion region,
                                 std::span<double> solution,
                                 std::span<double> scratch)
{
    require_conformable(matrix, rhs, solution, scratch);
    if (constraint.size() != matrix.diag.size()) {
        throw std::invalid_argument("tridiagonal: the constraint must have the system's length");
    }
    const std::size_t n = matrix.diag.size();

    // `scratch` holds the pivots and `solution` the eliminated right-hand side,
    // which the substitution overwrites in place. Each entry of the latter is
    // read once, immediately before it is written, in both directions.
    if (region == ExerciseRegion::Lower) {
        // Eliminate from the high end down, so that the substitution runs from
        // the low end up — into the continuation region, out of the exercise
        // region. Every node is constrained before its higher neighbour needs it.
        scratch[n - 1] = matrix.diag[n - 1];
        solution[n - 1] = rhs[n - 1];
        for (std::size_t i = n - 1; i-- > 0;) {
            const double factor = matrix.sup[i] / scratch[i + 1];
            scratch[i] = matrix.diag[i] - factor * matrix.sub[i + 1];
            solution[i] = rhs[i] - factor * solution[i + 1];
        }

        solution[0] = std::fmax(solution[0] / scratch[0], constraint[0]);
        for (std::size_t i = 1; i < n; ++i) {
            solution[i] =
                std::fmax((solution[i] - matrix.sub[i] * solution[i - 1]) / scratch[i], constraint[i]);
        }
        return;
    }

    // The mirror image: ordinary Thomas elimination downward, substitution
    // upward, into the exercise region at the top.
    scratch[0] = matrix.diag[0];
    solution[0] = rhs[0];
    for (std::size_t i = 1; i < n; ++i) {
        const double factor = matrix.sub[i] / scratch[i - 1];
        scratch[i] = matrix.diag[i] - factor * matrix.sup[i - 1];
        solution[i] = rhs[i] - factor * solution[i - 1];
    }

    solution[n - 1] = std::fmax(solution[n - 1] / scratch[n - 1], constraint[n - 1]);
    for (std::size_t i = n - 1; i-- > 0;) {
        solution[i] =
            std::fmax((solution[i] - matrix.sup[i] * solution[i + 1]) / scratch[i], constraint[i]);
    }
}

}  // namespace touchstone
