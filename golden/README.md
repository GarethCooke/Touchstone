# `golden/` — committed known answers

Everything the C++ tests compare against that was produced somewhere other than this
library. Two files, two different origins, and the difference matters when one of them
disagrees with the code.

| File | Origin | Read by | Documented in |
|---|---|---|---|
| `bs_vanilla.json` | Generated here by `generate_bs_vanilla.py` from QuantLib-Python (constitution I4: the oracle, never a dependency) | `tests/test_closed_form.cpp`, `tests/test_parity.cpp` | [`SCHEMA.md`](SCHEMA.md) |
| `rng-known-answers.json` | Copied from `touchstone-learn`, where the TypeScript implementation generated it at L0 | `tests/test_rng.cpp` | [`../docs/rng.md`](../docs/rng.md) §5 |

A failure against the first means this library disagrees with QuantLib. A failure against
the second means the C++ and the browser would draw different numbers from the same seed,
which is the one thing the shared generator exists to prevent.

## Provenance of the RNG copy

Constitution amendment **A4** (2026-08-29) is the authority: the RNG specification and its
known-answer fixture originate in `touchstone-learn` at L0 and are copied **once** into
`touchstone` at T2, pinned to the L0 merge commit. From T2 onward `touchstone/docs/rng.md`
is the home and the site's copy is downstream. Both files were copied unchanged on
2026-08-29:

| Here | From `touchstone-learn` | SHA-256 |
|---|---|---|
| `../docs/rng.md` | `docs/rng.md` | `c0e39b7569a1cb0289be46b3638f4e250efab08c0d678be98fbb32adffdf69f6` |
| `rng-known-answers.json` | `src/demos/__fixtures__/rng-known-answers.json` | `6fe9c0a518ff1a5a5769a320e7bde4b147316deedfb58fad93043f226331fd6c` |

**Pin: `bd16b7189d535251634eaf6eb4f9ab26eb951581`** — `touchstone-learn` `main` as it stood
when L0's tollgate verdict was recorded, which is the state the copy was taken from. A4 says
"the L0 merge commit"; L0's history is linear, so there is no merge commit to name. The two
files themselves last changed at `dbd786d` ("L0 — scaffold the learn site") and neither has
been touched since, so the pin and that commit describe the same bytes. The digests above are
the check that matters either way: they were verified equal on both sides at the moment of
copying, and `cmp` reported the files identical.

The fixture is not regenerated here and there is no generator for it in this repository.
Regenerating it is `npm run fixture:rng` in `touchstone-learn`, and `docs/rng.md` §5 is
explicit that doing so is an amendment rather than maintenance — the fixture is what the two
implementations agree *on*, so a fixture regenerated to match a changed implementation proves
nothing. `tests/test_rng.cpp` therefore reads this file and never writes it, and checks the
metadata fields (`generator`, `seedExpansion`, `uniform`, `normal`, `spec`) before it compares
a single number, so a fixture swapped for one describing a different specification stops the
tests rather than being compared against as though it had not changed.
