// How much of the statistical sweeps to run: one row in every `sweep_scale`.
//
// One by default, so the whole grid; CI's sanitizer job sets it higher, for the
// reason `CMakeLists.txt` gives where the option is declared — a sweep is
// thousands of evaluations, the sanitizer build is nine times slower, and every
// row exercises the same code. Every bound computed from a sweep is computed
// from the rows actually swept, so a scaled run is a smaller valid test rather
// than a weaker one; the few assertions that need the whole sample check
// `full_sweep` and stand aside.

#pragma once

#include <cstddef>

#ifndef TOUCHSTONE_SWEEP_SCALE
#define TOUCHSTONE_SWEEP_SCALE 1
#endif

namespace touchstone::testing {

inline constexpr std::size_t sweep_scale = TOUCHSTONE_SWEEP_SCALE;
inline constexpr bool full_sweep = (sweep_scale == 1);

}  // namespace touchstone::testing
