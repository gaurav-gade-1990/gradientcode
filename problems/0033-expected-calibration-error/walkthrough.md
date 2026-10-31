## 1. What the problem is really asking

A classifier's probabilities are **calibrated** when they mean what they say: of all the predictions made with 80% confidence, about 80% are right. Modern neural networks are usually overconfident. They say 99% and are right 85% of the time. ECE puts one number on that gap.

Under the story, ECE is a **group-by and a weighted average**:

1. Reduce each row of `probs` to two numbers: a confidence (the max probability) and a correct/incorrect flag.
2. Group the samples into equal-width confidence bins.
3. In each bin, compare the accuracy with the mean confidence.
4. Average those gaps, weighting each bin by how many samples it holds.

The judge compares one `float` with `rtol=1e-9`. Almost everything is forgiving except the **bin boundaries**: a confidence sitting exactly on an edge has to go into the bin the problem says, and confidences like `0.5`, `0.75` and `1.0` are common.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `probs` | `(n, C)` float, rows sum to 1 | predicted distribution per sample | `max` gives confidence, `argmax` gives the prediction |
| `labels` | `(n,)` int in `[0, C)` | true classes | compared with the prediction |
| `n_bins` | int, default 10 | number of equal-width bins `B` | edges `np.linspace(0, 1, B + 1)` |
| return | Python `float` | ECE | `float(...)` around the NumPy scalar |

The details that are easy to miss:

- **Confidence is the probability of the predicted class**, not of the true class. For a wrong prediction those differ, and the gap between them is exactly what ECE is measuring.
- **Bins are open on the left, closed on the right**: bin $b$ is $(e_b, e_{b+1}]$. With 4 bins, `0.5` goes to bin 1 and `0.75` goes to bin 2. The natural `floor(conf * B)` does the opposite (left-closed) and puts them in bins 2 and 3.
- **Ties in `argmax` go to the lowest index.** A row `[0.5, 0.5]` predicts class 0. `np.argmax` already does this.

## 3. The math

For sample $i$: confidence $c_i = \max_j p_{ij}$, prediction $\hat y_i = \arg\max_j p_{ij}$, correctness $a_i = [\hat y_i = y_i] \in \{0, 1\}$. Let $B_b$ be the set of samples in bin $b$ and $n$ the total count. Per bin:

$$\text{acc}(B_b) = \frac{1}{|B_b|} \sum_{i \in B_b} a_i, \qquad \text{conf}(B_b) = \frac{1}{|B_b|} \sum_{i \in B_b} c_i.$$

The definition is

$$\text{ECE} = \sum_{b:\,|B_b|>0} \frac{|B_b|}{n} \,\big|\text{acc}(B_b) - \text{conf}(B_b)\big|.$$

