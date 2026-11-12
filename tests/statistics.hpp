// The one statistical idea these tests need, in one place.
//
// A Monte Carlo estimate is not compared with a closed form the way two
// closed forms are compared. It is compared in units of its own standard
// error, and a sweep of thousands of such comparisons is then a sample that
// should look standard normal — which is a much stronger statement than any
// one comparison, and the only honest way to test a whole grid at once.

#pragma once

#include <cstddef>
#include <string>
#include <vector>

namespace touchstone::testing {

/// What a sample of z-scores looks like, and what it should look like.
struct Standardised {
    std::size_t count{};
    double mean{};
    double standard_deviation{};
    double worst{};        ///< Largest |z|.
    std::string worst_at;  ///< The row that produced it.
    std::size_t beyond_three{};
    double expected_beyond_three{};

    /// The largest |z| a sample of this size should reach. Not 3: three
    /// standard errors is the right bound for *one* comparison, and a sweep of
    /// n of them expects n * 0.0027 of its rows to exceed it — twenty of them
    /// on a grid of seven thousand. This is the two-sided normal quantile that
    /// leaves a one-in-ten-thousand chance of *any* row in the sample exceeding
    /// it, which is what "three standard errors" becomes when it is asked of
    /// thousands of rows simultaneously.
    double worst_bound{};

    [[nodiscard]] std::string report(const char* what) const;

    /// `k` standard errors of a mean of `count` standard normals: `k / sqrt(n)`.
    [[nodiscard]] double mean_bound(double k) const noexcept;

    /// `k` standard errors of the sample standard deviation of `count`
    /// standard normals: `k / sqrt(2n)`.
    [[nodiscard]] double standard_deviation_bound(double k) const noexcept;
};

/// Summarise a sample of z-scores. `labels` names the rows, for the report.
/// A sample's mean and its variance on `n - 1` degrees of freedom, two-pass.
struct Moments {
    double mean{};
    double variance{};
};

[[nodiscard]] Moments moments(const std::vector<double>& values);

/// The two-sided normal quantile that leaves probability `family` of any of
/// `count` independent standard normals exceeding it: Bonferroni's bound.
[[nodiscard]] double bonferroni_bound(double family, double count);

/// A count within `k` of its Poisson standard deviations of what was expected,
/// plus one for the discreteness of a small count.
[[nodiscard]] bool within_poisson(double observed, double expected, double k);

[[nodiscard]] Standardised standardise(const std::vector<double>& z,
                                       const std::vector<std::string>& labels);

}  // namespace touchstone::testing
