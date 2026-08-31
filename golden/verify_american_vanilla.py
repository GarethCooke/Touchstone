"""Independently re-derive and check ``golden/american_vanilla.json``.

The counterpart to ``verify_bs_vanilla.py``, and it exists for the same reason: a generator
that drives QuantLib wrongly -- the dividend handle where the rate handle belongs, an
exercise object that is European after all -- produces a perfectly self-consistent file full
of wrong numbers, and nothing else in the pipeline would notice.

It checks five things, in this order.

1. **Structure.** Schema id, field list, counts, and that the cases are the full cartesian
   product of the declared axes with nothing missing or repeated.

2. **An independent lattice.** A Cox-Ross-Rubinstein tree with early exercise, written here
   in numpy from the recursion rather than called from QuantLib, priced for every row and
   compared with the file. It is vectorised across rows rather than across time, so the
   whole grid is one backward induction.

3. **Two exact identities**, which are the only places an American value can be checked
   against a closed form:

   - an American call on an underlying with **no dividend yield and a non-negative rate**
     is worth exactly its European counterpart, because exercising early throws away
     ``K - K e^{-rT} >= 0`` and gains nothing;
   - an American put with a **non-positive rate and a non-negative yield** is worth exactly
     its European counterpart, for the mirror-image reason.

   Note what the conditions exclude. "Never exercise an American call early" is a statement
   about non-negative rates: at ``r < 0`` the strike is worth *more* later, and the file
   contains rows where immediate exercise is optimal for a call on a non-dividend-paying
   underlying. The identity is asserted where it holds and not where it does not.

4. **Bounds.** Every value at least its European counterpart and at least its intrinsic
   value; and the American put-call relation, which is a pair of inequalities rather than
   an identity:

       S e^{-qT} - K  <=  C_A - P_A  <=  S - K e^{-rT}

5. **The spread field** is the largest disagreement among three lattices, so it must be
   non-negative and finite, and it must not be zero everywhere -- a spread that is
   identically zero means the cross-checks were not run.

Exit 0 on pass, 1 on any failure, with the worst offending row named.

Usage::

    uv run golden/verify_american_vanilla.py
"""

from __future__ import annotations

import json
import math
import sys
from itertools import product
from pathlib import Path

import numpy as np

SCHEMA_ID = "touchstone/golden/american_vanilla@1"

# The verifier's own tree. Deliberately a different scheme and a different step count from
# the file's primary engine: agreeing with Leisen-Reimer at 2001 steps because this is also
# Leisen-Reimer at 2001 steps would be a tautology.
VERIFY_STEPS = 1200

# What the two lattices are allowed to differ by, scaled as
# ``max(|reference|, strike)`` -- the option's own scale, which is the scale a lattice's
# error lives on. Measured at 1.1e-4 on the committed file; the bound is an order above it.
LATTICE_TOLERANCE = 1e-3

# The exact identities are exact, so they are held to the *oracle's* accuracy rather than to
# a lattice's. Measured at 4e-9 scaled; the bound is two orders above.
IDENTITY_TOLERANCE = 1e-6

# The put-call bounds are arithmetic between two numbers already in the file, so nothing
# but rounding stands between them. Measured at 3e-13 scaled.
PARITY_TOLERANCE = 1e-10

failures: list[str] = []


def fail(message: str) -> None:
    failures.append(message)


def norm_cdf_numpy(x: np.ndarray) -> np.ndarray:
    """N(x) = 0.5 erfc(-x / sqrt 2), elementwise.

    The route is the one ``normal.hpp`` and ``SCHEMA.md`` both name: computing N(-x) as
    1 - N(x) loses the left tail entirely. numpy has no erfc, and scipy is not a dependency
    of this project, so it is a Python loop -- which costs nothing here, because it runs
    once over a few hundred rows rather than inside the lattice.
    """
    flat = np.asarray(x, dtype=float).ravel()
    out = np.array([0.5 * math.erfc(-v / math.sqrt(2.0)) for v in flat])
    return out.reshape(np.shape(x))


def european(
    w: np.ndarray, spot: np.ndarray, strike: np.ndarray, vol: np.ndarray,
    rate: np.ndarray, yield_: np.ndarray, years: np.ndarray,
) -> np.ndarray:
    total_vol = vol * np.sqrt(years)
    d1 = (np.log(spot / strike) + (rate - yield_) * years + 0.5 * vol * vol * years) / total_vol
    d2 = d1 - total_vol
    return w * (
        spot * np.exp(-yield_ * years) * norm_cdf_numpy(w * d1)
        - strike * np.exp(-rate * years) * norm_cdf_numpy(w * d2)
    )