**Simplify.** Substitute the means and pull $1/|B_b|$ out of the absolute value (it's positive):

$$\frac{|B_b|}{n}\left|\frac{1}{|B_b|}\sum_{i\in B_b} a_i - \frac{1}{|B_b|}\sum_{i\in B_b} c_i\right| = \frac{1}{n}\left|\sum_{i \in B_b} a_i - \sum_{i \in B_b} c_i\right|.$$

So

$$\text{ECE} = \frac{1}{n} \sum_b \Big| S^{a}_b - S^{c}_b \Big|, \qquad S^{a}_b = \sum_{i \in B_b} a_i,\quad S^{c}_b = \sum_{i \in B_b} c_i.$$

The bin count cancels. You only need two per-bin sums, and an empty bin has both sums equal to 0, so it contributes 0 automatically. That's why the problem's "skip empty bins" rule never needs a division by zero.

**The bin index.** With edges $e_0 = 0 < e_1 < \dots < e_B = 1$, sample $i$ is in bin $b$ when $e_b < c_i \le e_{b+1}$. That $b$ equals the number of **inner** edges $e_1, \dots, e_{B-1}$ that are strictly less than $c_i$. `np.searchsorted(edges[1:-1], conf, side="left")` returns exactly that count: `side="left"` puts a value equal to an edge *before* the edge, so the edge itself is not counted. Confidence is always at least $1/C > 0$, so nothing lands on $e_0$.

## 4. Trace an example by hand

**Example 2:** `probs = [[0.25, 0.75], [0.5, 0.5], [1.0, 0.0]]`, `labels = [1, 1, 0]`, `n_bins = 4`. Inner edges are `[0.25, 0.5, 0.75]`.

| sample | `conf` | `pred` | correct | bin (right-closed) |
|---|---|---|---|---|
| 0 | 0.75 | 1 | 1 | 2, since 0.75 is in (0.5, 0.75] |
| 1 | 0.5 | 0 (tie goes to class 0) | 0 | 1, since 0.5 is in (0.25, 0.5] |
| 2 | 1.0 | 0 | 1 | 3 |

Per-bin arrays, all shape `(4,)`: `count = [0, 1, 1, 1]`, `sum_conf = [0, 0.5, 0.75, 1.0]`, `sum_acc = [0, 0, 1, 1]`. The gaps are `0.5`, `0.25` and `0`, so ECE = `(0.5 + 0.25 + 0) / 3 = 0.25`.

**The hidden case that decides the boundary rule, "edge value changes bins":** `probs = [[0.25, 0.75], [0.1, 0.9], [0.5, 0.5], [0.6, 0.4]]`, `labels = [1, 1, 0, 1]`, 4 bins. Confidences `[0.75, 0.9, 0.5, 0.6]`, correct `[1, 1, 1, 0]`.

| | bins | count | `sum_conf` | `sum_acc` | ECE |
|---|---|---|---|---|---|
| right-closed (correct) | `[2, 3, 1, 2]` | `[0, 1, 2, 1]` | `[0, 0.5, 1.35, 0.9]` | `[0, 1, 1, 1]` | **0.2375** |
| left-closed `floor(c·B)` | `[3, 3, 2, 2]` | `[0, 0, 2, 2]` | `[0, 0, 1.1, 1.65]` | `[0, 0, 1, 2]` | 0.1125 |

The `0.75` sample moves bins, which changes which samples share a gap. In Example 2, every sample is alone in its bin under both rules, so both give 0.25. That's why the visible examples can't tell the two rules apart.

## 5. Key idea: per-bin sums with bincount

You could loop over bins with a mask per bin. `np.bincount` does the group-by in one pass:

```python
count    = np.bincount(bins, minlength=B)                 # (B,) samples per bin
sum_conf = np.bincount(bins, weights=conf, minlength=B)   # (B,) sum of conf per bin
sum_acc  = np.bincount(bins, weights=correct, minlength=B)# (B,) number correct per bin
```

`bincount(bins, weights=w)[b]` is the sum of `w[i]` over every `i` with `bins[i] == b`. `minlength=B` makes the output length exactly `B` even when the top bins are empty; without it, the length is `max(bins) + 1`.

## 6. Plan before you code

```
conf    = row max of probs                         # (n,)
correct = (row argmax == labels) as float          # (n,)
bins    = searchsorted(inner edges, conf, "left")  # (n,) ints in 0..B-1
count, sum_conf, sum_acc = bincount per bin        # (B,) each
keep only bins with count > 0
ECE = sum(count/n * |sum_acc - sum_conf| / count)  # = sum |sum_acc - sum_conf| / n
```

| choice | right | wrong |
|---|---|---|
| confidence | `probs.max(1)` | `probs[i, labels[i]]` |
| bin rule | `searchsorted(edges[1:-1], conf, "left")` | `floor(conf * B)` |
| averaging | weight by `count / n` | plain mean over non-empty bins |

## 7. Build it one piece at a time

**Step 1: confidence and correctness.**

```python
conf = probs.max(axis=1)                                     # (n,)
correct = (probs.argmax(axis=1) == labels).astype(float)     # (n,) 1.0 or 0.0
```

`axis=1` reduces across classes, leaving one value per sample. Casting the boolean to float lets it be a `bincount` weight.

**Step 2: the bin of each sample.**

```python
edges = np.linspace(0.0, 1.0, n_bins + 1)                    # (B+1,)
bins = np.searchsorted(edges[1:-1], conf, side="left")       # (n,) in 0..B-1
```

Using the same `linspace` edges as the definition, rather than recomputing boundaries by multiplication, keeps you consistent with the spec even where `linspace` gives values like `0.30000000000000004`. A confidence of `1.0` is greater than every inner edge, so it lands in bin `B - 1` without any clamp.

**Step 3: the per-bin sums.** As in section 5, three `bincount` calls, each `(B,)`.

**Step 4: the weighted gaps.**

```python
nonempty = count > 0                                                  # (B,) bool
gap = np.abs(sum_acc[nonempty] - sum_conf[nonempty]) / count[nonempty]  # (B',) |acc - conf|
return float(np.sum(count[nonempty] / n * gap))
```

Masking with `nonempty` before dividing avoids `0/0` for empty bins. The `float()` turns the NumPy scalar into the Python `float` the signature promises.

Floating-point note: Example 1 has accuracy 3/4 and mean confidence 0.75 in its one bin, so the true ECE is 0, but the reference returns `1.11022e-16` because `0.9 + 0.8 + 0.7 + 0.6` isn't exactly 3 in binary. The judge's `atol=1e-12` absorbs that.

## 8. Full solution

```python
# NumPy for row max/argmax, searchsorted binning and bincount group-sums
import numpy as np


# probs: (n, C) rows summing to 1; labels: (n,); returns ECE as a Python float
def expected_calibration_error(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
    # (n,) confidence = probability of the PREDICTED class, not the true one
    conf = probs.max(axis=1)
    # (n,) 1.0 where the argmax (ties -> lowest index) matches the label, else 0.0
    correct = (probs.argmax(axis=1) == labels).astype(float)
    # (B+1,) equal-width edges exactly as the definition builds them
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    # (n,) bin b holds edges[b] < conf <= edges[b+1]: count of inner edges strictly below conf
    bins = np.searchsorted(edges[1:-1], conf, side="left")
    # total samples, for the |B_b| / n weights
    n = len(conf)
    # (B,) samples per bin; minlength keeps empty top bins in the array
    count = np.bincount(bins, minlength=n_bins)
    # (B,) sum of confidences per bin
    sum_conf = np.bincount(bins, weights=conf, minlength=n_bins)
    # (B,) number of correct predictions per bin
    sum_acc = np.bincount(bins, weights=correct, minlength=n_bins)
    # (B,) empty bins contribute nothing, and skipping them avoids 0/0
    nonempty = count > 0
    # (B',) |accuracy - mean confidence| for each non-empty bin
    gap = np.abs(sum_acc[nonempty] - sum_conf[nonempty]) / count[nonempty]
    # weight each gap by its bin's share of samples and add them up
    return float(np.sum(count[nonempty] / n * gap))
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `1.11022e-16` (zero up to rounding) | a perfectly calibrated bin: accuracy 3/4, confidence 0.75 |
| Example 2 | `0.25` | argmax tie to class 0; `1.0` lands in the last bin |
| confidence on the edges | `0.1` | several confidences exactly on edges, 3 classes |
| edge value changes bins | `0.2375` | right-closed bins; left-closed gives `0.1125` |
| uneven bin sizes | `0.26` | bin weighting: 4 samples in bin 9, 1 in bin 5 |
| one bin | `0.0333333` | `n_bins = 1`, so ECE is \|overall accuracy − mean confidence\| |
| all wrong and confident | `0.985` | confidence is the predicted class's probability, not the true class's |
| single sample | `0.4` | `n = 1`: a correct prediction at 0.6 confidence |
| overconfident network | `0.177594` | 400 samples from sharpened softmax outputs, 15 bins |
| random distributions | `0.239696` | 200 Dirichlet rows, 4 classes |

## 10. Complexity

The row max and argmax touch every entry: $O(nC)$. `searchsorted` is $O(n \log B)$ and the three `bincount` calls are $O(n + B)$. Memory is $O(n + B)$ beyond the input.

In production you compute ECE on a held-out set after every training run or calibration change, often across many slices (per class, per language, per customer). The `bincount` form lets you do that with no Python loop over bins, and it streams well: keep running `count`, `sum_conf` and `sum_acc` arrays and update them batch by batch.

## 11. If you got Wrong Answer

- **Only "edge value changes bins" fails, with `0.1125`.** Your bins are left-closed: `floor(conf * B)` (`wrong_left_closed_bins.py`). This bug passes every other case, including "confidence on the edges".
- **Example 1 gives `0.25` and "all wrong and confident" gives `0.015` instead of `0.985`.** You used the probability of the true class as the confidence (`wrong_true_class_prob.py`). For a wrong prediction that number is small, so the model looks humble rather than overconfident.
- **"uneven bin sizes" gives `0.36875` instead of `0.26`.** You took a plain mean of the per-bin gaps (`wrong_unweighted_bins.py`). The lone sample in bin 5 got as much weight as the four in bin 9.
- **`nan` or a divide warning.** You divided by `count` before removing empty bins.
- **A shape error from `bincount`, or an index error.** You forgot `minlength=n_bins`, so the arrays are shorter than `B` when the top bins are empty.

## 12. Follow-ups an interviewer might ask

- *How do you fix a miscalibrated model?* Temperature scaling: divide the logits by a scalar $T > 1$ fitted on a validation set to minimize log loss. It doesn't change the argmax, so accuracy is untouched. The softmax itself is problem 1 (stable-softmax).
- *What are ECE's weaknesses?* It depends on the bin count, and equal-width bins are mostly empty for an overconfident model (everything piles up near 1). Adaptive ECE uses equal-mass bins instead. Proper scoring rules such as log loss and the Brier score need no bins.
- *Why only the top-1 confidence?* That's what decision-makers act on. Classwise ECE bins every class probability separately and catches miscalibration in the non-top classes.
- *Can a model have ECE 0 and still be useless?* Yes. A model that always predicts the class prior has ECE near 0 and no discrimination. Report ECE alongside accuracy or AUC.
