// The shared random-number generator, frozen by `docs/rng.md` (constitution I16).
//
// Same seed, same numbers, in this library and in the browser. That is the whole
// point of freezing it: the tutorial's demos and the library's tests draw from
// one stream, so a check on the page is a test of this code rather than a
// separate thing that happens to agree. `src/demos/rng.ts` in `touchstone-learn`
// is the other implementation; `golden/rng-known-answers.json` is what proves
// the two agree, and `docs/rng.md` is the specification both were written from.
//
// Nothing here may be changed without amending the constitution: a different
// generator, a different seed expansion, a different bit layout in the uniform,
// or a different order of the two draws would each invalidate every fixture
// downstream of it.

#pragma once

#include <touchstone/normal.hpp>

#include <cstdint>

namespace touchstone {

/// The MurmurHash3 32-bit finaliser, which is how one seed becomes four state
/// words. `docs/rng.md` section 2.
[[nodiscard]] constexpr std::uint32_t fmix32(std::uint32_t h) noexcept
{
    h ^= h >> 16;
    h *= 0x85ebca6bu;
    h ^= h >> 13;
    h *= 0xc2b2ae35u;
    h ^= h >> 16;
    return h;
}

namespace detail {

/// Rotate left. The shift is a template parameter so that the one way this can
/// be undefined — a rotation by 0 or 32, which is a shift by 32 — is a
/// compile error rather than something UBSan has to find. xoshiro uses 7 and 11.
template <int K>
[[nodiscard]] constexpr std::uint32_t rotl(std::uint32_t x) noexcept
{
    static_assert(K > 0 && K < 32, "a rotation by 0 or 32 shifts by 32, which is undefined");
    return static_cast<std::uint32_t>((x << K) | (x >> (32 - K)));
}

}  // namespace detail

/// xoshiro128** — Blackman and Vigna's reference implementation, unmodified.
///
/// Four 32-bit words of state; one call returns one uint32. All arithmetic is
/// modulo 2^32, which `std::uint32_t` gives for free here and which the
/// TypeScript has to reach for `Math.imul` to get.
///
/// The generator is integer arithmetic throughout, so it is *exact* across
/// languages rather than merely close: so are the uniforms, which are an
/// integer expression times a power of two. Only the normals can differ between
/// implementations, and only in the last few units in the last place, because
/// `sqrt` and `log` are allowed a half-ulp of freedom by IEEE 754.
/// `docs/rng.md` section 6 sets the tolerance for that at 1e-12 absolute.
class Xoshiro128SS {
public:
    /// Seed expansion: `fmix32(seed + i)` for i in 0..3, the addition modulo
    /// 2^32. `docs/rng.md` section 2.
    explicit constexpr Xoshiro128SS(std::uint32_t seed) noexcept
        : s0_(fmix32(seed + 0u)),
          s1_(fmix32(seed + 1u)),
          s2_(fmix32(seed + 2u)),
          s3_(fmix32(seed + 3u))
    {
        // xoshiro is stuck at zero for ever if seeded there. The branch is
        // unreachable in practice — fmix32 is a bijection with fmix32(0) = 0,
        // and the four inputs differ, so at most one word can come out zero —
        // and it is here anyway because the specification says it is, so that
        // this port has nothing left to decide.
        if ((s0_ | s1_ | s2_ | s3_) == 0u) {
            s0_ = 0x9e3779b9u;
        }
    }

    /// One 32-bit output.
    constexpr std::uint32_t next_u32() noexcept
    {
        const std::uint32_t result = detail::rotl<7>(s1_ * 5u) * 9u;
        const std::uint32_t t = s1_ << 9;

        s2_ ^= s0_;
        s3_ ^= s1_;
        s1_ ^= s2_;
        s0_ ^= s3_;

        s2_ ^= t;
        s3_ = detail::rotl<11>(s3_);

        return result;
    }

    /// One uniform double in [0, 1): 27 bits from the first output, 26 from the
    /// second, scaled by 2^-53. Uniformly spaced; zero occurs with probability
    /// 2^-53 and the smallest value above it is 2^-53.
    [[nodiscard]] double next_uniform() noexcept
    {
        // Two statements, not one expression. Which output is the high word is
        // part of the specification, and the order in which two calls within
        // one expression are evaluated is unspecified in C++ — so writing this
        // as a single line would give a generator that agrees with the browser
        // on some compilers and with nothing at all on others.
        const std::uint32_t hi = next_u32();
        const std::uint32_t lo = next_u32();

        constexpr double two_pow_26 = 67108864.0;
        return (static_cast<double>(hi >> 5) * two_pow_26 + static_cast<double>(lo >> 6)) * 0x1p-53;
    }

    /// One standard normal: the inverse CDF of one uniform.
    ///
    /// The i-th normal is `N^-1` of the i-th uniform of the same seeded stream,
    /// so a caller can switch between uniforms and normals without the seed
    /// coming to mean something different. Two 32-bit outputs are consumed,
    /// exactly as for a uniform.
    [[nodiscard]] double next_normal() noexcept { return norm_inv(next_uniform()); }

private:
    std::uint32_t s0_{};
    std::uint32_t s1_{};
    std::uint32_t s2_{};
    std::uint32_t s3_{};
};

}  // namespace touchstone
