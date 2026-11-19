#include <touchstone/paths.hpp>

#include <touchstone/detail/checks.hpp>
#include <touchstone/detail/path_generator.hpp>
#include <touchstone/detail/scales.hpp>

#include <array>
#include <cmath>
#include <stdexcept>

namespace touchstone {
namespace detail {

namespace {

/// `path[0] = spot`, then the value after each step, one step per normal: the
/// loop behind one path of `gbm_path` and every path of `gbm_paths`.
///
/// `normals` may be the rest of `path` itself, as `PathGenerator::write_gbm`
/// passes it: each normal is read, as the factor's argument, before the value
/// it steps to is written into its slot.
void write_gbm_steps(const GbmStep& step,
                     double spot,
                     std::span<const double> normals,
                     std::span<double> path) noexcept
{
    path[0] = spot;
    const std::span<double> after = path.subspan(1);
    walk(step, std::array{spot}, normals, 1.0,
         [after](std::size_t k, const std::array<double, 1>& value) { after[k] = value[0]; });
}

}  // namespace

PathGenerator::PathGenerator(std::uint32_t seed, const GbmStep& step) noexcept
    : rng_(seed),
      step_(step),
      sqrt_dt_(std::sqrt(step.dt()))
{
}

void PathGenerator::write_brownian(std::span<double> path) noexcept
{
    // The normals are drawn into the path itself, one place along, and each is
    // then replaced by the value it steps to: every slot is read once, as a
    // normal, immediately before it is written as a value.
    path[0] = 0.0;
    draw(path.subspan(1));
    for (std::size_t k = 1; k < path.size(); ++k) {
        path[k] = path[k - 1] + sqrt_dt_ * path[k];
    }
}

void PathGenerator::write_gbm(double spot, std::span<double> path) noexcept
{
    // As for a Brownian path, the normals are drawn into the path itself.
    const std::span<double> steps = path.subspan(1);
    draw(steps);
    write_gbm_steps(step_, spot, steps, path);
}

}  // namespace detail

namespace {

[[nodiscard]] double step_of(double horizon, std::size_t steps) noexcept
{
    return horizon / static_cast<double>(steps);
}

[[nodiscard]] double step_of(const PathGrid& grid, std::size_t values) noexcept
{
    return step_of(grid.horizon, values - 1);
}

[[nodiscard]] double step_of(const StepGrid& grid) noexcept
{
    return step_of(grid.horizon, grid.steps);
}

void require_valid_horizon(double horizon)
{
    if (!detail::is_finite_positive(horizon)) {
        throw std::invalid_argument("paths: horizon must be finite and positive");
    }
}

/// The process, stepped by `dt`: what both kinds of grid require of it.
void require_valid_process(const GbmDynamics& dynamics, double dt)
{
    if (!detail::is_finite_non_negative(dynamics.spot)) {
        throw std::invalid_argument("paths: spot must be finite and non-negative");
    }
    if (!std::isfinite(dynamics.drift)) {
        throw std::invalid_argument("paths: drift must be finite");
    }
    if (!detail::is_finite_non_negative(dynamics.vol)) {
        throw std::invalid_argument("paths: vol must be finite and non-negative");
    }
    // The two products a step forms. Either one infinite would make the exact
    // step's exponent `inf - inf` for some draw, which is a NaN.
    if (!std::isfinite(detail::drift_time(dynamics.drift, dt))) {
        throw std::invalid_argument("paths: drift times the step overflows a double");
    }
    if (!std::isfinite(detail::total_variance(dynamics.vol, dt))) {
        throw std::invalid_argument(
            "paths: the variance over one step, (vol sqrt(dt))^2, overflows a double");
    }
}

}  // namespace

void require_valid(const PathGrid& grid, std::size_t values)
{
    if (values < 2) {
        throw std::invalid_argument(
            "paths: a path needs at least two values, a start and one step");
    }
    require_valid_horizon(grid.horizon);
}

void require_valid(const PathGrid& grid, const GbmDynamics& dynamics, std::size_t values)
{
    require_valid(grid, values);
    require_valid_process(dynamics, step_of(grid, values));
}

namespace {

/// The values one path of a sample holds: its start and one per step.
[[nodiscard]] std::size_t path_values(const StepGrid& grid) noexcept
{
    return grid.steps + 1;
}

/// Everything `require_valid` checks but the room the caller made, and the
/// room the sample needs.
[[nodiscard]] std::size_t validated_values(const StepGrid& grid,
                                           const GbmDynamics& dynamics,
                                           std::span<const double> normals)
{
    if (grid.steps < 1) {
        throw std::invalid_argument("paths: a sample needs at least one step per path");
    }
    require_valid_horizon(grid.horizon);
    require_valid_process(dynamics, step_of(grid));
    if (normals.size() % grid.steps != 0) {
        throw std::invalid_argument(
            "paths: the normals must be a whole number of runs of steps, one run per path");
    }
    for (const double z : normals) {
        if (!std::isfinite(z)) {
            throw std::invalid_argument("paths: every normal must be finite");
        }
    }
    return (normals.size() / grid.steps) * path_values(grid);
}

/// Path `p` of the sample from the `p`-th run of normals, for every run. The
/// inputs have been validated.
void step_sample(const StepGrid& grid,
                 const GbmDynamics& dynamics,
                 Scheme scheme,
                 std::span<const double> normals,
                 std::span<double> paths) noexcept
{
    const detail::GbmStep step(scheme, dynamics.drift, dynamics.vol, step_of(grid));
    const std::size_t values = path_values(grid);
    for (std::size_t p = 0; p * grid.steps < normals.size(); ++p) {
        detail::write_gbm_steps(step, dynamics.spot, normals.subspan(p * grid.steps, grid.steps),
                                paths.subspan(p * values, values));
    }
}

}  // namespace

void require_valid(const StepGrid& grid,
                   const GbmDynamics& dynamics,
                   std::span<const double> normals,
                   std::size_t values)
{
    if (values != validated_values(grid, dynamics, normals)) {
        throw std::invalid_argument(
            "paths: the sample needs steps + 1 values for each run of steps normals");
    }
}

void brownian_path(const PathGrid& grid, std::span<double> path)
{
    require_valid(grid, path.size());
    // The process plays no part in a Brownian path; a generator needs one, and
    // this one is never asked for a factor.
    detail::PathGenerator generator(
        grid.seed, detail::GbmStep(Scheme::ExactTerminal, 0.0, 0.0, step_of(grid, path.size())));
    generator.write_brownian(path);
}

void gbm_path(const PathGrid& grid,
              const GbmDynamics& dynamics,
              Scheme scheme,
              std::span<double> path)
{
    require_valid(grid, dynamics, path.size());
    detail::PathGenerator generator(
        grid.seed,
        detail::GbmStep(scheme, dynamics.drift, dynamics.vol, step_of(grid, path.size())));
    generator.write_gbm(dynamics.spot, path);
}

void gbm_paths(const StepGrid& grid,
               const GbmDynamics& dynamics,
               Scheme scheme,
               std::span<const double> normals,
               std::span<double> paths)
{
    require_valid(grid, dynamics, normals, paths.size());
    step_sample(grid, dynamics, scheme, normals, paths);
}

std::vector<double> gbm_paths(const StepGrid& grid,
                              const GbmDynamics& dynamics,
                              Scheme scheme,
                              std::span<const double> normals)
{
    std::vector<double> paths(validated_values(grid, dynamics, normals));
    step_sample(grid, dynamics, scheme, normals, paths);
    return paths;
}

}  // namespace touchstone
