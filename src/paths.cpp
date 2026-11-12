#include <touchstone/paths.hpp>

#include <touchstone/detail/checks.hpp>
#include <touchstone/detail/path_generator.hpp>
#include <touchstone/detail/scales.hpp>

#include <cmath>
#include <stdexcept>

namespace touchstone {
namespace detail {

GbmStep::GbmStep(Scheme scheme, double drift, double vol, double dt) noexcept
    : scheme_(scheme),
      dt_(dt),
      drift_term_(scheme == Scheme::ExactTerminal ? log_drift_time(drift, vol, dt)
                                                  : drift_time(drift, dt)),
      diffusion_(total_volatility(vol, dt))
{
}

double GbmStep::factor(double z) const noexcept
{
    if (scheme_ == Scheme::ExactTerminal) {
        return std::exp(drift_term_ + diffusion_ * z);
    }
    return 1.0 + drift_term_ + diffusion_ * z;
}

PathGenerator::PathGenerator(std::uint32_t seed, const GbmStep& step) noexcept
    : rng_(seed),
      step_(step),
      sqrt_dt_(std::sqrt(step.dt()))
{
}

void PathGenerator::draw(std::span<double> normals) noexcept
{
    for (double& z : normals) {
        z = rng_.next_normal();
    }
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
    // As for a Brownian path, the normals are drawn into the path itself and
    // each is read, as the factor's argument, before its slot is written.
    path[0] = spot;
    const std::span<double> steps = path.subspan(1);
    draw(steps);
    walk(step_, spot, steps, 1.0, [steps](std::size_t k, double value) { steps[k] = value; });
}

}  // namespace detail

namespace {

[[nodiscard]] double step_of(const PathGrid& grid, std::size_t values) noexcept
{
    return grid.horizon / static_cast<double>(values - 1);
}

}  // namespace

void require_valid(const PathGrid& grid, std::size_t values)
{
    if (values < 2) {
        throw std::invalid_argument(
            "paths: a path needs at least two values, a start and one step");
    }
    if (!detail::is_finite_positive(grid.horizon)) {
        throw std::invalid_argument("paths: horizon must be finite and positive");
    }
}

void require_valid(const PathGrid& grid, const GbmDynamics& dynamics, std::size_t values)
{
    require_valid(grid, values);
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
    const double dt = step_of(grid, values);
    if (!std::isfinite(detail::drift_time(dynamics.drift, dt))) {
        throw std::invalid_argument("paths: drift times the step overflows a double");
    }
    if (!std::isfinite(detail::total_variance(dynamics.vol, dt))) {
        throw std::invalid_argument(
            "paths: the variance over one step, (vol sqrt(dt))^2, overflows a double");
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

}  // namespace touchstone
