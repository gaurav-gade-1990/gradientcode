## 1. What the problem is really asking

Every hour a monitoring job compares this hour's model inputs (`current`) with a baseline window (`reference`), one numeric feature at a time. For each feature it asks: "do these two samples look like they came from the same distribution?" The tool for that is the **two-sample Kolmogorov–Smirnov test**. Then, because the job runs many tests at once, it has to correct for multiple testing so that the on-call doesn't get paged by chance.

Under the story there are three small pieces:

- a **triage** per feature: missing column, too little data, or testable;
- a **largest gap between two step functions** (the KS statistic `D`), computed with integer arithmetic so that ties are exact, plus a closed-form p-value;
- a **Bonferroni threshold** `alpha / tested`, where `tested` counts only the features that actually ran.

The judge compares the whole report dict: `tested`, `threshold`, the `drifted` list in its exact order, and every feature row including `n_ref`, `n_cur`, `D`, `at` and `p_value`. So the bookkeeping fields (`at`, `threshold`, the `None`s) count just as much as the yes/no decision.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `reference` | `{feature: [values or None]}`, the baseline window | one sample per feature |
| `current` | same shape, this hour's window | the other sample |
| `alpha` | family-wise significance level, default `0.05` | divided by `tested` |
| `min_samples` | minimum non-null count on **each** side, default `30` | below it, `"insufficient_data"` |
| return | `{"tested", "threshold", "drifted", "features"}` | `features` has a row for every name in either dict |

Three details are easy to miss:

- **The feature list is the union** of both dicts' keys, sorted. A feature that exists only in `current` (a new column) is reported as `"missing"` too, with `n_ref: None`.
- **`None` is dropped, not zeroed.** `n_ref` and `n_cur` are the counts *after* dropping nulls. A feature can have 6 entries and still be `"insufficient_data"` because only 2 of them are real.
- **`at` must be the smallest value that attains the maximum gap**, and it is "the value as it appears in the input" (an `int` stays an `int`). When the two samples are identical, every gap is 0, and `at` is still reported: it's the smallest value overall.

## 3. Trace Example 1 by hand

`latency_ms`: reference `[120, 135, 150, 160, 180, 210, 240, 300]`, current `[150, 190, 230, 260, 310, 340, 390, 450]`, so `n = m = 8`. Walk the sorted union. `a` counts reference values `<= x`, `b` counts current values `<= x`, and the numerator is `|a·m − b·n|`:

| x | a | b | \|8a − 8b\| |
|---|---|---|---|
| 120 | 1 | 0 | 8 |
| 135 | 2 | 0 | 16 |
| 150 | 3 | 1 | 16 |
| 160 | 4 | 1 | 24 |
| **180** | **5** | **1** | **32** |
| 190 | 5 | 2 | 24 |
| 210 | 6 | 2 | 32 |
| 240 | 7 | 3 | 32 |
| 300 | 8 | 4 | 32 |
| 310 | 8 | 5 | 24 |
| ... | | | falls to 0 at 450 |

The maximum numerator is 32, first reached at `x = 180`. It is reached again at 210, 240 and 300, but `at` is the smallest, so `at = 180`, and `D = 32 / 64 = 0.5`.

The p-value: `n_e = 8·8/16 = 4`, so `λ = (2 + 0.12 + 0.11/2) · 0.5 = 1.0875`. That is above 0.27, so you sum the series and get `p = 0.187684`.

`prompt_tokens` gives `D = 0.125` at `90` and `p = 0.999999`. Two features ran, so `threshold = 0.05 / 2 = 0.025`. Neither p-value is below it, and the result is `{"tested": 2, "threshold": 0.025, "drifted": []}`.

**Example 2** shows the triage. `attachments_count` exists only in `reference`, so it is `"missing"` with `n_ref: 10, n_cur: None`. `account_age_days` keeps 4 and 2 non-null values. With `min_samples = 3` the current side is too small, so it's `"insufficient_data"`. Only `latency_ms` is tested, so the threshold stays `0.05 / 1 = 0.05`. Every current value is above every reference value, so the gap is total: `D = 1` at `x = 300` (the largest reference value, where the reference CDF hits 1 and the current CDF is still 0). `λ = 2.405` and `p = 1.88798e-05`: drifted.

**The tricky hidden case, "shift between reference points".** Reference is `100, 110, ..., 490`; current is `105, 115, ..., 295` plus twenty copies of `104.5`. At `x = 105`, a current value, the reference has 1 value `<= 105` and the current has 21, so the numerator is `|40 − 840| = 800` and `D = 0.5`. If you only evaluate at reference values, the best you find is `x = 110` (`a = 2, b = 21`), `D = 0.475`. The verdict happens to stay "drifted" here, but `D`, `at` and `p_value` are all wrong.

