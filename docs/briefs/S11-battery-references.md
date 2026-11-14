# S11 follow-up — the 2.11 battery names its two lognormals; and T5's row is completed

**For:** a Claude Code session. **Repo:** `C:\Development\Projects\Touchstone`, `main` at `ef578ea` when this was written.
**Written:** 2026-11-14. Run this before the L2 rulings session in `Touchstone-Learn`, which vendors what this one commits.

## Run it with

Model Opus 5.5, effort **high**, **ultracode off**. One agent in the tree.

## Job 1: complete T5's row (its own commit, first)

`ARCHITECTURE.md` §10.1 still says T5 is "In review". The fix is a patch already in `.git/`.

1. `git pull --ff-only`
2. `git apply --index .git/t5-row.patch`
3. `git commit -F .git/t5-row-commit-msg.txt`
4. `git push`

If `git apply` fails, stop this job and report the error. Do not edit `ARCHITECTURE.md` or `claims.md` by hand. If `git log` already shows "ARCHITECTURE.md: T5's row in the milestone table, completed", this job is done: skip it.

The two experiment files in the working tree are modified and belong to Job 2. `git apply --index` does not touch them; leave them out of this commit.

## Job 2: the battery

### The owner's ruling (L2 item `f3-2-11`, 2026-11-14)

Leave page 2.11 as it is, fix the experiment first, and let the page follow. Keep both lognormals and name each.

### The defect

`battery_2_6` in `experiments/2_11_where_it_breaks.py` said it tests the mixture's draws "against the lognormal matching the first two log moments". It uses two lognormals and named one.

- Rows 1, 2 and 6 (log mean, log variance, median) use the log-moment fit: log mean −0.05, σ_fit = 0.4543, median e^(E log S_T) = 95.12.
- Rows 5 and 7 (E[S_T], sd of S_T) use F = 105.13 and F√(e^(σ_fit² T) − 1) = 50.33. That is a lognormal with the forward F and the vol σ_fit, whose log mean is (r − ½σ_fit²)T = −0.0532.
- Row 1's label gave the formula "(r − 1/2 sigma_fit^2) T" for an expected value that is the mixture's exact log mean, −0.05. The formula is the other lognormal's.

The numbers were right; the names were not. `touchstone-learn`'s `docs/evidence/L2/batch-11/summary.md`, *Flagged* 3, has the detail.

### What is already done, on disk and uncommitted

The Fable session of 14 November edited the script and re-ran it. Both files are modified in the working tree:

| File | SHA-256 on disk |
|---|---|
| `experiments/2_11_where_it_breaks.py` | `d4fb488526ff175c2da19aeae7205795954472222a753336d45b809057ffc0a0` |
| `experiments/2_11_where_it_breaks.json` | `03d65e604a967ac36ac71524ef99142ddb30cb6ab4ffda9abd9af3ab00e3ce68` |

If either hash differs, someone has changed the file since: stop and report.

The edit, all in `battery_2_6` but for one check's text and the header comment:

1. The docstring and the header comment's C3 lines say which rows are tested against which lognormal.
2. Row 1's label drops the wrong formula.
3. Every row gains `reference`: `"log-moment fit"` for rows 1, 2 and 6; `"any lognormal"` for rows 3 and 4; `"forward-matched lognormal, vol sigma_fit"` for rows 5 and 7.
4. Rows 5 and 7 gain `log_moment_fit_expected`, what the log-moment fit itself would give. Row 5 also gains `log_moment_fit_z`.
5. Row 5's label and the C3 check's text name the two as the mixture and any lognormal priced to the same forward.

No check was added or removed, and no existing number was changed.

The run was made in the environment S11 used: the Linux VM on this workstation, `uv sync --frozen`, numpy 2.5.2, QuantLib 1.43. There the unmodified script first reproduced the committed JSON byte for byte. After the edit:

- 13,820 values compared with the committed JSON; 0 numbers, booleans or shapes changed;
- 3 strings changed: `results.returns.battery_2_6.rows[0].check`, `rows[4].check`, and `checks[57].claim`;
- 10 fields added: the seven `reference` fields, `rows[4].log_moment_fit_expected` = 105.46405521383795, `rows[4].log_moment_fit_z` = −7.491375390905411, `rows[6].log_moment_fit_expected` = 50.49567900872939;
- 157 of 157 checks pass.

**Do not re-run the full experiment natively on Windows and commit its output.** A run in another environment differs from the committed JSON in the last bits, as page 2.11 itself reports, and that would move every number. The JSON on disk is the one to commit.

### What you do

1. Read `git diff` on both files and confirm it is the edit described above and nothing else.
2. Compare the JSON yourself, `git show HEAD:experiments/2_11_where_it_breaks.json` against the working tree, value by value. You must find what the list above says: no number changed, three strings, ten new fields. If you find anything else, stop and report; do not commit.
3. Build and run the C++ tests. `tests/test_implied_vol.cpp` reads this JSON.
4. Add a dated entry at the head of `docs/evidence/S11/summary.md`: what changed, why (the owner's ruling and *Flagged* 3), how the run was made, and what the comparison found.
5. One commit: the script, the JSON, this brief and the summary. Message in the repo's convention. Push `main`. Wait for CI and report its result.

## Report

- The two commit hashes, and CI's result.
- Your JSON comparison: values compared, values changed, strings changed, fields added.
- Anything this brief got wrong.
