## 1. What the problem is really asking

A search engine or recommender returns a ranked list. NDCG@k asks one question about that list: **how close is your top `k` to the best top `k` you could possibly have shown?** Relevant items count more when they are near the top, and highly relevant items count much more than marginal ones.

Under the story, this is **sort, gather, weighted sum, normalize**, done for every row of a batch at once:

1. Sort each row's items by score (descending, stable).
2. Gather the relevance labels in that order and keep the first `K`.
3. Take a weighted sum: gain times a position discount. That's DCG.
4. Do the same with the relevance labels sorted best-first. That's IDCG.
5. Divide, with `0.0` when IDCG is `0`.

The judge compares your `(q,)` float array with `rtol=1e-9`, so the formula has to be exactly the one given: exponential gain, log-2 discount, ties to the lower index.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `scores` | `(q, m)` float | model score for each item of each query | sort key, descending |
| `relevance` | `(q, m)` int, `0..5` | the true graded label of each item | the gains |
| `k` | int `>= 1` | cutoff | `K = min(k, m)` |
| return | `(q,)` float | NDCG@k per query | in `[0, 1]` |

The details that are easy to miss:

- **`k` may be larger than `m`.** Slicing `[:, :k]` already stops at `m`, but your discount vector must have length `K = min(k, m)`, not `k`, or the broadcast multiply fails.
- **Ties go to the lower item index.** `np.argsort(-scores, kind="stable")` does that. Sorting ascending and reversing does the opposite.
- **IDCG uses all `m` labels**, not just the `K` you retrieved. A relevant item you ranked below the cutoff still belongs in the ideal list.

## 3. The math

Let $\pi$ be the ranking: $\pi(j)$ is the item at 1-based position $j$. Write $r_{(j)} = \text{rel}_{\pi(j)}$. With **gain** $g(r) = 2^r - 1$ and **discount** $d_j = 1/\log_2(j+1)$:

$$\text{DCG@}k = \sum_{j=1}^{K} g\big(r_{(j)}\big)\, d_j, \qquad K = \min(k, m).$$

The discounts for the first four positions are $d_1 = 1/\log_2 2 = 1$, $d_2 = 1/\log_2 3 \approx 0.63093$, $d_3 = 1/\log_2 4 = 0.5$ and $d_4 = 1/\log_2 5 \approx 0.43068$. They are strictly decreasing.

**Why the ideal ranking is "sort the labels descending."** You want to maximize $\sum_j g_{(j)} d_j$ over all orderings. The discounts are fixed and decreasing. By the rearrangement inequality, a sum of products of two sequences is largest when both are sorted the same way. So the best ranking pairs the largest gain with the largest discount, the next largest with the next, and so on. Because $g$ is increasing in $r$, sorting gains descending is the same as sorting labels descending:

$$\text{IDCG@}k = \sum_{j=1}^{K} g\big(r^{*}_{(j)}\big)\, d_j, \qquad r^{*} = \text{sort}(\text{rel}, \text{descending}).$$

Since no ranking beats the ideal one, $0 \le \text{DCG} \le \text{IDCG}$, and

$$\text{NDCG@}k = \frac{\text{DCG@}k}{\text{IDCG@}k} \in [0, 1].$$

When every label is 0, every gain is $2^0 - 1 = 0$ and IDCG is 0. The ratio is $0/0$, and the problem defines it as $0$.

**0-based code positions.** In code the position is $j' = j - 1$, from 0, so the discount is $1/\log_2(j' + 2)$. That's `np.log2(np.arange(2, K + 2))`.

## 4. Trace an example by hand

**Example 1:** `scores = [[0.9, 0.8, 0.1]]`, `relevance = [[1, 3, 0]]`, `k = 2`. So `K = 2`.

| step | value | shape |
|---|---|---|
| `discount` | `[1.0, 0.63093]` | `(2,)` |
| `order` | `[[0, 1]]` | `(1, 2)` |
| `ranked` | `[[1, 3]]` | `(1, 2)` |
| gains `2**ranked - 1` | `[[1, 7]]` | `(1, 2)` |
| `dcg` | `1·1 + 7·0.63093 = 5.416508` | `(1,)` |
| `ideal` | `[[3, 1]]` | `(1, 2)` |
| `idcg` | `7·1 + 1·0.63093 = 7.63093` | `(1,)` |
| NDCG | `5.416508 / 7.63093 = 0.70981` | `(1,)` |

The model put the relevance-1 item above the relevance-3 item. That swap costs about 29%.

