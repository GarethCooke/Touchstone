// Sample paths of Brownian motion and geometric Brownian motion, on the shared
// generator of `docs/rng.md`.
//
// A Brownian path is a running sum of `√dt Z`. A geometric Brownian motion path
// is that sum's exponential, stepped exactly, or the stochastic differential
// equation itself stepped by Euler-Maruyama — and both schemes are driven by the
// *same* normals, so that two paths from one seed differ by discretisation and
// nothing else, which is a number rather than an opinion.
//
// Each function writes a whole path into a span the caller owns: `path.size()`
// values on the grid `{0, dt, 2dt, ..., T}` with `dt = T / (path.size() - 1)`,
// one normal taken from the seeded stream per step, in order. A finer grid is
// therefore a different path rather than a refinement of the coarse one; a
// caller that wants a coarse path and its own midpoints asks for the fine grid
// and strides through it.
//
// `gbm_paths`, at the end, steps a whole sample from normals the caller
// supplies, one run of them per path, by the same step.
//
// The demos draw their paths from these functions, so a path on the page and a
// path in a test are the same numbers: same seed, same path.
// `golden/paths-known-answers.json` is what holds the two to each other.

#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace touchstone {

/// How a geometric Brownian motion is stepped from one standard normal per step.
enum class Scheme {
    /// The exact transition law over each step:
    /// `S_(k+1) = S_k exp((mu - sigma^2/2) dt + sigma sqrt(dt) Z_k)`.
    /// The solution of the equation evaluated at the grid points, so there is no
    /// discretisation error at any step count and the path never goes negative.
    /// Over a single step of the whole expiry it is the terminal law sampled
    /// exactly, one normal per path, which is how `monte_carlo` uses it.
    ExactTerminal,

    /// Euler-Maruyama: `S_(k+1) = S_k (1 + mu dt + sigma sqrt(dt) Z_k)`. Wrong on
    /// purpose, by an amount that shrinks with dt at a rate the tests pin down.
    ///
    /// It can go negative, and is not clipped: a step's factor is negative
    /// whenever its `Z` is far enough below zero, and a scheme that quietly
    /// floored the spot at zero would converge at a different rate than the one
    /// the tests claim.
    EulerMaruyama,
};

/// The seeded grid a path is drawn on. The number of steps is the caller's span,
/// less its starting value.
struct PathGrid {
    std::uint32_t seed{1};  ///< Same seed, same path.
    double horizon{1.0};    ///< T: the path runs over [0, T].
};

/// The process a geometric Brownian motion path follows.
struct GbmDynamics {
    double spot{};   ///< S_0 >= 0.
    double drift{};  ///< mu, the drift of S. Risk-neutral pricing puts r - q here.
    double vol{};    ///< sigma >= 0.
};

/// Throws `std::invalid_argument` unless a path of `values` values can be drawn
/// on this grid: at least two values — a start and one step — and a finite,
/// positive horizon.
void require_valid(const PathGrid& grid, std::size_t values);

/// The same, and the process: a finite, non-negative spot and volatility, a
/// finite drift, and a step on which `mu dt` and `(sigma sqrt(dt))^2` are both
/// representable.
///
/// Accepting the inputs is a promise that no value of the path is a NaN. A path
/// may still saturate: an exact step whose exponent overflows is an infinity,
/// one whose exponent underflows is a zero, and zero is absorbing — a process
/// that reaches it stays there, in both schemes, which is also what keeps an
/// infinity times a zero from ever being formed.
void require_valid(const PathGrid& grid, const GbmDynamics& dynamics, std::size_t values);

/// `W` on the grid: `path[0] = 0` and `path[k+1] = path[k] + sqrt(dt) Z_k`.
void brownian_path(const PathGrid& grid, std::span<double> path);

/// `S` on the grid, from `path[0] = S_0`, under `scheme`, driven by the normals
/// `brownian_path` draws from the same grid.
void gbm_path(const PathGrid& grid,
              const GbmDynamics& dynamics,
              Scheme scheme,
              std::span<double> path);

// --- A sample of paths, from normals the caller supplies ----------------------
//
// A sample is many paths stepped from one stream: path `p` takes the `p`-th run
// of `steps` normals. Drawn from the shared generator — `steps * P` normals from
// one seed — path 0 is therefore `gbm_path`'s path at that seed, and another
// seed moves every path of the sample rather than shifting it along by one.
// The normals are an argument rather than a seed so that both schemes can be
// stepped from the same draws, and so that increments recorded elsewhere — an
// experiment's, say — can be stepped by this library and compared.

/// The grid a sample is stepped on: a horizon and a step count, and no seed,
/// because nothing is drawn.
struct StepGrid {
    double horizon{1.0};   ///< T: each path runs over [0, T].
    std::size_t steps{1};  ///< Steps per path; dt = T / steps.
};

/// Throws `std::invalid_argument` unless: `steps >= 1`; the horizon is finite and
/// positive; the process is one `require_valid(PathGrid, GbmDynamics, steps + 1)`
/// accepts; `normals.size()` is a whole number of runs of `steps`; every normal
/// is finite; and `values` is `steps + 1` for each run, the start included.
///
/// The normals must be finite because an accepted input never produces a NaN:
/// at a volatility of zero an infinite normal would make a step's exponent
/// `0 * inf`.
void require_valid(const StepGrid& grid,
                   const GbmDynamics& dynamics,
                   std::span<const double> normals,
                   std::size_t values);

/// A sample of paths of `S`, path-major. Path `p` is `S` stepped under `scheme`
/// from `S_0` by `normals[p*steps, (p+1)*steps)` and written to
/// `paths[p*(steps+1), (p+1)*(steps+1))`, exactly as `gbm_path` steps its one
/// path from the normals it draws. No normals is an empty sample.
void gbm_paths(const StepGrid& grid,
               const GbmDynamics& dynamics,
               Scheme scheme,
               std::span<const double> normals,
               std::span<double> paths);

/// The same sample, in a vector of the size it needs, validated before anything
/// is allocated.
[[nodiscard]] std::vector<double> gbm_paths(const StepGrid& grid,
                                            const GbmDynamics& dynamics,
                                            Scheme scheme,
                                            std::span<const double> normals);

}  // namespace touchstone
