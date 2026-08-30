#include "statistics.hpp"

#include <touchstone/normal.hpp>

#include <cmath>
#include <iomanip>
#include <sstream>
#include <stdexcept>

namespace touchstone::testing {

Standardised standardise(const std::vector<double>& z, const std::vector<std::string>& labels)
{
    if (z.empty()) {
        throw std::runtime_error("standardise: empty sample");
    }
    if (labels.size() != z.size()) {
        throw std::runtime_error("standardise: one label per value, please");
    }

    Standardised result{};
    result.count = z.size();

    const double n = static_cast<double>(z.size());
    double sum = 0.0;
    for (const double value : z) {
        sum += value;
    }
    result.mean = sum / n;

    double sum_squares = 0.0;
    for (const double value : z) {
        const double centred = value - result.mean;
        sum_squares += centred * centred;
    }
    result.standard_deviation = std::sqrt(sum_squares / (n - 1.0));

    for (std::size_t i = 0; i < z.size(); ++i) {
        const double magnitude = std::abs(z[i]);
        if (magnitude > result.worst) {
            result.worst = magnitude;
            result.worst_at = labels[i];
        }
        if (magnitude > 3.0) {
            ++result.beyond_three;
        }
    }

    // 2 N(-3): the two-sided tail beyond three standard errors, 0.0027.
    result.expected_beyond_three = n * 2.0 * norm_cdf(-3.0);

    // Bonferroni: a one-in-ten-thousand chance that any of the n rows exceeds
    // this, if every row really is a standard normal draw.
    result.worst_bound = -norm_inv(1e-4 / (2.0 * n));

    return result;
}

std::string Standardised::report(const char* what) const
{
    const double n = static_cast<double>(count);
    std::ostringstream out;
    out << std::fixed << std::setprecision(3);
    out << what << ": " << count << " rows in standard-error units"
        << "\n    mean          " << mean << "   (0 +/- " << 1.0 / std::sqrt(n) << " expected)"
        << "\n    sd            " << standard_deviation << "   (1 +/- "
        << 1.0 / std::sqrt(2.0 * n) << " expected)"
        << "\n    beyond 3 SE   " << beyond_three << "   (" << expected_beyond_three << " +/- "
        << std::sqrt(expected_beyond_three) << " expected)"
        << "\n    worst |z|     " << worst << "   (bound " << worst_bound << ")"
        << "\n    worst row     " << worst_at;
    return out.str();
}

}  // namespace touchstone::testing
