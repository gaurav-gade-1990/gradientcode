## Approach

The perceptron is the simplest online learner. Predict with $\operatorname{sign}(w^\top x + b)$, and when it's wrong, nudge the hyperplane toward the misclassified point:

$$
y_i (w^\top x_i + b) \le 0 \;\Rightarrow\; w \mathrel{+}= \eta\, y_i x_i,\quad b \mathrel{+}= \eta\, y_i .
$$

Every update raises the score $y_i(w^\top x_i + b)$ for that sample by $\eta(\lVert x_i\rVert^2 + 1) > 0$. On linearly separable data, Novikoff's theorem bounds the total number of mistakes by $(R/\gamma)^2$. On non-separable data like XOR, the weights cycle forever.

```python
def perceptron(X, y, n_epochs, lr=1.0):
    w, b = np.zeros(X.shape[1]), 0.0
    for _ in range(n_epochs):
        for i in range(len(X)):
            if y[i] * (X[i] @ w + b) <= 0:
                w = w + lr * y[i] * X[i]
                b = b + lr * y[i]
    return w, float(b)
```

The inner loop can't be vectorized. Each decision depends on the updates made just before it.

## Common mistakes

- **`< 0` instead of `<= 0`.** From $w = 0$ every score is 0. A strict test never fires, and the model never learns.
- **Batch updates.** Summing over every misclassified point and updating once per epoch is a different algorithm, and it produces different weights.
- **Labels in {0, 1}.** The update rule needs $\pm 1$ labels.

## Complexity

- **Time:** $O(E\, n d)$ for $E$ epochs.
- **Space:** $O(d)$.
