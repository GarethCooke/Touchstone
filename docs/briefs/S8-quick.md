# S8 follow-up: 2.8's `--quick` — instruction for Claude Code in `touchstone`

Written 2026-11-15 by the Fable session that holds the two pre-L3 fixes (session B). Model
Opus 5.5, effort high, ultracode off. This file is self-contained: do not go back to any chat
for context.

The edit is already made. Three files arrived in the working tree from that session, and your
job is to verify them, add one paragraph of your own to the pack, commit, and push `main`.

| File | State |
|---|---|
| `experiments/2_8_risk_neutral_pricing.py` | modified |
| `docs/evidence/S8/summary.md` | modified: one new entry at the head |
| `docs/briefs/S8-quick.md` | new: this file |

## 0. Boundaries

- Read first (P1): `CONSTITUTION.md`, and the new entry at the head of
  `docs/evidence/S8/summary.md`, which says what changed and why.
- Confirm `main` is at `74011c2` or later and that `git status` shows exactly the three files
  above and nothing else. If anything else is modified, stop.
- **Do not run the script without `--quick`.** A full run rewrites
  `experiments/2_8_risk_neutral_pricing.json`, and a native Windows run differs from the
  committed file in its last bits. The committed JSON must not change by a byte. If it is ever
  modified, `git checkout -- experiments/2_8_risk_neutral_pricing.json` and say so.
- Do not edit the script. If a check below fails, stop and report; the fix goes back to the
  session that wrote it.
- You touch nothing under `../Touchstone-Learn`. Re-vendoring the script there is a second
  instruction, after this commit is on `main`.
- You may push `main`. This is the one push.

## 1. Verify

Each of these has an expected answer. If yours differs, stop and say which.

1. `git diff --stat`: two files, `experiments/2_8_risk_neutral_pricing.py` and
   `docs/evidence/S8/summary.md`. The JSON is not in it.
2. `git hash-object experiments/2_8_risk_neutral_pricing.py` gives
   `53be4f13bd36afac8f669421041398db39e21c80`, and its sha256 is
   `33497ce0b566985424764e57baacc54ae83ebae7765b4f8dc229757253d94318`. The file has 597 lines and
   LF endings.
3. `sha256` of `experiments/2_8_risk_neutral_pricing.json` is
   `c4b8abe589e6aec81624fcd8f5c455a2ae18630131350f96a3b10aa89256e94c`, as at `HEAD`.
4. `git diff -U0 experiments/2_8_risk_neutral_pricing.py`, read in full. Above line 392 exactly
   three hunks, each replacing lines one for one: lines 55–57 and 72–74 of the docstring, and
   line 388, which gains a trailing comment. So lines 208, 283, 289, 337, 343 and 391 are still
   `def terminal_run(`, `    return out`, `def path_run(`, `    }`, `def mc_surface(` and the
   `return` of `feynman_kac`, which is what `touchstone-learn`'s page 2.8 shows by line number.
   Below line 392: `build_checks` takes `quick`; two tolerances move under `quick` only; the
   sizes in `main()`; and the call that passes `quick=args.quick`.
5. Read the full run's path through the diff and satisfy yourself it is the old one: with
   `--quick` absent, `nested_ns` is `[1000, 10000, 100000, 1000000]`, `batch_ns` is
   `[100, 1000, 10000]`, `se_L2` is the sample's standard error and `wider` is 1.0. That is the
   argument that the committed JSON is unchanged; the Fable session also ran it, in an
   environment that reproduces the file byte for byte, and got the same bytes.
6. `uv run --frozen experiments/2_8_risk_neutral_pricing.py --quick`: 130 of 130 checks pass,
   it prints "NOT written", and `git status` still shows the JSON unmodified.
7. The seed sweep, natively, `--quick` only. In Git Bash:

   ```
   for s in $(seq 1 300); do uv run --frozen experiments/2_8_risk_neutral_pricing.py --quick --seed $s > /dev/null 2>&1 || echo "FAIL $s"; done
   ```

   Expected: it prints nothing. Then the same loop on `HEAD`'s script, from a scratch copy
   outside the tree (`git show HEAD:experiments/2_8_risk_neutral_pricing.py > <scratch>/old.py`):
   expected 23 failing seeds, 5, 14, 62, 73, 76, 81, 89, 103, 120, 144, 145, 147, 176, 180, 188,
   234, 235, 259, 267, 283, 287, 288 and 290. Those were measured on Linux; a seed that sits on a
   tolerance could differ on Windows, so report the two lists as you find them rather than
   stopping on a difference of one or two in the second.
8. The C++ suite does not read this experiment's JSON, and CI does not run the experiments, so
   neither is expected to move. Say what CI did after the push.

## 2. The pack

At the end of the new entry in `docs/evidence/S8/summary.md`, directly above the
`### 2026-11-04` entry, add one paragraph of your own, headed `**Verification on the
workstation.**`: the blob id and the two hashes as you measured them, the `--quick` result with
your Python and numpy versions, and the two sweep counts. Change nothing else in the entry.

## 3. Commit

All three files, one commit, on `main`:

```
S8 follow-up: 2.8's --quick asserts the full run's claims on a tenth of the draws; the JSON is byte-identical

--quick ran a tenth of the draws against the full run's batch and nested
sizes: batches of 10,000 numbered 10, so two checks were dropped and both
slopes were fitted through two points at the full run's ±0.06. A reviewer's
run of seeds 1 to 300 failed on 23 (touchstone-learn, L2 batch 8, Findings
5), and touchstone-learn's deploy runs --quick with numpy unpinned.

The batch sizes are now fractions of the draws, so --quick has the full
run's 10,000, 1,000 and 100 batches and fits both slopes through three
points. The nested estimates stop at the draws there are. Two tolerances
move under --quick only: mean L² and the effective sample size take the
larger of the sample's standard error and the exact one, and the PDE
residual's bound is twice the widened fraction. --quick asserts 130 of the
full run's 131 checks; seeds 1 to 3,000 all pass.

Two statements corrected in comments and the docstring. The field
largest_pde_term_rms is the gamma term's rms and theta's is larger; the
name stays, because the committed JSON carries it. The weighted estimate's
standard error does not grow with |lambda| for the call: it is below the
Q-run's at mu = +0.3.

The committed JSON is unchanged: the full run's sizes, claims and
tolerances are what they were. The Fable session ran the edited script in
full in an environment where the unmodified script reproduces the
committed file byte for byte (uv sync --frozen, numpy 2.5.2, AVX-512 off),
and got the same bytes. Lines 1 to 391 keep their numbers, so page 2.8's
three ranges hold.

The brief, docs/briefs/S8-quick.md, is committed with it.

Evidence: docs/evidence/S8/summary.md

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

Correct any figure in it that you measured differently, and say that you did. Then push `main`.

## 4. Report

End with: the commit hash; the blob id of the script at that commit; whether the JSON's sha256
is still `c4b8abe5…`; the `--quick` result; the two sweep lists; what CI did; anything you
stopped on; and anything in this instruction you did differently, with why.
