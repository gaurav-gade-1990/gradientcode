## 1. What the problem is really asking

Strip the monitoring story and PSI is a **histogram comparison with fixed buckets**. You cut the reference window into bins that each hold about the same share of its traffic, count both windows into those *same* bins, and add up a per-bin divergence term. If today's traffic spreads over the bins the way the reference did, every term is near zero. If mass moved from some bins into others, those bins light up.

Three choices carry the whole problem:

- the bins come from the **reference only**,
- they are **right-closed**, so a value on an edge goes to the lower bin,
- empty bins are **floored at `eps`** so the log never sees zero.

The judge compares every field of the returned dict with `rtol=1e-7`: the edges, both proportion lists, every contribution, the total, the severity label and `top_bin`. A bin assignment that is off for a single tied value shows up in `ref_pct`, so the binning rules have to be exact, not approximately right.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `reference` | the 30-day window, a list of numbers | fits the edges and gives `r_j` |
| `current` | today's window | gives `c_j`, counted into the reference's bins |
| `n_bins` | the number of bins you *ask* for | interior cut points at `1/n, ..., (n-1)/n` |
| `eps` | floor on each proportion | keeps `ln(c/r)` finite |
| return value | `edges`, `ref_pct`, `cur_pct`, `contrib`, `psi`, `severity`, `top_bin` | lists as plain Python floats, in bin order |

Details that are easy to miss:

- **`n_bins` is a request, not a promise.** On tied data the quantiles repeat, and `np.unique` collapses them. The real bin count is `len(edges) + 1`, and every list you return has that length.
- **`ref_pct` and `cur_pct` are the floored values.** You return `max(count / n, eps)`, not the raw share, and you don't renormalize, so the lists may not sum to exactly 1.
- **The two windows have different sizes.** Divide each window's counts by its own length.
- **`top_bin` ties go to the lowest index.** `np.argmax` already does that.

## 3. The math

For bin $j$, let $r_j$ and $c_j$ be the floored reference and current proportions. The contribution of that bin and the total are

$$
\text{contrib}_j = (c_j - r_j)\,\ln\frac{c_j}{r_j}, \qquad \text{PSI} = \sum_{j=0}^{B-1} \text{contrib}_j .
$$

Every term is non-negative. If $c_j > r_j$, both $(c_j - r_j)$ and $\ln(c_j / r_j)$ are positive. If $c_j < r_j$, both are negative. If they are equal, the term is 0. So no bin can cancel another, and PSI is 0 only when every bin matches.

The formula is a symmetrised KL divergence. Expand the sum:

$$
\sum_j (c_j - r_j)\ln\frac{c_j}{r_j} = \sum_j c_j \ln\frac{c_j}{r_j} + \sum_j r_j \ln\frac{r_j}{c_j} = \mathrm{KL}(c \,\|\, r) + \mathrm{KL}(r \,\|\, c).
$$

That is why swapping the windows gives the same number, and why an empty bin is fatal without the floor: $\ln(0)$ is $-\infty$, and an empty bin on both sides gives $0 \cdot \ln(0/0)$, which is `NaN`.

## 4. Trace Example 1 by hand

`n_bins = 4`. The reference has 20 sorted prompt lengths. NumPy's default quantile interpolates linearly at position $q\,(n-1) = 19q$:

| q | position | neighbours | edge |
|---|---|---|---|
| 0.25 | 4.75 | 120 and 131 | 120 + 0.75 × 11 = **128.25** |
| 0.50 | 9.5 | 175 and 182 | 175 + 0.5 × 7 = **178.5** |
| 0.75 | 14.25 | 230 and 248 | 230 + 0.25 × 18 = **234.5** |

Each reference bin holds 5 of 20 values, so `r = [0.25, 0.25, 0.25, 0.25]`. Today's 10 prompts `[120, 150, 176, 210, 240, 265, 300, 340, 395, 450]` land like this:

