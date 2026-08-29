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
};

/// Summarise a sample of z-scores. `labels` names the rows, for the report.
[[nodiscard]] Standardised standardise(const std::vector<double>& z,
                                       const std::vector<std::string>& labels);

}  // namespace touchstone::testing
