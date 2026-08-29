// Reading `golden/bs_vanilla.json`, and the one comparison rule its schema
// permits.

#pragma once

#include <touchstone/black_scholes.hpp>

#include <cstddef>
#include <string>
#include <vector>

namespace touchstone::testing {

/// One row of the golden file: the inputs, and what QuantLib returned for them.
struct GoldenCase {
    EuropeanVanilla option{};
    BlackScholesMarket market{};
    PriceAndGreeks reference{};
    int expiry_days{};
    std::string label{};  ///< Non-empty only in the edge block.
};

struct GoldenFile {
    std::string path;
    std::string schema;
    std::string oracle_version;
    double tolerance_cases{};
    double tolerance_edge_cases{};
    std::size_t declared_cases{};
    std::size_t declared_edge_cases{};
    std::vector<GoldenCase> cases;
    std::vector<GoldenCase> edge_cases;
};

/// Parsed once, on first use. Throws `std::runtime_error` if the file is
/// missing, malformed, or carries a schema id other than the one these tests
/// were written against — a file that has changed its meaning must stop the
/// tests rather than be compared against as though it had not.
const GoldenFile& golden_file();

/// `golden/SCHEMA.md`'s comparison rule: relative above 1.0, absolute below it.
///
///     scale = max(|reference|, 1.0)
///     error = |actual - reference| / scale
///
/// A deep out-of-the-money price is the residue of cancelling two numbers of
/// order S, so its absolute accuracy is a few ulps of S however small the true
/// value is; 106 rows of the file are in fact slightly negative. A relative
/// comparison there would measure the noise floor and nothing else.
///
/// A NaN, or an infinity where the reference is finite, returns infinity rather
/// than a comparison that quietly succeeds.
[[nodiscard]] double scaled_error(double actual, double reference) noexcept;

/// The worst scaled error over a sweep, and the row that produced it.
class Worst {
public:
    void observe(double actual, double reference, const GoldenCase& source);

    [[nodiscard]] double error() const noexcept { return error_; }
    [[nodiscard]] std::string describe(const char* field) const;

private:
    double error_{0.0};
    double actual_{0.0};
    double reference_{0.0};
    GoldenCase source_{};
    bool seen_{false};
};

/// The inputs of a row, on one line, at full precision.
[[nodiscard]] std::string describe(const GoldenCase& row);

}  // namespace touchstone::testing