| bin | range | current values | `c_j` | `contrib_j` |
|---|---|---|---|---|
| 0 | (−∞, 128.25] | 120 | 0.1 | (0.1 − 0.25) ln(0.4) = 0.137444 |
| 1 | (128.25, 178.5] | 150, 176 | 0.2 | (0.2 − 0.25) ln(0.8) = 0.0111572 |
| 2 | (178.5, 234.5] | 210 | 0.1 | 0.137444 |
| 3 | (234.5, ∞) | 240, 265, 300, 340, 395, 450 | 0.6 | (0.6 − 0.25) ln(2.4) = 0.306414 |

PSI = 0.592458, which is `"major"`, and `top_bin = 3`: the top quartile of prompt length gained the most share. Note that bins 0 and 2 contribute equally even though nothing changed between them. Losing share counts as much as gaining it.

**Example 2, the tied feature.** Reference retries `[0, 0, 0, 0, 0, 0, 0, 1, 1, 2]` with `n_bins = 5`. Positions `9q` are 1.8, 3.6, 5.4 and 7.2, giving quantiles `[0, 0, 0, 1]`. After `np.unique`, `edges = [0, 1]` and there are only 3 bins: `(−∞, 0]`, `(0, 1]` and `(1, ∞)`. The value 1 sits exactly on an edge and stays in bin 1. Shares move from `[0.7, 0.2, 0.1]` to `[0.3, 0.3, 0.4]`, and PSI = 0.795354, `top_bin = 2`.

## 5. Key idea: right-closed bins are `searchsorted(..., side="left")`

`np.searchsorted(edges, x, side="left")` returns the number of edges strictly less than `x`. That's the index of the first edge that is `>= x`. So with edges `[0, 1]`:

| x | edges < x | bin |
|---|---|---|
| 0 | none | 0, i.e. (−∞, 0] |
| 0.5 | 0 | 1 |
| 1 | 0 | 1, i.e. (0, 1] |
| 2 | 0, 1 | 2 |

That is exactly "a value equal to an edge belongs to the lower bin". `side="right"` counts edges `<= x` and pushes every on-edge value up one bin. On Example 2 every 0 moves into bin 1, bin 0 becomes empty in both windows, and you get `ref_pct [0.0001, 0.7, 0.3]` and PSI 0.677838 instead of 0.795354. Integer features such as token counts and retries sit on integer edges all the time, so this one-word bug causes phantom drift on real data. It fails "30-day reference vs a normal day" as well.

## 6. Key idea: edges come from the reference, and stay there

The bins are the reference's deciles, so the reference spreads about 10% into each, and movement shows up as bins that gained or lost share. If you refit the edges on `current`, today's traffic is spread evenly by construction and the bins no longer mean anything stable. In Example 1 the refit edges become `[184.5, 252.5, 330]` and PSI 0.625015. In "long-prompt launch" you get 2.83522 instead of 2.42275. Either way the number isn't comparable with yesterday's, because yesterday used different bins. In production you store the reference edges with the model version and reuse them.

## 7. Plan before you code

```
ref, cur = float arrays (copies, inputs untouched)
edges = unique(quantile(ref, [1/n, ..., (n-1)/n]))
B = len(edges) + 1
ref_counts = bincount(searchsorted(edges, ref, "left"), minlength=B)
cur_counts = same for cur
r = max(ref_counts / len(ref), eps); c = max(cur_counts / len(cur), eps)
contrib = (c - r) * ln(c / r); psi = sum
severity by the bands; top_bin = argmax(contrib)
```

| PSI | severity |
|---|---|
| `< 0.1` | `"stable"` |
| `0.1` to `< 0.25` | `"moderate"` |
| `>= 0.25` | `"major"` |

## 8. Build it one piece at a time

**Step 1: the edges.** `np.asarray(..., dtype=float)` makes a new array, so nothing you do afterwards touches the caller's lists. `np.unique` both sorts and deduplicates.

```python
    ref = np.asarray(reference, dtype=float)                       # (n_ref,)
    cur = np.asarray(current, dtype=float)                         # (n_cur,)
    edges = np.unique(np.quantile(ref, [i / n_bins for i in range(1, n_bins)]))   # (B-1,)
```

