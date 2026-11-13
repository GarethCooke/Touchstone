#include <touchstone/tridiagonal.hpp>

#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>

namespace touchstone {
namespace {

/// Three bands of one non-zero length.
[[nodiscard]] bool bands_conform(const Tridiagonal& matrix) noexcept
{
    const std::size_t n = matrix.diag.size();
    return n > 0 && matrix.sub.size() == n && matrix.sup.size() == n;
}

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
    if (!bands_conform(matrix) || !same(rhs.size()) || !same(solution.size())
        || !same(scratch.size())) {
        throw std::invalid_argument(
            "tridiagonal: sub, diag, sup, rhs, solution and scratch must all have length "
            + std::to_string(n));
    }
}

}  // namespace

double dominance_margin(const Tridiagonal& matrix) noexcept
{
    if (!bands_conform(matrix)) {
        return std::numeric_limits<double>::quiet_NaN();
    }
    const std::size_t n = matrix.diag.size();

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

namespace {

/// The Thomas algorithm, once, for all three of its uses here.
///
/// Forward elimination from one end of the index range, back substitution from
/// the other, with `project` applied to each value as the substitution produces
/// it. The plain solve projects nothing. Brennan and Schwartz's projected solve
/// takes `max(value, constraint)`, and the direction is the whole of the
/// difference between a put and a call: `Reversed` runs the same sweep over the
/// mirrored index range, eliminating from the high end and substituting from
/// the low one, where the two bands swap roles — what was the row below is now
/// the row before.
///
/// `scratch` holds the eliminated coupling to the next row and `solution` the
/// eliminated right-hand side, which the substitution then overwrites in place,
/// reading each entry exactly once before it does.
template <bool Reversed, class Project>
void sweep(const Tridiagonal& matrix,
           std::span<const double> rhs,
           std::span<double> solution,
           std::span<double> scratch,
           Project project)
{
    const std::size_t n = matrix.diag.size();
    // Row `k` in sweep order, and its coupling to the row before it and after it.
    const auto row = [n](std::size_t k) { return Reversed ? n - 1 - k : k; };
    const auto before = [&](std::size_t k) {
        return Reversed ? matrix.sup[row(k)] : matrix.sub[row(k)];
    };
    const auto after = [&](std::size_t k) {
        return Reversed ? matrix.sub[row(k)] : matrix.sup[row(k)];
    };

    scratch[row(0)] = after(0) / matrix.diag[row(0)];
    solution[row(0)] = rhs[row(0)] / matrix.diag[row(0)];
    for (std::size_t k = 1; k < n; ++k) {
        const double pivot = matrix.diag[row(k)] - before(k) * scratch[row(k - 1)];
        scratch[row(k)] = after(k) / pivot;
        solution[row(k)] = (rhs[row(k)] - before(k) * solution[row(k - 1)]) / pivot;
    }

    // The last row eliminated is already solved, up to the projection.
    solution[row(n - 1)] = project(row(n - 1), solution[row(n - 1)]);
    for (std::size_t k = n - 1; k-- > 0;) {
        solution[row(k)] =
            project(row(k), solution[row(k)] - scratch[row(k)] * solution[row(k + 1)]);
    }
}

}  // namespace

void solve_tridiagonal(const Tridiagonal& matrix,
                       std::span<const double> rhs,
                       std::span<double> solution,
                       std::span<double> scratch)
{
    require_conformable(matrix, rhs, solution, scratch);
    sweep<false>(matrix, rhs, solution, scratch, [](std::size_t, double value) { return value; });
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
    const auto at_least_constraint = [constraint](std::size_t i, double value) {
        return std::fmax(value, constraint[i]);
    };

    // The substitution must start in the exercise region and run out of it, so
    // that every node is constrained before its neighbour on the continuation
    // side needs it. A put is exercised at low indices: eliminate from the high
    // end, substitute from the low one. A call is exercised at high indices:
    // Thomas's own order.
    if (region == ExerciseRegion::Lower) {
        sweep<true>(matrix, rhs, solution, scratch, at_least_constraint);
    } else {
        sweep<false>(matrix, rhs, solution, scratch, at_least_constraint);
    }
}

}  // namespace touchstone
