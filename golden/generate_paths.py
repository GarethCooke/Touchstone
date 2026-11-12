"""Generate the path known-answer fixture, ``golden/paths-known-answers.json``.

The library's path API (``include/touchstone/paths.hpp``) replaces the TypeScript path
sampling the tutorial's demos run on today (``touchstone-learn/src/demos/paths.ts``), and the
two must draw the same paths from the same seed. This script is the fixture that says what
"the same" means: an independent transcription of ``docs/rng.md`` and of ``paths.ts``,
written in plain Python from those two documents and not from the C++, run over a fixed set
of cases.

Three properties matter.

**Independent of the code it tests.** Nothing here reads the C++. The generator follows
``docs/rng.md`` sections 1 to 4 line by line, and the paths follow ``paths.ts`` expression by
expression, including its association of the exact step's exponent,
``(mu - sigma^2/2) dt + sigma sqrt(dt) Z``, which the C++ forms differently -- through
``detail/scales.hpp``, as ``mu dt - (sigma sqrt(dt))^2 / 2 + sigma sqrt(dt) Z``. The two
agree to rounding, not to the bit, and the fixture's tolerance says by how much they may
differ.

**Checked before it is trusted.** Before writing anything, the generator reproduces
``golden/rng-known-answers.json``, the fixture the TypeScript implementation generated: every uniform
exactly, every normal to the 1e-12 absolute tolerance ``docs/rng.md`` section 6 sets. A
generator that cannot reproduce that file does not write this one.

**Deterministic.** No clock, no randomness of its own: the cases are fixed in source, and one
of them is found by a deterministic search (the first seed whose Euler path goes negative).
The same Python on the same libm writes the same bytes, and CI regenerates the file and
requires the working tree to be clean.

Usage::

    uv run golden/generate_paths.py            # write golden/paths-known-answers.json
    uv run golden/generate_paths.py --stdout   # write to stdout instead
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "paths-known-answers.json"
RNG_FIXTURE = HERE / "rng-known-answers.json"

MASK = 0xFFFFFFFF

# docs/rng.md section 3: the spacing of the uniforms, and so the smallest one above
# zero; section 4 clamps to it.
UNIFORM_RESOLUTION = 2.0**-53

# docs/rng.md section 6: cross-language agreement on the normals, and the fixture's
# tolerance, which is that agreement carried along a path.
NORMAL_TOLERANCE = 1e-12

# --- docs/rng.md section 2: fmix32 ---------------------------------------------------------


def fmix32(h: int) -> int:
    h &= MASK
    h ^= h >> 16
    h = (h * 0x85EBCA6B) & MASK
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & MASK
    h ^= h >> 16
    return h


# --- docs/rng.md section 1: xoshiro128** ---------------------------------------------------


def rotl(x: int, k: int) -> int:
    return ((x << k) | (x >> (32 - k))) & MASK


class Xoshiro128StarStar:
    def __init__(self, seed: int) -> None:
        self.s = [fmix32((seed + i) & MASK) for i in range(4)]
        if (self.s[0] | self.s[1] | self.s[2] | self.s[3]) == 0:
            self.s[0] = 0x9E3779B9

    def next_u32(self) -> int:
        s0, s1, s2, s3 = self.s
        result = (rotl((s1 * 5) & MASK, 7) * 9) & MASK
        t = (s1 << 9) & MASK
        s2 ^= s0
        s3 ^= s1
        s1 ^= s2
        s0 ^= s3
        s2 ^= t
        s3 = rotl(s3, 11)
        self.s = [s0, s1, s2, s3]
        return result

    # --- docs/rng.md section 3: uniforms -----------------------------------------------------

    def next_uniform(self) -> float:
        hi = self.next_u32()
        lo = self.next_u32()
        return ((hi >> 5) * 2.0**26 + (lo >> 6)) * UNIFORM_RESOLUTION

    # --- docs/rng.md section 4: normals ------------------------------------------------------

    def next_normal(self) -> float:
        return norm_inv(self.next_uniform())


A = [3.3871328727963666080e+0, 1.3314166789178437745e+2, 1.9715909503065514427e+3,
     1.3731693765509461125e+4, 4.5921953931549871457e+4, 6.7265770927008700853e+4,
     3.3430575583588128105e+4, 2.5090809287301226727e+3]
B = [1.0, 4.2313330701600911252e+1, 6.8718700749205790830e+2,
     5.3941960214247511077e+3, 2.1213794301586595867e+4, 3.9307895800092710610e+4,
     2.8729085735721942674e+4, 5.2264952788528545610e+3]
C = [1.42343711074968357734e+0, 4.63033784615654529590e+0, 5.76949722146069140550e+0,
     3.64784832476320460504e+0, 1.27045825245236838258e+0, 2.41780725177450611770e-1,
     2.27238449892691845833e-2, 7.74545014278341407640e-4]
D = [1.0, 2.05319162663775882187e+0, 1.67638483018380384940e+0,
     6.89767334985100004550e-1, 1.48103976427480074590e-1, 1.51986665636164571966e-2,
     5.47593808499534494600e-4, 1.05075007164441684324e-9]
E = [6.65790464350110377720e+0, 5.46378491116411436990e+0, 1.78482653991729133580e+0,
     2.96560571828504891230e-1, 2.65321895265761230930e-2, 1.24266094738807843860e-3,
     2.71155556874348757815e-5, 2.01033439929228813265e-7]
F = [1.0, 5.99832206555887937690e-1, 1.36929880922735805310e-1,
     1.48753612908506148525e-2, 7.86869131145613259100e-4, 1.84631831751005468180e-5,
     1.42151175831644588870e-7, 2.04426310338993978564e-15]


def horner(c: list[float], x: float) -> float:
    """Highest coefficient first; the coefficients are listed lowest-order first."""
    result = c[7]
    for i in range(6, -1, -1):
        result = result * x + c[i]
    return result


def norm_inv(p: float) -> float:
    if p <= 0.0:
        p = UNIFORM_RESOLUTION
    q = p - 0.5
    if abs(q) <= 0.425:
        r = 0.180625 - q * q
        return q * horner(A, r) / horner(B, r)
    r = p if q < 0.0 else 1.0 - p
    r = math.sqrt(-math.log(r))
    if r <= 5.0:
        r -= 1.6
        value = horner(C, r) / horner(D, r)
    else:
        r -= 5.0
        value = horner(E, r) / horner(F, r)
    return -value if q < 0.0 else value


def normals(seed: int, n: int) -> list[float]:
    rng = Xoshiro128StarStar(seed)
    return [rng.next_normal() for _ in range(n)]


# --- paths.ts, transcribed -----------------------------------------------------------------


def brownian_path(seed: int, steps: int, horizon: float) -> list[float]:
    z = normals(seed, steps)
    sqrt_dt = math.sqrt(horizon / steps)
    path = [0.0] * (steps + 1)
    for i in range(steps):
        path[i + 1] = path[i] + sqrt_dt * z[i]
    return path


def gbm_path(seed: int, steps: int, horizon: float, spot: float, drift: float, vol: float,
             scheme: str) -> list[float]:
    z = normals(seed, steps)
    dt = horizon / steps
    sqrt_dt = math.sqrt(dt)
    path = [0.0] * (steps + 1)
    path[0] = spot
    if scheme == "exact":
        drift_term = (drift - 0.5 * vol * vol) * dt
        for i in range(steps):
            path[i + 1] = path[i] * math.exp(drift_term + vol * sqrt_dt * z[i])
        return path
    for i in range(steps):
        path[i + 1] = path[i] * (1 + drift * dt + vol * sqrt_dt * z[i])
    return path


# --- the self-check ------------------------------------------------------------------------


def check_rng_fixture() -> dict:
    fixture = json.loads(RNG_FIXTURE.read_text(encoding="utf-8"))
    worst_normal = 0.0
    for vector in fixture["vectors"]:
        rng = Xoshiro128StarStar(vector["seed"])
        uniforms = [rng.next_uniform() for _ in range(len(vector["uniforms"]))]
        if uniforms != vector["uniforms"]:
            raise SystemExit(f"generate_paths: seed {vector['seed']}: the uniforms do not reproduce "
                             "rng-known-answers.json exactly; refusing to write a fixture")
        for got, want in zip(normals(vector["seed"], len(vector["normals"])), vector["normals"]):
            worst_normal = max(worst_normal, abs(got - want))
    if worst_normal > NORMAL_TOLERANCE:
        raise SystemExit(f"generate_paths: normals differ from rng-known-answers.json by "
                         f"{worst_normal:.3e}, above docs/rng.md's {NORMAL_TOLERANCE}; refusing to write a fixture")
    return {"vectors": len(fixture["vectors"]), "uniforms": "exact",
            "worst_normal_difference": worst_normal}


# --- the cases -----------------------------------------------------------------------------

BROWNIAN = [
    {"seed": 1, "steps": 10, "horizon": 1.0},
    {"seed": 42, "steps": 64, "horizon": 2.0},
    {"seed": 2147483647, "steps": 5, "horizon": 0.25},
]

GBM = [
    # A risk-neutral path: the drift is r - q.
    {"seed": 1, "steps": 10, "horizon": 1.0, "spot": 100.0, "drift": 0.03, "vol": 0.2},
    # A trading year of daily steps at a high volatility.
    {"seed": 42, "steps": 252, "horizon": 1.0, "spot": 100.0, "drift": 0.05, "vol": 0.4},
    # No volatility: compound interest in Euler, continuous in the exact scheme.
    {"seed": 7, "steps": 8, "horizon": 2.0, "spot": 50.0, "drift": 0.04, "vol": 0.0},
    # A negative drift and a small spot.
    {"seed": 2147483647, "steps": 16, "horizon": 0.5, "spot": 0.01, "drift": -0.02, "vol": 0.3},
]

# A coarse, very volatile grid on which an Euler step's factor 1 + mu dt + sigma sqrt(dt) Z
# goes negative when Z falls below about -1.36. The seed is the first one whose Euler path
# does, found below rather than chosen, so the fixture holds a path the library must not clip.
NEGATIVE_EULER = {"steps": 4, "horizon": 1.0, "spot": 100.0, "drift": 0.05, "vol": 1.5}


def first_negative_euler_seed() -> int:
    c = NEGATIVE_EULER
    for seed in range(1, 10_000):
        path = gbm_path(seed, c["steps"], c["horizon"], c["spot"], c["drift"], c["vol"], "euler")
        if min(path) < 0.0:
            return seed
    raise SystemExit("generate_paths: no seed below 10000 gives a negative Euler path")


def build() -> dict:
    self_check = check_rng_fixture()

    brownian = []
    for case in BROWNIAN:
        brownian.append({**case, "path": brownian_path(case["seed"], case["steps"], case["horizon"])})

    gbm_cases = list(GBM)
    gbm_cases.append({"seed": first_negative_euler_seed(), **NEGATIVE_EULER})
    gbm = []
    for case in gbm_cases:
        for scheme in ("exact", "euler"):
            path = gbm_path(case["seed"], case["steps"], case["horizon"], case["spot"],
                            case["drift"], case["vol"], scheme)
            gbm.append({**case, "scheme": scheme, "path": path})

    return {
        "schema": "touchstone/golden/paths@1",
        "spec": "docs/rng.md sections 1-4 for the normals; touchstone-learn src/demos/paths.ts "
                "for the paths, transcribed expression by expression",
        "generator": "golden/generate_paths.py",
        "grid": "steps + 1 values on {0, dt, ..., T}, dt = horizon / steps; one normal per "
                "step, in order, from a generator seeded with seed",
        "brownian_rule": "W_0 = 0; W_(k+1) = W_k + sqrt(dt) Z_k",
        "gbm_rules": {
            "exact": "S_(k+1) = S_k exp((drift - 0.5 vol vol) dt + vol sqrt(dt) Z_k)",
            "euler": "S_(k+1) = S_k (1 + drift dt + vol sqrt(dt) Z_k)",
        },
        "tolerance": {
            "value": NORMAL_TOLERANCE,
            "rule": "|value - reference| <= 1e-12 * max(1, |reference|) at every point of every "
                    "path: docs/rng.md's 1e-12 on the normals, carried through the steps, with "
                    "room for the C++ associating the exact step's exponent differently",
        },
        "self_check": self_check,
        "counts": {"brownian": len(brownian), "gbm": len(gbm)},
        "brownian": brownian,
        "gbm": gbm,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stdout", action="store_true", help="write to stdout instead of the file")
    args = parser.parse_args()

    text = json.dumps(build(), indent=2) + "\n"
    if args.stdout:
        sys.stdout.write(text)
    else:
        OUTPUT.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {OUTPUT.relative_to(HERE.parent)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