With a constant reference (`[256] * 50`) all nine quantiles are 256, `edges = [256]`, and there are two bins: "256 or less" and "above 256". Keeping the duplicates gives ten bins, eight of them zero-width, and the report lists bins that cannot hold anything.

**Step 2: counts per bin.** `minlength` matters: if the top bin is empty, `bincount` would otherwise return a shorter array and the lists would have the wrong length.

```python
    B = len(edges) + 1
    ref_counts = np.bincount(np.searchsorted(edges, ref, side="left"), minlength=B)   # (B,)
    cur_counts = np.bincount(np.searchsorted(edges, cur, side="left"), minlength=B)   # (B,)
```

**Step 3: floored proportions and the sum.** Floor before the log, and return the floored values.

```python
    r = np.maximum(ref_counts / len(ref), eps)
    c = np.maximum(cur_counts / len(cur), eps)
    contrib = (c - r) * np.log(c / r)
    psi = float(contrib.sum())
```

In "constant reference", nothing in the reference is above 256, so `r_1` would be 0 and its term `inf`. With the floor, `r_1 = 0.0001`, today's 25% above 256 contributes 1.95523, and PSI is 2.02715: a large but finite number that a `psi >= 0.25` alert can compare. Without the floor, PSI is `inf` here. On a bin that is empty in both windows it would be `NaN`, and `NaN >= 0.25` is `False`, so the page never fires.

**Step 4: plain Python types.** The judge compares JSON, so convert NumPy scalars with `float()` and `int()`.

## 9. Full solution

```python
import numpy as np                                   # quantiles, binning and vector math


def _severity(psi):                                  # map PSI to the industry bands
    if psi < 0.1:                                    # below 0.1: no meaningful shift
        return "stable"                              # nothing to page about
    if psi < 0.25:                                   # 0.1 up to 0.25: worth a look
        return "moderate"                            # investigate, don't page
    return "major"                                   # 0.25 and above: the distribution moved


def psi_report(reference, current, n_bins=10, eps=1e-4):   # PSI of today's window vs the reference
    ref = np.asarray(reference, dtype=float)         # a new float array; the caller's list stays untouched
    cur = np.asarray(current, dtype=float)           # same for today's window
    # interior cut points from the reference only; unique() drops repeats on tied features
    edges = np.unique(np.quantile(ref, [i / n_bins for i in range(1, n_bins)]))
    n_bins_eff = len(edges) + 1                      # the real bin count after deduplication
    # side="left" gives right-closed bins: a value on an edge stays in the lower bin
    ref_counts = np.bincount(np.searchsorted(edges, ref, side="left"), minlength=n_bins_eff)
    # minlength keeps empty top bins, so both count vectors have length B
    cur_counts = np.bincount(np.searchsorted(edges, cur, side="left"), minlength=n_bins_eff)
    r = np.maximum(ref_counts / len(ref), eps)       # reference share per bin, floored so log never sees 0
    c = np.maximum(cur_counts / len(cur), eps)       # today's share per bin, over today's own length
    contrib = (c - r) * np.log(c / r)                # per-bin term, never negative
    psi = float(contrib.sum())                       # total drift as a plain float
    return {                                         # every field is graded
        "edges": [float(e) for e in edges],          # the cut points used, as Python floats
        "ref_pct": [float(x) for x in r],            # floored reference proportions
        "cur_pct": [float(x) for x in c],            # floored current proportions
        "contrib": [float(x) for x in contrib],      # where the drift is, bin by bin
        "psi": psi,                                  # the headline number
        "severity": _severity(psi),                  # the label the alert keys on
        "top_bin": int(np.argmax(contrib)),          # biggest mover; argmax picks the lowest index on ties
    }
```

## 10. How the test cases map to the code