## 4. Key idea: the maximum is at a sample value, in either sample

Each empirical CDF is a step function that only jumps at its own sample values. Between two consecutive values of the union, both CDFs are flat, so their difference is flat. That means the supremum over all real `x` is attained at some value in `R ∪ C`, and checking those finitely many points is exact. It also means you need **both** samples: a current-only point (like `105` above) can be where the gap peaks.

Use `bisect_right` on the sorted lists to count values `<= x`. That's the standard CDF convention, $F(x) = P(X \le x)$, and it matters on tied integer features like `retrieved_chunks`, where many values sit exactly on `x`.

## 5. Key idea: compare integers, not floats

`a/n − b/m` and `c/n − d/m` can be mathematically equal and still differ in the last bit of floating point. If you compared floats, a rounding difference could make a later tie look larger and move `at`. Multiplying through by `n·m` gives the integer `|a·m − b·n|`, where ties are exact. Find the maximum (and its first location) on the integer, and divide by `n·m` once at the end.

Start `best` at `-1`, not `0`. With `best = 0` and strict `>`, identical samples (every numerator 0) would never set `at`, and you'd return `None`. With `-1`, the first value in the union sets it. That's why the "identical windows" case reports `at = -0.81`, the smallest sentiment score.

## 6. Key idea: Bonferroni over the features you actually tested

Running `k` independent tests at level `α` gives up to a `k·α` chance of at least one false alarm. Twenty features at `0.05` would page someone on most quiet hours. Bonferroni tests each at `α / k`, which keeps the family-wise error at `α`.

The `k` is the number of features that **ran** the test. A dropped column or a feature with 3 rows never produced a p-value, so it can't produce a false alarm, and counting it only makes the threshold stricter and hides real drift. In "Bonferroni over tested features only", `latency_ms` has `p = 0.0222`. Divided by the one tested feature the threshold is `0.05`, so it drifts. Divided by all three columns it would be `0.0167`, and the real shift would be missed.

This means you can't decide `"ok"` or `"drifted"` in the first pass, because you don't know `tested` yet. Run every test first, then label.

## 7. Plan before you code

```
features = {}, tested = []
for name in sorted(union of keys):
    ref = non-null reference values, or None if the key is absent
    cur = same for current
    if either is None:            status "missing"
    elif either has < min_samples: status "insufficient_data"
    else:
        num, at = max |a*m - b*n| over the union, first location
        D = num / (n*m);  p = kolmogorov_p(D, n, m)
        remember name in tested
threshold = alpha / len(tested), or None if nothing was tested
second pass over tested: p < threshold -> "drifted", else "ok"
drifted sorted by (p_value, name)
```

| situation | status | D, at, p_value |
|---|---|---|
| key absent from either dict | `"missing"` | `None` |
| a side has fewer than `min_samples` non-null values | `"insufficient_data"` | `None` |
| `p_value < alpha / tested` | `"drifted"` | numbers |
| otherwise | `"ok"` | numbers |

## 8. Build it one piece at a time

**Step 1: the statistic.** Sort once, then count with `bisect_right` at each union value:

```python
def ks_statistic(ref, cur):
    n, m = len(ref), len(cur)
    rs, cs = sorted(ref), sorted(cur)
    best, at = -1, None
    for x in sorted(set(rs) | set(cs)):
        a = bisect.bisect_right(rs, x)
        b = bisect.bisect_right(cs, x)
        num = abs(a * m - b * n)
        if num > best:
            best, at = num, x
    return best, at
```

Strict `>` keeps the *first* (smallest) `x` among ties, because the union is walked in ascending order.

**Step 2: the p-value.** This is the formula from the statement, line for line. The `λ < 0.27` shortcut matters: for small `λ` the alternating series converges slowly and its value is 1 to many digits anyway.

```python
def kolmogorov_p(D, n, m):
    ne = n * m / (n + m)
    lam = (math.sqrt(ne) + 0.12 + 0.11 / math.sqrt(ne)) * D
    if lam < 0.27:
        return 1.0
    s = sum((-1) ** (j - 1) * math.exp(-2.0 * j * j * lam * lam) for j in range(1, 101))
    return min(1.0, max(0.0, 2.0 * s))
```

The clip is required: for moderate `λ`, truncation and rounding can push `2·s` a hair outside `[0, 1]`.

**Step 3: the triage loop.** Build `ref` and `cur` as `None` when the key is absent, so the "missing" check and the `n_ref`/`n_cur` fields come from the same variable:

```python
ref = [v for v in reference[name] if v is not None] if name in reference else None
```

**Step 4: the second pass.** Only after the loop do you know `len(tested)`, so the threshold and the labels come last. Sort `drifted` by `(p_value, name)`; ties in p-value (two features with `p = 0`, for example) fall back to the name.

## 9. Full solution

```python
import bisect  # binary search counts "values <= x" in a sorted list
import math  # sqrt and exp for the Kolmogorov p-value


# Largest CDF gap as an integer numerator, plus the first value where it occurs.
def ks_statistic(ref, cur):
    n, m = len(ref), len(cur)  # non-null sample sizes of the two windows
    rs, cs = sorted(ref), sorted(cur)  # sort once so each count is a binary search
    best, at = -1, None  # -1 so even an all-zero gap (identical samples) sets `at`
    for x in sorted(set(rs) | set(cs)):  # the gap can only peak at a value from either sample
        a = bisect.bisect_right(rs, x)  # reference values <= x
        b = bisect.bisect_right(cs, x)  # current values <= x
        num = abs(a * m - b * n)  # |a/n - b/m| scaled by n*m, so ties compare exactly
        if num > best:  # strict: keep the smallest x among equal gaps
            best, at = num, x  # new maximum and where it happens
    return best, at  # caller divides by n*m to get D


# Asymptotic Kolmogorov p-value with the small-sample correction to lambda.
def kolmogorov_p(D, n, m):
    ne = n * m / (n + m)  # effective sample size of the two-sample test
    lam = (math.sqrt(ne) + 0.12 + 0.11 / math.sqrt(ne)) * D  # corrected test statistic
    if lam < 0.27:  # the series is 1 to many digits here and converges slowly
        return 1.0  # no evidence of a difference
    s = 0.0  # running sum of the alternating series
    for j in range(1, 101):  # 100 terms is far more than needed once lam >= 0.27
        s += (-1) ** (j - 1) * math.exp(-2.0 * j * j * lam * lam)  # j-th alternating term
    return min(1.0, max(0.0, 2.0 * s))  # clip rounding noise back into [0, 1]


# Per-feature KS drift report with a Bonferroni threshold over the tested features.
def ks_drift(reference, current, alpha=0.05, min_samples=30):
    features, tested = {}, []  # every feature's row, and the names that ran the test
    for name in sorted(set(reference) | set(current)):  # a column in either window gets a row
        # drop nulls (a missing measurement is not a zero); None marks an absent column
        ref = [v for v in reference[name] if v is not None] if name in reference else None
        # the same for the current window
        cur = [v for v in current[name] if v is not None] if name in current else None
        # start with everything unset; counts are None for an absent side
        row = {"status": None, "n_ref": None if ref is None else len(ref), "n_cur": None if cur is None else len(cur),
               "D": None, "at": None, "p_value": None}
        if ref is None or cur is None:  # the column was dropped on one side
            row["status"] = "missing"  # a pipeline problem, not drift
        elif len(ref) < min_samples or len(cur) < min_samples:  # too few real values to test
            row["status"] = "insufficient_data"  # report it, but don't run the test
        else:  # enough data on both sides: run KS
            n, m = len(ref), len(cur)  # sample sizes for D and the p-value
            num, at = ks_statistic(ref, cur)  # integer gap and its first location
            row["D"] = num / (n * m)  # turn the numerator back into a CDF gap
            row["at"] = at  # where the gap is largest, as given in the input
            row["p_value"] = kolmogorov_p(row["D"], n, m)  # how surprising that gap is
            tested.append(name)  # counts toward the Bonferroni divisor
        features[name] = row  # store the row whatever its status
    threshold = alpha / len(tested) if tested else None  # Bonferroni over tests actually run
    drifted = []  # names that beat the corrected threshold
    for name in tested:  # labels need the threshold, so they come after every test ran
        row = features[name]  # the row to label
        if row["p_value"] < threshold:  # significant even after the correction
            row["status"] = "drifted"  # this feature's distribution moved
            drifted.append(name)  # collect it for the summary list
        else:  # not significant at the corrected level
            row["status"] = "ok"  # no page for this feature
    drifted.sort(key=lambda k: (features[k]["p_value"], k))  # strongest evidence first, ties by name
    return {"tested": len(tested), "threshold": threshold, "drifted": drifted, "features": features}  # the report
```