**The hidden case that teaches the most, "relevant item below the cutoff":** `scores = [[3, 2, 1, 0]]`, `relevance = [[0, 1, 0, 3]]`, `k = 2`. The top 2 are items 0 and 1, with labels `[0, 1]`, so DCG = `0·1 + 1·0.63093 = 0.63093`. The ideal list sorts **all four** labels: `[3, 1, 0, 0]`, keep `[3, 1]`, so IDCG = `7.63093`. NDCG is `0.082681`. If you built the ideal from the retrieved labels `[0, 1]` only, you'd get IDCG `= 1·1 + 0 = 1` and NDCG `0.6309`: you'd score the model well for burying the most relevant item.

**Ties, "all scores tied":** every score is 0, so the stable order is `[0, 1, 2]` in both rows. Row 0 gets labels `[0, 0, 3]`, DCG `= 7·0.5 = 3.5`, IDCG over `[3, 2, 1]` is `7 + 3·0.63093 + 1·0.5 = 9.392789`, NDCG `0.372626`. Row 1 gets `[4, 0, 0]`, DCG 15, IDCG `15 + 1·0.63093 = 15.63093`, NDCG `0.959636`.

## 5. Key idea: argsort, then take_along_axis

You need a per-row sort of one array (`scores`) applied to another (`relevance`). That's the pattern:

```python
order = np.argsort(-scores, axis=1, kind="stable")   # (q, m) column indices, best first
ranked = np.take_along_axis(relevance, order, axis=1) # (q, m) labels in ranked order
```

`relevance[order]` would be wrong: it indexes **rows** with `order`, giving a `(q, m, m)` array. `take_along_axis` pairs row `i` of `order` with row `i` of `relevance`, which is what you mean.

Negating the scores and sorting ascending gives descending order, and `kind="stable"` keeps equal scores in index order. The alternative `np.argsort(scores)[:, ::-1]` also gives descending order, but reversing a stable sort puts tied items in **reverse** index order. The default `kind="quicksort"` makes no tie promise at all. It may happen to look right on small inputs, but don't rely on it.

## 6. Plan before you code

```
K = min(k, m)
discount = 1 / log2(2 .. K+1)                         # (K,)
order    = stable argsort of -scores per row, first K  # (q, K)
ranked   = relevance gathered by order                 # (q, K)
dcg      = sum over positions of (2^ranked - 1) * discount   # (q,)
ideal    = relevance sorted descending per row, first K      # (q, K)
idcg     = same sum on ideal                                 # (q,)
return dcg / idcg where idcg > 0, else 0
```

| choice | right | wrong |
|---|---|---|
| gain | `2**rel - 1` | `rel` (linear gain) |
| discount at 0-based `j` | `1/log2(j + 2)` | `1/log2(j + 1)`, divides by 0 at `j = 0` |
| ideal list | all `m` labels, sorted | only the retrieved `K` |
| ties | stable sort of `-scores` | reversed ascending sort |

## 7. Build it one piece at a time

**Step 1: the cutoff and the discount vector.**

```python
m = scores.shape[1]
kk = min(k, m)
discount = 1.0 / np.log2(np.arange(2, kk + 2))   # (K,) = [1, 0.6309, 0.5, ...]
```

The discount is the same for every query, so build it once with shape `(K,)`. Later it broadcasts against `(q, K)` arrays: NumPy lines up the trailing axis and repeats the vector across all `q` rows.

**Step 2: rank and gather.**

```python
order = np.argsort(-scores, axis=1, kind="stable")[:, :kk]           # (q, K)
ranked = np.take_along_axis(relevance, order, axis=1).astype(float)  # (q, K)
```

Cutting to `K` after the sort keeps the gathered array small. The cast to float matters for the next line.

**Step 3: DCG.**

```python
dcg = ((2.0 ** ranked - 1.0) * discount).sum(axis=1)   # (q, K) * (K,) -> (q, K) -> (q,)
```

Using `2.0 **` keeps the arithmetic in floats. Labels are at most 5, so the largest gain is 31; there's no overflow risk here. With unbounded labels (say, click counts) `2**rel` would explode, which is one reason some systems use linear gain.

**Step 4: IDCG and the safe divide.**

```python
ideal = -np.sort(-relevance.astype(float), axis=1)[:, :kk]   # (q, K) best labels first
idcg = ((2.0 ** ideal - 1.0) * discount).sum(axis=1)         # (q,)
return np.divide(dcg, idcg, out=np.zeros_like(dcg), where=idcg > 0)
```

`np.sort` is ascending; negate, sort, negate back for descending. For the divide, `where=idcg > 0` computes the ratio only where it's defined, and `out=np.zeros_like(dcg)` supplies `0.0` everywhere else. Without `out`, the skipped slots hold whatever memory happened to be there. A plain `dcg / idcg` gives `nan` with a warning for the all-zero query.

## 8. Full solution

