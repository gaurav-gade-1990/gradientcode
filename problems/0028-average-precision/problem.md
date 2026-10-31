Compute the **average precision** (AP) of a binary classifier's scores, the step-wise area under the precision-recall curve that scikit-learn's `average_precision_score` reports.

Every **distinct** score value $\tau$ is a threshold. At threshold $\tau$, the samples with $s_i \ge \tau$ are predicted positive, and

$$
P(\tau) = \frac{TP(\tau)}{\#\{i : s_i \ge \tau\}}, \qquad R(\tau) = \frac{TP(\tau)}{n_+}
$$

where $TP(\tau)$ is the number of true positives among them and $n_+$ is the total number of positives. Go through the thresholds from the highest score to the lowest, $\tau_1 > \tau_2 > \dots > \tau_T$, and sum the precision at each threshold weighted by how much recall increased there:

$$
\text{AP} = \sum_{t=1}^{T} \big(R(\tau_t) - R(\tau_{t-1})\big)\, P(\tau_t), \qquad R(\tau_0) = 0
$$

There is no interpolation: don't use the trapezoidal rule, and don't replace precision by its running maximum.

**Tied scores** are one threshold. All samples with the same score enter together, so a block of ties contributes a single term.

Return a Python `float`.

**Constraints**

- `y_true` is a 1-D integer array of `0`s and `1`s with at least one `1`
- `scores` is a 1-D float array of the same length, `1 <= n <= 10^5`, with no `nan`