def american_crr(
    w: np.ndarray, spot: np.ndarray, strike: np.ndarray, vol: np.ndarray,
    rate: np.ndarray, yield_: np.ndarray, years: np.ndarray, steps: int,
) -> np.ndarray:
    """Cox-Ross-Rubinstein with early exercise, vectorised across rows.

    One column of the recursion per row, stepped backwards together. At each node the value
    is the larger of the discounted continuation value and the payoff of exercising now,
    which is the whole of the American feature.
    """
    rows = spot.shape[0]
    dt = years / steps
    up = np.exp(vol * np.sqrt(dt))
    down = 1.0 / up
    discount = np.exp(-rate * dt)
    # The risk-neutral probability under the dividend-adjusted drift.
    p = (np.exp((rate - yield_) * dt) - down) / (up - down)
    if np.any((p < 0.0) | (p > 1.0)):
        fail("CRR risk-neutral probability outside [0, 1]: the tree is not arbitrage-free")

    # Terminal spots: S u^j d^(n-j) for j = 0..n, one row per case.
    j = np.arange(steps + 1, dtype=float)
    log_spot = (
        np.log(spot)[:, None]
        + j[None, :] * np.log(up)[:, None]
        + (steps - j)[None, :] * np.log(down)[:, None]
    )
    terminal = np.exp(log_spot)
    value = np.maximum(w[:, None] * (terminal - strike[:, None]), 0.0)

    log_up = np.log(up)[:, None]
    log_down = np.log(down)[:, None]
    for step in range(steps - 1, -1, -1):
        j = np.arange(step + 1, dtype=float)
        continuation = discount[:, None] * (
            p[:, None] * value[:, 1 : step + 2] + (1.0 - p)[:, None] * value[:, 0 : step + 1]
        )
        node_spot = np.exp(
            np.log(spot)[:, None] + j[None, :] * log_up + (step - j)[None, :] * log_down
        )
        exercise = np.maximum(w[:, None] * (node_spot - strike[:, None]), 0.0)
        value = np.maximum(continuation, exercise)

    assert value.shape == (rows, 1)
    return value[:, 0]


def scaled(actual: np.ndarray, reference: np.ndarray, strike: np.ndarray) -> np.ndarray:
    """Relative to the option's own scale: its value, or the strike where that is larger."""
    return np.abs(actual - reference) / np.maximum(np.abs(reference), strike)


def describe(case: dict) -> str:
    return (
        f"{case['type']} S={case['spot']} K={case['strike']} vol={case['vol']} "
        f"r={case['rate']} q={case['dividend_yield']} days={case['expiry_days']}"
    )


def check_structure(doc: dict) -> None:
    if doc.get("schema") != SCHEMA_ID:
        fail(f"schema is {doc.get('schema')!r}, expected {SCHEMA_ID!r}")
    cases = doc["cases"]
    if len(cases) != doc["counts"]["cases"]:
        fail(f"counts.cases says {doc['counts']['cases']}, the file holds {len(cases)}")

    axes = doc["axes"]
    expected = set(
        product(
            axes["type"], axes["spot"], axes["strike"], axes["vol"],
            axes["rate"], axes["dividend_yield"], axes["expiry_days"],
        )
    )
    seen = {
        (c["type"], c["spot"], c["strike"], c["vol"], c["rate"],
         c["dividend_yield"], c["expiry_days"])
        for c in cases
    }
    if seen != expected:
        fail(
            f"the cases are not the cartesian product of the axes: "
            f"{len(expected - seen)} missing, {len(seen - expected)} unexpected"
        )
    if len(seen) != len(cases):
        fail("the file contains duplicate parameter sets")

    for case in cases:
        for field in doc["fields"]:
            if field not in case:
                fail(f"field {field!r} missing from a case: {describe(case)}")
                return
        if abs(case["expiry_years"] - case["expiry_days"] / 365.0) > 0:
            fail(f"expiry_years is not expiry_days / 365 exactly: {describe(case)}")
            return