| test case | expected (from the reference) | what it checks |
|---|---|---|
| Example 1 | edges `[128.25, 178.5, 234.5]`, PSI 0.592458, `top_bin` 3 | linear-interpolated quantiles, the sum, the severity band |
| Example 2 | edges `[0, 1]`, 3 bins, PSI 0.795354 | `np.unique` on tied quantiles, and a value on an edge staying low |
| Example 3 | every contrib 0, PSI 0, `top_bin` 0 | the zero case and the lowest-index tie for `top_bin` |
| 30-day reference vs a normal day | PSI 0.02299, `"stable"` | same distribution, integer values on integer edges |
| long-prompt launch | bin 0 floored at 0.0001 today, PSI 2.42275 | an empty current bin needs the floor |
| slight growth, 20 bins | PSI 0.134173, `"moderate"` | the middle band and a larger `n_bins` |
| latency tail from a slow replica | PSI 0.0818723, `"stable"` | a tail shift that lands in the top bin barely moves PSI |
| retry storm on tied feature | edges `[0, 1]` from `n_bins=10`, PSI 0.395937 | deduplication with ten requested bins |
| today's traffic all in one bin | nine bins at `eps = 0.001`, PSI 6.17576 | a custom `eps` |
| edge values exactly on cut points | edges `[10, 20, ..., 90]`, PSI 0.117078 | the deciles of 0 to 100 are whole numbers, so 10, 20, ..., 90 sit on edges and stay in the lower bin (`side="right"` gives 0.798162) |
| constant reference | edges `[256]`, PSI 2.02715 | one interior edge, and an empty reference bin floored |
| single request today | 1 in bin 3, every other bin floored, PSI 8.14173 | a one-element window |

## 11. Complexity

`np.quantile` sorts the reference (or partitions it), O(n log n). `searchsorted` is O(log B) per value, so binning is O((n_ref + n_cur) log B), and the rest is O(B). Memory is O(n + B).

At production scale you don't ship raw values to Python at all. You store the reference edges once, compute bin counts in the warehouse (`width_bucket` in SQL or a Spark job), and only two count vectors of length `B` reach the PSI code. That makes PSI cheap enough to run per feature, per segment, per hour.

## 12. If you got Wrong Answer

- **The edge list has repeats and the lists have length `n_bins`** (Example 2 shows `edges [0, 0, 0, 1]` and five bins). You skipped `np.unique`.
- **Example 2's `ref_pct` starts with 0.0001 and PSI is 0.677838.** Your bins are left-closed: you used `side="right"`, so every 0 moved into bin 1.
- **PSI is `inf` or `NaN`** ("constant reference", "long-prompt launch"). You didn't floor the proportions at `eps` before the log.
- **Example 1's edges are `[184.5, 252.5, 330]`.** You fitted the quantiles on `current`. The bins come from `reference` only.
- **Only the cases with an empty bin fail** ("long-prompt launch", "constant reference", "single request today"), and the proportions no longer match the floored values. You renormalized after flooring. The spec returns the floored values as they are.
- **A length mismatch when the top bin is empty.** Pass `minlength=len(edges) + 1` to `np.bincount`.

## 13. Follow-ups an interviewer might ask

- *PSI said "stable" on the latency case, but 10% of requests got 2.5 s slower. Why?* The slow requests all land in the top bin, which already held 10% of the reference, so only one bin moves (`c_9 = 0.148`). PSI is coarse in the tails. A KS test (problem 136, ks-drift-detector) looks at the whole CDF and comes with a p-value, and percentile monitoring (problem 138) watches the tail directly.
- *Are 0.1 and 0.25 statistically meaningful?* No. They come from credit-risk scorecards. PSI grows with the number of bins and is noisy on small windows ("single request today" scores 8.14), so require a minimum sample size and tune the bands per feature.
- *How do you handle a categorical feature?* One bin per category from the reference, plus an "other" bin for unseen values, so a brand-new category shows up as drift instead of being dropped.
- *What about unstructured inputs like prompts?* Track drift in embedding space instead, for example the shift of the mean embedding or a classifier two-sample test (problem 141, embedding-drift).
- *How would you alert without paging on every noisy day?* Require the band for several consecutive windows, or feed the daily PSI into an EWMA detector (problem 140, ewma-anomaly-detection) so that a sustained climb pages and a single spike doesn't.