## 10. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `D = 0.5` at `180`, `p = 0.187684`, threshold `0.025`, nothing drifted | the union walk, smallest `at` among ties, `alpha / 2` |
| Example 2 | `missing`, `insufficient_data`, and `latency_ms` drifted with `D = 1` at `300` | the triage, nulls dropped before counting, threshold `0.05` |
| quiet hour, six features | 6 tested, threshold `0.00833333`, nothing drifted | the correction on a normal hour |
| prompt-length incident | `prompt_tokens` (`p = 1.66e-11`) and `sentiment_score` drift; `latency_ms` (`p = 0.0142`) does not | Bonferroni stops a borderline feature; `attachments_count` missing |
| incident at alpha 0.01 | threshold `0.002`, same two drifted | `alpha` is honoured, not hard-coded |
| CRM outage nulls | `account_age_days` has `n_cur = 128`, `p = 0.028`, `ok` | 120 nulls are dropped, not counted as zeros |
| high min_samples skips sparse | `tested = 0`, threshold `None` | `min_samples` applies to both sides |
| nothing tested | both features `missing`, threshold `None` | a column present on only one side, either way round |
| shift between reference points | `D = 0.5` at `105`, drifted | the maximum sits at a current-only value |
| tied integer feature | `D = 0.2575` at `3`, drifted | `bisect_right` (`<= x`) on heavy ties |
| Bonferroni over tested features only | 1 tested, threshold `0.05`, `latency_ms` drifted at `p = 0.0222` | the divisor excludes missing and sparse columns |
| identical windows | `D = 0` at `-0.81`, `p = 1` | `best = -1` so `at` is still set |

## 11. Complexity

For one feature with `n` reference and `m` current values, sorting costs O((n + m) log(n + m)) and the union walk does two binary searches per distinct value, so the same bound overall. The p-value is 100 terms, constant. Across `F` features the job is O(F · N log N) with `N` the larger window, which is milliseconds at the constraints (30 features of 2,000 values).

A two-pointer merge over the sorted lists would make the walk linear, which matters when windows reach millions of rows. At that size the bigger production issue is statistical: KS on 100k-row windows flags tiny, harmless shifts with `p ≈ 0`. Mature teams alert on an effect size (`D` itself, or PSI from problem 135) **and** significance, not on `p` alone.

## 12. If you got Wrong Answer

- **`threshold` is `0.05` in Example 1, and `latency_ms` drifts in "prompt-length incident".** You skipped the correction (`threshold = alpha`). In "CRM outage nulls" that also flips `account_age_days` (`p = 0.028`) to drifted.
- **`account_age_days` drifts with `at = 0` in "CRM outage nulls", or Example 2 tests it.** You replaced `None` with `0`. That turns an upstream outage into a fake spike at zero (`D = 0.4255`) and inflates `n_cur` to 250. A null burst is a data-quality incident (problem 137), not drift.
- **"Bonferroni over tested features only" reports nothing drifted, and the threshold is `0.0167`.** You divided `alpha` by every column instead of the features that were tested.
- **`D = 0.475` at `110` in "shift between reference points".** You only evaluated the CDFs at reference values. Walk the union.
- **`at` is a later value than expected, for example `300` instead of `180` in Example 1.** You used `>=` instead of `>`, so the last tie wins. Float comparison of the gaps can move `at` the same way.
- **`at` is `None` in "identical windows".** You started `best` at `0`.
- **"tied integer feature" is `ok` with `D = 0.0558` at `1`.** You counted the current side with `bisect_left` (strictly less than) and the reference with `bisect_right`. Mixed conventions shift every tied value by a whole bucket.

## 13. Follow-ups an interviewer might ask

- *Bonferroni is too strict with 500 features. What would you use?* Benjamini–Hochberg: sort the p-values, find the largest `k` with `p_(k) <= k·α/F`, and flag those `k`. It controls the false discovery rate rather than the chance of any false alarm, which is the right trade when you'd rather see a few extra flags than miss real drift.
- *How do you handle a categorical or low-cardinality integer feature?* KS assumes continuous data, and on heavily tied values its asymptotic p-value is conservative. Use a chi-squared test on the category counts, or PSI (problem 135).
- *The windows have 100k rows and everything drifts. What now?* Large `n` makes any tiny shift significant. Alert on effect size too: require `D > 0.1` (or a PSI band) in addition to `p < threshold`.
- *How would you monitor text or embedding inputs?* Per-dimension KS on embeddings explodes the test count. Compare centroid distance or a classifier two-sample test on the embedding sets instead (problem 141, embedding-drift).
- *What should a `"missing"` feature do on the dashboard?* Page on it separately. A dropped column is often the real incident, a broken pipeline, and a drift detector that silently skips it hides it. Problem 137 (data-quality-validator) covers schema and null-rate checks.
