## Approach: bin by confidence, compare to accuracy

A calibrated model that says "80% sure" is right 80% of the time. ECE groups predictions by confidence and measures the gap between how sure the model was and how often it was right, weighted by how many predictions fall in each group.

1. Confidence and correctness per sample: `conf = probs.max(1)` and `correct = probs.argmax(1) == labels`.
2. A bin index per sample. For right-closed bins $(e_b, e_{b+1}]$, the bin index is the number of inner edges strictly below `conf`, which is `np.searchsorted(edges[1:-1], conf, side="left")`.
3. Per-bin sums with `np.bincount(bins, weights=...)`, then the weighted gaps.

$$
\text{ECE} = \sum_b \frac{|B_b|}{n} \left| \frac{\sum_{i \in B_b} \text{correct}_i}{|B_b|} - \frac{\sum_{i \in B_b} c_i}{|B_b|} \right| = \frac{1}{n}\sum_b \Big| \sum_{i \in B_b} (\text{correct}_i - c_i) \Big|
$$

```python
def expected_calibration_error(probs, labels, n_bins=10):
    conf = probs.max(axis=1)
    correct = (probs.argmax(axis=1) == labels).astype(float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins = np.searchsorted(edges[1:-1], conf, side="left")
    count = np.bincount(bins, minlength=n_bins)
    sum_conf = np.bincount(bins, weights=conf, minlength=n_bins)
    sum_acc = np.bincount(bins, weights=correct, minlength=n_bins)
    ne = count > 0
    return np.sum(np.abs(sum_acc[ne] - sum_conf[ne])) / len(conf)
```

The second form of the equation shows the weights cancel the per-bin means, so you never divide by a bin count.

## Common mistakes

- **Unweighted mean over bins.** A bin holding one sample counts as much as a bin holding a thousand. That is a different metric (sometimes called the average calibration error).
- **Left-closed bins.** `floor(conf * B)` puts a confidence of exactly `0.5` in the upper bin. Confidences such as `0.5`, `0.75` and `1.0` are common with a few classes.
- **Probability of the true class as the confidence.** ECE uses the probability of the **predicted** class.

## Complexity

- **Time:** $O(nC)$ for the max and argmax, plus $O(n \log B + B)$ for binning.
- **Space:** $O(n + B)$.
