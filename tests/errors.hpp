// How the tests measure an error, and how a sweep remembers the largest one.
//
// Two scales, one rule. `golden/SCHEMA.md` compares relative to the reference
// above 1 and absolutely below it, which is right for a closed form whose noise
// floor is a few ulps of its own size. A finite-difference grid's error is a
// fraction of the underlying's scale instead, so the grid's sweeps put the spot
// where SCHEMA.md puts 1. Both are `scaled_error`, with a different floor.

#pragma once

#include <algorithm>
#include <cmath>
#include <limits>
#include <string>

namespace touchstone::testing {

/// `|actual - reference| / max(|reference|, floor)`.
///
/// A NaN, or an infinity where the reference is finite, returns infinity rather
/// than a comparison that quietly succeeds; two infinities of the same sign
/// agree.
[[nodiscard]] inline double scaled_error(double actual, double reference, double floor = 1.0) noexcept
{
    if (actual == reference) {
        return 0.0;
    }
    if (!std::isfinite(actual) || !std::isfinite(reference)) {
        return std::numeric_limits<double>::infinity();
    }
    return std::abs(actual - reference) / std::max(std::abs(reference), floor);
}

/// `|actual - reference| / |reference|`, for a reference known not to be small.
[[nodiscard]] inline double relative_error(double actual, double reference) noexcept
{
    return std::abs(actual - reference) / std::abs(reference);
}

/// The largest value a sweep has seen, and the row it came from. `describe` of
/// the row says where, found by argument lookup for whichever row type the
/// sweep walks.
template <class Row>
class Largest {
public:
    /// Keep `value` and `row` if `value` is the largest so far. True if it was.
    bool observe(double value, const Row& row)
    {
        if (!(value > value_)) {
            return false;
        }
        value_ = value;
        row_ = row;
        seen_ = true;
        return true;
    }

    [[nodiscard]] double value() const noexcept { return value_; }

    /// The row's inputs on one line, or nothing if no value was ever above zero.
    [[nodiscard]] std::string at() const { return seen_ ? describe(row_) : std::string{}; }

private:
    double value_{0.0};
    Row row_{};
    bool seen_{false};
};

}  // namespace touchstone::testing
