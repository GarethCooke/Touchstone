# The shared random-number generator

Frozen by constitution I16. This document is the specification; `src/demos/rng.ts` is
the TypeScript implementation and Touchstone's C++ port must reproduce it. Changing
anything here is an amendment, and it invalidates every fixture downstream.

The point of freezing it: a demo in the browser and a test in the library must produce
the *same numbers* from the same seed. That is what lets the tutorial's checks be the
library's tests rather than a separate thing that happens to agree.

---

## 1 — Generator: xoshiro128\*\*

Blackman and Vigna's `xoshiro128**`, reference implementation, unmodified. State is
four 32-bit unsigned words `s0 s1 s2 s3`; one call returns one `uint32`.

```
uint32_t rotl(uint32_t x, int k) { return (x << k) | (x >> (32 - k)); }

uint32_t next() {
    uint32_t result = rotl(s1 * 5, 7) * 9;
    uint32_t t      = s1 << 9;

    s2 ^= s0;
    s3 ^= s1;
    s1 ^= s2;
    s0 ^= s3;

    s2 ^= t;
    s3  = rotl(s3, 11);

    return result;
}
```

All arithmetic is modulo 2³². **In JavaScript every 32-bit multiply must go through
`Math.imul`** — `s1 * 5` as a double silently loses precision above 2⁵³ and the two
languages then agree about nothing.

Chosen for the reasons in tech-decisions A6: fast in JavaScript, trivial in C++, and
two draws give a double.

## 2 — Seed expansion: fmix32

The state is expanded from a single 32-bit seed with the MurmurHash3 finaliser,
applied to `seed + i` for `i` in `0..3`. The addition is modulo 2³².

```
uint32_t fmix32(uint32_t h) {
    h ^= h >> 16;
    h *= 0x85ebca6b;
    h ^= h >> 13;
    h *= 0xc2b2ae35;
    h ^= h >> 16;
    return h;
}

s0 = fmix32(seed + 0);
s1 = fmix32(seed + 1);
s2 = fmix32(seed + 2);
s3 = fmix32(seed + 3);

if ((s0 | s1 | s2 | s3) == 0) s0 = 0x9e3779b9;   // see below
```

**The all-zero rejection.** xoshiro is stuck at zero for ever if seeded there, so the
state is checked and `s0` set to `0x9e3779b9` (the golden-ratio constant) if all four
words come out zero. In practice the branch is unreachable: `fmix32` is a bijection
with `fmix32(0) = 0`, and the four inputs differ, so at most one word can be zero.
It is specified and implemented anyway so that the C++ port has nothing left to decide.

## 3 — Uniform doubles

One uniform in `[0, 1)` costs two generator outputs. The **first** output is the high
word.

```
hi = next();          // 32 bits, 27 of them used
lo = next();          // 32 bits, 26 of them used
u  = ((hi >> 5) * 2^26 + (lo >> 6)) * 2^-53;
```

53 bits of mantissa, uniformly spaced on `[0, 1)`. The smallest value above zero is
2⁻⁵³ ≈ 1.11e-16; zero itself occurs with probability 2⁻⁵³.

## 4 — Normals: inverse CDF by AS241

Standard normals come from the inverse normal CDF of the uniforms — **the i-th normal
is `Φ⁻¹` of the i-th uniform of the same seeded stream**, so `normals(seed, n)` and
`uniforms(seed, n)` consume the stream identically and a demo can switch between them
without the seed meaning something different.

The inverse CDF is Wichura's AS241 (`PPND16`, *Applied Statistics* 37, 1988): pure
rational approximations, accurate to about 1e-16 over the whole range. No `erfc`, no
`erfinv`, nothing from libm beyond `sqrt` and `log` — which is the point, because
those are exactly the functions whose last bits differ between V8 and glibc.

```
q = p - 0.5

if |q| <= 0.425:
    r = 0.180625 - q*q
    return q * A(r) / B(r)

r = (q < 0) ? p : 1 - p
r = sqrt(-log(r))

if r <= 5:
    r = r - 1.6
    value = C(r) / D(r)
else:
    r = r - 5
    value = E(r) / F(r)

return (q < 0) ? -value : value
```

`A`…`F` are degree-7 polynomials evaluated by Horner, coefficients lowest-order first:

```
A = 3.3871328727963666080e+0   1.3314166789178437745e+2   1.9715909503065514427e+3
    1.3731693765509461125e+4   4.5921953931549871457e+4   6.7265770927008700853e+4
    3.3430575583588128105e+4   2.5090809287301226727e+3

B = 1.0                        4.2313330701600911252e+1   6.8718700749205790830e+2
    5.3941960214247511077e+3   2.1213794301586595867e+4   3.9307895800092710610e+4
    2.8729085735721942674e+4   5.2264952788528545610e+3

C = 1.42343711074968357734e+0  4.63033784615654529590e+0  5.76949722146069140550e+0
    3.64784832476320460504e+0  1.27045825245236838258e+0  2.41780725177450611770e-1
    2.27238449892691845833e-2  7.74545014278341407640e-4

D = 1.0                        2.05319162663775882187e+0  1.67638483018380384940e+0
    6.89767334985100004550e-1  1.48103976427480074590e-1  1.51986665636164571966e-2
    5.47593808499534494600e-4  1.05075007164441684324e-9

E = 6.65790464350110377720e+0  5.46378491116411436990e+0  1.78482653991729133580e+0
    2.96560571828504891230e-1  2.65321895265761230930e-2  1.24266094738807843860e-3
    2.71155556874348757815e-5  2.01033439929228813265e-7

F = 1.0                        5.99832206555887937690e-1  1.36929880922735805310e-1
    1.48753612908506148525e-2  7.86869131145613259100e-4  1.84631831751005468180e-5
    1.42151175831644588870e-7  2.04426310338993978564e-15
```

**The zero draw.** `Φ⁻¹(0)` is `-∞`. A uniform of exactly zero happens with probability
2⁻⁵³, so rather than leave it to the caller, `p <= 0` is clamped to 2⁻⁵³ before the
approximation runs. Both languages must do this, in the same place.

## 5 — Known answers

`src/demos/__fixtures__/rng-known-answers.json` holds the first ten uniforms and the
first ten normals for seeds **1**, **42** and **2147483647** (2³¹ − 1). `npm test`
checks the TypeScript against it exactly; Touchstone copies the same file and its C++
tests check against it to tolerance.

Regenerate with `npm run fixture:rng`. Doing so is an amendment, not maintenance — the
fixture is what the two implementations agree *on*.

## 6 — Tolerance

Agreement is to stated tolerance, never bit-exact (constitution I6). The generator
itself is integer arithmetic and *is* exact across languages; the uniforms are exact
too, being an integer expression times a power of two. Only the normals can differ, and
only in the last few units in the last place, because `sqrt` and `log` are permitted a
half-ulp of freedom by IEEE 754 and the polynomial evaluation order fixes the rest.

The tolerance for cross-language agreement on normals is **1e-12 absolute**. The
TypeScript implementation is checked against the fixture exactly, since it is the
implementation the fixture was generated from.

## 7 — Verification already done

The TypeScript implementation was cross-checked, at L0, against an independent Python
transcription using arbitrary-precision integers with explicit 32-bit masking: the
generator outputs and the uniforms agree exactly for seeds 1, 42 and 2³¹ − 1. The AS241
values were round-tripped through `math.erfc` and agree to 1e-14 relative across all
three branches of the approximation. That is the check the C++ port should repeat.
