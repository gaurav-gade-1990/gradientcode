Compute the **expected calibration error** (ECE) of a classifier, as in Guo et al., *On Calibration of Modern Neural Networks* (2017).

You get `probs` with shape `(n, C)`, where each row is a predicted probability distribution over `C` classes, and the true `labels` with shape `(n,)`. For each sample:

- the **confidence** is $c_i = \max_j \texttt{probs}[i, j]$
- the **prediction** is $\hat y_i = \arg\max_j \texttt{probs}[i, j]$, with ties going to the lowest class index (what `np.argmax` does)
- the sample is **correct** when $\hat y_i = \texttt{labels}[i]$

Split $[0, 1]$ into `n_bins` equal-width bins with edges `np.linspace(0, 1, n_bins + 1)`. Bin $b$ holds the samples whose confidence lies in $(\text{edges}[b],\ \text{edges}[b+1]]$: **open on the left, closed on the right**, so a confidence of exactly `1.0` lands in the last bin and a confidence of exactly `0.5` with 4 bins lands in bin 1, not bin 2.

For each non-empty bin $B_b$, let $\text{acc}(B_b)$ be the fraction of its samples that are correct and $\text{conf}(B_b)$ the mean confidence. Then

$$
\text{ECE} = \sum_{b:\, |B_b| > 0} \frac{|B_b|}{n}\, \big|\text{acc}(B_b) - \text{conf}(B_b)\big|
$$

Empty bins contribute nothing. Return a Python `float`.

**Constraints**

- `probs` is a 2-D float array, `1 <= n <= 10^5`, `2 <= C <= 100`; rows are non-negative and sum to `1`
- `labels` is a 1-D integer array with values in `[0, C)`
- `1 <= n_bins <= 100`