```python
# NumPy for the per-row sorts, gathers and the guarded divide
import numpy as np


# scores, relevance: (q, m); returns (q,) NDCG@k per query
def ndcg_at_k(scores: np.ndarray, relevance: np.ndarray, k: int) -> np.ndarray:
    # number of candidate items per query
    m = scores.shape[1]
    # k may exceed m; the ranked list can't be longer than the item count
    kk = min(k, m)
    # (K,) log-2 discounts for 0-based positions j: 1/log2(j+2), so position 0 gets weight 1
    discount = 1.0 / np.log2(np.arange(2, kk + 2))
    # (q, K) item indices best-first; negate for descending, stable so ties keep the lower index
    order = np.argsort(-scores, axis=1, kind="stable")[:, :kk]
    # (q, K) each query's labels in ranked order; float so the gain math stays in floats
    ranked = np.take_along_axis(relevance, order, axis=1).astype(float)
    # (q,) DCG: exponential gain times discount, (K,) broadcasts over the q rows, summed per row
    dcg = ((2.0 ** ranked - 1.0) * discount).sum(axis=1)
    # (q, K) best possible ranking: ALL m labels sorted descending, then cut to K
    ideal = -np.sort(-relevance.astype(float), axis=1)[:, :kk]
    # (q,) IDCG with the same gains and discounts
    idcg = ((2.0 ** ideal - 1.0) * discount).sum(axis=1)
    # ratio where IDCG > 0; queries with no relevant items keep the 0.0 from `out`
    return np.divide(dcg, idcg, out=np.zeros_like(dcg), where=idcg > 0)
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `[0.7098]` | the formula: exponential gain and the log-2 discount |
| Example 2 | `[1., 0.]` | a score tie broken by the lower index (item 1 first) gives the ideal order; an all-zero query returns 0, not `nan` |
| relevant item below the cutoff | `[0.0827]` | IDCG comes from all `m` labels, not the retrieved ones |
| k larger than m | `[0.5869]` | `K = min(k, m)` so the discount length matches |
| k is 1 | `[1., 0.3333]` | only the top item counts; row 2 ranks label 1 first, giving `1/3` |
| all scores tied | `[0.3726, 0.9596]` | the whole ranking is decided by the tie rule |
| perfect ranking | `[1.]` | DCG equals IDCG, including tied labels `2, 2` |
| single item | `[1.]` | `m = 1` with `k = 5` |
| integer score ties | six values, e.g. `0.3507` first | many ties per row, across a batch |
| batch of queries | 30 values, e.g. `0.7965` first | the vectorized path at `(30, 40)`, `k = 10` |

## 10. Complexity

Two sorts of a `(q, m)` array dominate: $O(qm \log m)$ time. The gathers, gains and sums are $O(qK)$. Memory is $O(qm)$ for the argsort result. At `q = 200`, `m = 500` that's trivial.

At production scale (millions of candidates per query) you never sort everything. You need only the top `K` by score, which `np.argpartition` finds in $O(m)$ before sorting just those `K`. The ideal list likewise needs only the top `K` labels. And since labels take only six values, IDCG can be built from a label histogram without sorting at all.

## 11. If you got Wrong Answer

- **NDCG is too high, often exactly 1, when a relevant item sits below the cutoff.** You built the ideal list from the retrieved labels. "relevant item below the cutoff" gives `0.6309` instead of `0.0827` (`wrong_ideal_from_retrieved.py`).
- **Every value is a little off, including Example 1 (`0.7967` vs `0.7098`).** You used linear gain `rel` instead of `2**rel - 1` (`wrong_linear_gain.py`).
- **Example 2's first query is `0.7967`, not `1.0`, or "all scores tied" gives `[0.7592, 0.064]`.** Ties go to the higher index because you reversed an ascending sort (`wrong_ties_high_index.py`).
- **`inf`, `nan`, or a divide-by-zero warning.** Your discount uses `log2(j + 1)` with 0-based `j`, or you divided by an IDCG of 0 without a guard.
- **A broadcasting error when `k > m`.** The discount vector has length `k` instead of `min(k, m)`.

## 12. Follow-ups an interviewer might ask

- *Why the logarithmic discount?* It models users scanning top-down with slowly decaying attention. Other metrics use a harsher model: reciprocal rank stops at the first relevant item.
- *How does NDCG compare with average precision?* AP (problem 28, average-precision) uses binary relevance and is precision-oriented. NDCG handles graded labels, which is why it's the standard for web search and recommendation.
- *Can you train a model to maximize NDCG directly?* Not by gradient descent: the sort makes it piecewise constant in the scores. LambdaRank and LambdaMART weight pairwise gradients by the NDCG change of swapping the pair.
- *What changes for a huge candidate set?* Use `np.argpartition` to find the top `K` in linear time (problem 9, top-k-per-row), then sort only those.
- *How should you average NDCG across queries?* Usually the mean over queries, but decide up front what to do with queries that have no relevant items. Including them as 0 drags the mean down; most benchmarks drop them.