def main() -> int:
    path = Path(__file__).with_name("american_vanilla.json")
    doc = json.loads(path.read_text(encoding="utf-8"))
    cases = doc["cases"]

    check_structure(doc)

    w = np.array([1.0 if c["type"] == "call" else -1.0 for c in cases])
    spot = np.array([c["spot"] for c in cases])
    strike = np.array([c["strike"] for c in cases])
    vol = np.array([c["vol"] for c in cases])
    rate = np.array([c["rate"] for c in cases])
    yield_ = np.array([c["dividend_yield"] for c in cases])
    years = np.array([c["expiry_years"] for c in cases])
    price = np.array([c["price"] for c in cases])
    spread = np.array([c["spread"] for c in cases])

    if not np.all(np.isfinite(price)):
        fail("the file contains a non-finite price")
    if np.any(price < 0.0):
        fail("the file contains a negative price")
    if np.any(spread < 0.0) or not np.all(np.isfinite(spread)):
        fail("the file contains a negative or non-finite spread")
    if np.all(spread == 0.0):
        fail("every spread is zero: the cross-check lattices cannot have been run")

    # 2 — an independent lattice
    ours = american_crr(w, spot, strike, vol, rate, yield_, years, VERIFY_STEPS)
    error = scaled(ours, price, strike)
    worst = int(np.argmax(error))
    print(
        f"independent CRR at {VERIFY_STEPS} steps vs the file: worst scaled deviation "
        f"{error[worst]:.3e} at {describe(cases[worst])}"
    )
    if error[worst] > LATTICE_TOLERANCE:
        fail(
            f"independent lattice disagrees by {error[worst]:.3e}, above {LATTICE_TOLERANCE:.0e},"
            f" at {describe(cases[worst])}"
        )

    # 3 — the two exact identities
    euro = european(w, spot, strike, vol, rate, yield_, years)

    call_identity = (w > 0) & (yield_ == 0.0) & (rate >= 0.0)
    put_identity = (w < 0) & (rate <= 0.0) & (yield_ >= 0.0)
    for mask, label in ((call_identity, "call, q = 0, r >= 0"), (put_identity, "put, r <= 0, q >= 0")):
        if not np.any(mask):
            fail(f"no rows satisfy the identity condition {label}: the grid does not test it")
            continue
        deviation = scaled(price[mask], euro[mask], strike[mask])
        index = int(np.argmax(deviation))
        row = [c for c, keep in zip(cases, mask) if keep][index]
        print(
            f"identity ({label}): {int(mask.sum())} rows, worst scaled deviation from the "
            f"closed form {deviation[index]:.3e}"
        )
        if deviation[index] > IDENTITY_TOLERANCE:
            fail(
                f"identity ({label}) violated by {deviation[index]:.3e} at {describe(row)}"
            )

    # 4 — bounds
    intrinsic = np.maximum(w * (spot - strike), 0.0)
    # The slack is the oracle's own accuracy, not a rounding: on the rows where the
    # American value equals the European one exactly, the lattice's deviation from the
    # closed form was measured at 5e-7 absolute, and a bound asserted tighter than that
    # would be asserting the lattice is better than it is.
    slack = 1e-7 * np.maximum(np.abs(price), strike)
    if np.any(price < euro - slack):
        index = int(np.argmin(price - euro + slack))
        fail(f"an American value is below its European counterpart at {describe(cases[index])}")
    if np.any(price < intrinsic - slack):
        index = int(np.argmin(price - intrinsic + slack))
        fail(f"an American value is below its intrinsic value at {describe(cases[index])}")

    # The American put-call relation:
    #
    #     S e^{-qT} - K  <=  C_A - P_A  <=  S - K e^{-rT}
    #
    # asserted only where its derivation holds, which is r >= 0 and q >= 0. The condition
    # is not decoration. At r < 0 the lower bound genuinely fails, because the argument
    # behind it assumes the call is never exercised early and a negative rate is exactly
    # when it is; the file contains such rows and they breach it by up to 2.5e-2. Measured
    # on the r >= 0 half, both bounds hold to 3e-13 -- which is arithmetic, not lattice
    # error, and is why this is asserted five orders tighter than anything else here.
    key = lambda c: (c["spot"], c["strike"], c["vol"], c["rate"], c["dividend_yield"], c["expiry_days"])  # noqa: E731
    calls = {key(c): c for c in cases if c["type"] == "call"}
    puts = {key(c): c for c in cases if c["type"] == "put"}
    shared = sorted(set(calls) & set(puts))
    if len(shared) != len(calls) or len(shared) != len(puts):
        fail("calls and puts do not pair up one to one")
    worst_low = worst_high = 0.0
    tested = 0
    for k in shared:
        c, p = calls[k], puts[k]
        s, x, r, q, t = c["spot"], c["strike"], c["rate"], c["dividend_yield"], c["expiry_years"]
        if r < 0.0 or q < 0.0:
            continue
        tested += 1
        difference = c["price"] - p["price"]
        low = s * math.exp(-q * t) - x
        high = s - x * math.exp(-r * t)
        scale = max(abs(difference), x)
        worst_low = max(worst_low, (low - difference) / scale)
        worst_high = max(worst_high, (difference - high) / scale)
    print(
        f"American put-call bounds over {tested} pairs with r >= 0 and q >= 0: worst breach "
        f"of the lower bound {worst_low:.3e}, of the upper bound {worst_high:.3e}"
    )
    if tested == 0:
        fail("no pair satisfies r >= 0 and q >= 0: the put-call bounds are not tested")
    if max(worst_low, worst_high) > PARITY_TOLERANCE:
        fail(
            f"the American put-call bounds are breached by more than {PARITY_TOLERANCE:.0e}"
        )

    premium = price - euro
    material = int(np.sum(premium > 1e-6 * np.maximum(np.abs(euro), 1.0)))
    print(
        f"{material} of {len(cases)} rows carry a material early-exercise premium; "
        f"largest {premium.max():.4f}"
    )
    if material < len(cases) // 4:
        fail("too few rows carry an early-exercise premium: the grid barely tests it")

    if failures:
        print(f"\nFAILED — {len(failures)} problem(s):", file=sys.stderr)
        for message in failures:
            print(f"  - {message}", file=sys.stderr)
        return 1
    print("\nOK — every row re-derived, both identities hold, every bound holds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
