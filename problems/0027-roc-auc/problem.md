Compute the **area under the ROC curve** for a binary classifier from its labels and scores.

The AUC equals the probability that a randomly chosen positive gets a higher score than a randomly chosen negative, where a **tie counts as one half**:

$$
\text{AUC} = \frac{1}{n_+ n_-} \sum_{i:\, y_i = 1} \ \sum_{j:\, y_j = 0} \Big( \mathbb{1}[s_i > s_j] + \tfrac{1}{2}\, \mathbb{1}[s_i = s_j] \Big)
$$

This is the same number as the trapezoidal area under the ROC curve when tied scores are treated as a single threshold, and the same as scikit-learn's `roc_auc_score`.

The double sum is $O(n_+ n_-)$. Compute it in $O(n \log n)$ with the **rank-sum (Mann-Whitney U)** identity: rank all $n$ scores together in ascending order (ranks $1 \dots n$), giving **tied scores the average of the ranks they occupy**. Then

$$
\text{AUC} = \frac{\sum_{i:\, y_i = 1} \operatorname{rank}(s_i) - \frac{n_+(n_+ + 1)}{2}}{n_+ n_-}
$$

Return a Python `float`.

**Constraints**

- `y_true` is a 1-D integer array of `0`s and `1`s with at least one of each
- `scores` is a 1-D float array of the same length, `2 <= n <= 10^5`, with no `nan`
- scores may contain many ties
