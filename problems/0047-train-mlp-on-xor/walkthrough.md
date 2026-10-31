## 1. What the problem is really asking

This is the smallest complete training loop in deep learning: forward pass, loss, backward pass, update, repeat. Every framework hides these four steps behind `loss.backward()` and `optimizer.step()`. Here you write them out for a two-layer network, so you see exactly which arrays flow where and in what order.

XOR is the target because no straight line separates `[0,1], [1,0]` (label 1) from `[0,0], [1,1]` (label 0). The hidden `tanh` layer bends the input space so the output layer can draw a line. Underneath, the problem is **chain-rule bookkeeping on four matrices**, plus two ordering rules: record the loss *before* the update, and compute *all* gradients before changing *any* parameter.

The judge compares two arrays: `losses`, one value per epoch, and `probs`, the final predictions. Because `losses` holds every epoch, an error in step 1 shows up from `losses[1]` onward, so the first index that differs tells you a lot.

## 2. Understand the inputs

| name | shape | what it is |
|---|---|---|
| `X` | `(N, 2)` | the inputs, one row per example; XOR has `N = 4` |
| `y` | `(N,)` | labels in `{0, 1}` |
| `W1` | `(2, H)` | input-to-hidden weights |
| `b1` | `(H,)` | hidden bias |
| `W2` | `(H, 1)` | hidden-to-output weights; note the trailing 1 |
| `b2` | `(1,)` | output bias |
| `lr` | scalar | learning rate |
| `epochs` | int | number of full-batch updates |

Details that are easy to miss:

- **`W2` is `(H, 1)`, not `(H,)`.** So `h @ W2` is `(N, 1)`. You want `z` as `(N,)` to match `y`, so take column 0. If you leave it as `(N, 1)` and compute `p - y`, broadcasting silently makes an `(N, N)` matrix.
- **"Don't modify the input arrays."** `W1 -= ...` is in place. Copy the four parameters first.
- **`losses[t]` is the loss at the start of iteration `t`.** So `losses[0]` is the loss of the initial weights, and the loss after the final update never appears in `losses`; it lives only in `probs`.

## 3. The math

**Forward**, with shapes:

$$
a = XW_1 + b_1 \;\;(N,H), \qquad h = \tanh(a) \;\;(N,H), \qquad z = hW_2 + b_2 \;\;(N,), \qquad p = \sigma(z) = \frac{1}{1+e^{-z}} \;\;(N,).
$$

**Loss.** Mean binary cross-entropy, $L = -\frac1N \sum_i [y_i \log p_i + (1-y_i)\log(1-p_i)]$.

**Gradient with respect to the logit.** Use $\log p = -\log(1+e^{-z})$ and $\log(1-p) = -z - \log(1+e^{-z})$. Substituting,

$$
\ell_i = y_i \log(1+e^{-z_i}) + (1-y_i)\big(z_i + \log(1+e^{-z_i})\big) = \log(1 + e^{z_i}) - y_i z_i .
$$

Differentiate: $\frac{d}{dz}\log(1+e^z) = \frac{e^z}{1+e^z} = \sigma(z) = p$. So $\frac{\partial \ell_i}{\partial z_i} = p_i - y_i$, and with the mean,

$$
dz_i = \frac{\partial L}{\partial z_i} = \frac{p_i - y_i}{N}.
$$

The sigmoid's own derivative $p(1-p)$ cancels against the $\frac{1}{p}$ and $\frac{1}{1-p}$ from the logs. That cancellation is why you should never backprop through the sigmoid and the log separately.

**Output layer.** $z_i = \sum_j h_{ij} W_{2,j} + b_2$, so $\frac{\partial z_i}{\partial W_{2,j}} = h_{ij}$ and $\frac{\partial z_i}{\partial h_{ij}} = W_{2,j}$. Summing over examples,

$$
dW_2 = h^\top dz \;\;(H,1), \qquad db_2 = \textstyle\sum_i dz_i \;\;(1,), \qquad dh = dz\,W_2^\top \;\;(N,H),
$$

where $dz$ is treated as an `(N, 1)` column.

**Through tanh.** $\frac{d}{da}\tanh(a) = 1 - \tanh^2(a) = 1 - h^2$, elementwise:

$$
da = dh \odot (1 - h^2) \;\;(N,H).
$$

**Hidden layer.** The same dense-layer rule as the output layer:

$$
dW_1 = X^\top da \;\;(2,H), \qquad db_1 = \textstyle\sum_i da_{i,:} \;\;(H,).
$$

Every gradient has the shape of the parameter it updates. That is the fastest sanity check you have.

## 4. Trace Example 1 by hand

`W1 = [[1, -1], [-1, 1]]`, `b1 = [0, 0]`, `W2 = [[1], [1]]`, `b2 = [0]`, `lr = 0.5`, `epochs = 3`, `N = 4`, `H = 2`.

**Epoch 0, forward.**

| row | `X` | `a = X @ W1` | `h = tanh(a)` | `z = h @ W2` | `p` | `y` |
|---|---|---|---|---|---|---|
| 0 | `[0, 0]` | `[0, 0]` | `[0, 0]` | `0` | `0.5` | 0 |
| 1 | `[0, 1]` | `[-1, 1]` | `[-0.7616, 0.7616]` | `0` | `0.5` | 1 |
| 2 | `[1, 0]` | `[1, -1]` | `[0.7616, -0.7616]` | `0` | `0.5` | 1 |
| 3 | `[1, 1]` | `[0, 0]` | `[0, 0]` | `0` | `0.5` | 0 |

The two hidden units cancel in every row, so every `p` is `0.5` and `losses[0] = ln 2 = 0.693147`.

**Epoch 0, backward.**

- `dz = (p - y) / 4 = [0.125, -0.125, -0.125, 0.125]`, reshaped to `(4, 1)`.
- `dW2 = h.T @ dz = [0, 0]`. The positive and negative `h` values cancel, so the output layer gets no update in this first step. `db2 = 0`.
- `dh = dz @ W2.T`, shape `(4, 2)`: each row is `[dz_i, dz_i]`.
- `da = dh * (1 - h²)`. Rows 1 and 2 have `h² = 0.58`, so they shrink to `-0.0525`; rows 0 and 3 stay at `0.125`.
- `dW1 = X.T @ da = [[0.0725, 0.0725], [0.0725, 0.0725]]`, `db1 = [0.145, 0.145]`.

**Update.** `W1` becomes `[[0.9637, -1.0363], [-1.0363, 0.9637]]` and `b1` becomes `[-0.0725, -0.0725]`. `W2` and `b2` don't move.

**Epoch 1** starts from those weights. Now the hidden units no longer cancel, `z = [-0.1448, -0.0916, -0.0916, -0.288]`, and `losses[1] = 0.665718`. Epoch 2 records `0.649591`. The final forward pass gives `probs = [0.4277, 0.4601, 0.4601, 0.3573]`, which is still far from XOR after three steps. The case "xor converges" runs 2,000 epochs and ends at `probs = [0.0003, 0.9973, 0.9973, 0.004]`.

## 5. Key idea: every gradient comes from the same parameters

Step 2 of the statement says the gradients all come from the **current** parameters. The natural mistake is to update `W2` and then compute `dh = dz @ W2.T` with the **new** `W2`. That is no longer the gradient of `L` at any single point.

Example 1 shows why this bug is sneaky. In epoch 0, `dW2` is exactly zero, so updating `W2` early changes nothing and `losses[1]` still matches. The bug first shows at `losses[2]`: the expected `0.649591` against `0.649515`. Write all six gradient lines first, then all four updates, and the problem can't happen.

## 6. Key idea: compute the loss from the logit

The textbook formula takes `log(p)` and `log(1 - p)`. If `z` is large, say 40, then `p = 1/(1 + e^{-40})` rounds to exactly `1.0` in float64, `1 - p` is `0`, and `log(0)` is `-inf`. The derivation in section 3 gave an equivalent form that never takes the log of a probability:

$$
\ell_i = \log(1 + e^{z_i}) - y_i z_i .
$$

`np.logaddexp(0, z)` computes $\log(e^0 + e^z)$ without overflow, by factoring out the larger exponent. At `z = 40` it returns `40.0` where the naive form returns `inf`. The constraints promise `p` stays inside `(0, 1)` here, so both forms pass, but the logit form is the one you'd use in production.

## 7. Plan before you code

```
copy W1, b1, W2, b2
for t in range(epochs):
    forward: h (N,H), z (N,)
    losses[t] = mean(logaddexp(0, z) - y*z)
    p = sigmoid(z)
    dz = (p - y)/N as (N,1)
    dW2, db2 = h.T @ dz, sum(dz)
    dh = dz @ W2.T                # old W2
    da = dh * (1 - h^2)
    dW1, db1 = X.T @ da, sum(da over rows)
    update all four
final forward -> probs
```

## 8. Build it one piece at a time

**Step 1: copy and forward.** A helper keeps the final forward pass identical to the one inside the loop.

```python
def _forward(X, W1, b1, W2, b2):
    h = np.tanh(X @ W1 + b1)       # (N,2)@(2,H) -> (N,H); b1 (H,) broadcasts over rows
    z = (h @ W2 + b2)[:, 0]        # (N,H)@(H,1) -> (N,1); b2 (1,) broadcasts; take column -> (N,)
    return h, z

W1, b1, W2, b2 = W1.copy(), b1.copy(), W2.copy(), b2.copy()
```

`b1` has shape `(H,)` and `X @ W1` has shape `(N, H)`. Broadcasting aligns trailing axes, so `b1` is added to every row. That is exactly "same bias for every example".

**Step 2: loss and the logit gradient.**

```python
losses[t] = np.mean(np.logaddexp(0.0, z) - y * z)   # z, y both (N,)
p = 1.0 / (1.0 + np.exp(-z))                         # (N,)
dz = ((p - y) / N)[:, None]                          # (N,) -> (N,1) for the matmuls
```

Make sure `z` is `(N,)` before `p - y`. If `p` were `(N, 1)`, then `(N, 1) - (N,)` broadcasts to `(N, N)`, and the run continues with wrong numbers instead of crashing.

**Step 3: backward, top to bottom.**

```python
dW2 = h.T @ dz                 # (H,N)@(N,1) -> (H,1), matches W2
db2 = dz.sum(axis=0)           # (1,), matches b2
dh = dz @ W2.T                 # (N,1)@(1,H) -> (N,H), uses the W2 from the forward pass
da = dh * (1.0 - h * h)        # (N,H), tanh'(a) = 1 - h^2
dW1 = X.T @ da                 # (2,N)@(N,H) -> (2,H), matches W1
db1 = da.sum(axis=0)           # (H,), matches b1
```

Summing over `axis=0` (rows) is how a bias gradient collects the contribution of every example. Summing over `axis=1` would give an `(N,)` array, which then broadcasts into `b1` with the wrong meaning or fails on shape.

**Step 4: update, then the final pass.**

```python
W1 -= lr * dW1; b1 -= lr * db1; W2 -= lr * dW2; b2 -= lr * db2
...
_, z = _forward(X, W1, b1, W2, b2)
probs = 1.0 / (1.0 + np.exp(-z))
```

## 9. Full solution

```python
# NumPy for the matrix products, tanh and logaddexp
import numpy as np


# one forward pass, shared by the training loop and the final prediction
def _forward(X, W1, b1, W2, b2):
    h = np.tanh(X @ W1 + b1)            # hidden activations (N, H); b1 broadcasts over rows
    z = (h @ W2 + b2)[:, 0]             # output logits, (N, 1) squeezed to (N,) to line up with y
    return h, z                         # h is needed again for backprop, z for loss and p


# full-batch gradient descent on a 2-layer tanh network with a sigmoid output
def train_mlp(X, y, W1, b1, W2, b2, lr, epochs):
    W1, b1, W2, b2 = W1.copy(), b1.copy(), W2.copy(), b2.copy()  # the -= below must not touch the caller's arrays
    N = X.shape[0]                      # batch size, for the 1/N of the mean loss
    losses = np.empty(epochs)           # one loss per epoch, (epochs,)
    for t in range(epochs):             # exactly `epochs` updates
        h, z = _forward(X, W1, b1, W2, b2)  # forward pass with the current parameters
        # BCE from logits, stable: log(1 + e^z) - y z never takes log(0)
        losses[t] = np.mean(np.logaddexp(0.0, z) - y * z)
        p = 1.0 / (1.0 + np.exp(-z))    # probabilities (N,), needed for the gradient

        dz = ((p - y) / N)[:, None]     # dL/dz: sigmoid and BCE cancel to (p - y)/N; column (N, 1)
        dW2 = h.T @ dz                  # (H, 1), same shape as W2
        db2 = dz.sum(axis=0)            # (1,), the bias collects every row's gradient
        dh = dz @ W2.T                  # (N, H), uses W2 before its update
        da = dh * (1.0 - h * h)         # back through tanh: tanh' = 1 - h^2, elementwise
        dW1 = X.T @ da                  # (2, H), same shape as W1
        db1 = da.sum(axis=0)            # (H,), summed over the batch

        W1 -= lr * dW1                  # all four updates happen after all gradients exist
        b1 -= lr * db1                  # step the hidden bias downhill
        W2 -= lr * dW2                  # step the output weights downhill
        b2 -= lr * db2                  # step the output bias downhill
    _, z = _forward(X, W1, b1, W2, b2)  # one more forward pass with the trained parameters
    return losses, 1.0 / (1.0 + np.exp(-z))  # loss history and final probabilities (N,)
```

## 10. How the test cases map to the code

| test case | expected (first losses, final probs) | what it checks |
|---|---|---|
| Example 1 | `[0.6931, 0.6657, 0.6496]`, `[0.4277, 0.4601, 0.4601, 0.3573]` | the whole loop; `losses[0]` is the untouched start; `dW2 = 0` in epoch 0 |
| Example 2 | `[0.7101, 0.6979, 0.6926, 0.6891, 0.6861]` | `H = 3`, non-zero biases, `lr = 1` |
| single epoch | `[0.725]`, `[0.4827, 0.4869, 0.638, 0.6452]` | one update, then the final forward pass |
| xor 200 epochs | ends at `0.0185`, `[0.0136, 0.9741, 0.9769, 0.0104]` | the network actually learns XOR |
| xor converges | `losses[0] = 1.0582`, ends at `0.0024` | 2,000 epochs: small per-step errors compound |
| one hidden unit | ends at `0.5133`, `[0.357, 0.3292, 0.9281, 0.3455]` | `H = 1` can't solve XOR; shapes `(2, 1)` and `(1, 1)` |
| wide hidden, small lr | ends at `0.6423` | `H = 8`, slow learning, tiny differences |
| random quadrant data | ends at `0.0233` | `N = 12`, a non-XOR dataset: `N` isn't hard-coded to 4 |

## 11. Complexity

One epoch does four matrix products of size about `N × 2 × H` or `N × H`, so it costs $O(NH)$ time (the input width 2 is a constant). The whole run is $O(\text{epochs} \cdot N H)$, at most `2000 × 16 × 8`, about 256,000 multiply-adds per product. Memory is $O(NH)$ for `h`, `dh`, `da`, plus $O(\text{epochs})$ for `losses`.

At scale the same loop is unchanged in structure. What changes: mini-batches instead of the full batch, an optimizer with state instead of plain SGD (problems 48 to 53), and the backward pass is generated by autograd (problems 56 and 59). The activation memory, $O(NH)$ per layer kept alive for backprop, is what limits batch size on a GPU.

## 12. If you got Wrong Answer

- **`losses[0]` is off, and the rest look shifted one place left.** You record the loss after the update. In Example 1 you'd get `0.665718` at index 0, which is the expected `losses[1]`.
- **Example 1's `losses[1]` is exactly `0.693147` again.** You left out `(1 - h * h)`. With that missing, `dW1` and `db1` come out exactly zero in epoch 0 (the rows cancel), and with `dW2 = 0` too, nothing moves.
- **Example 1 matches through `losses[1]` but `losses[2]` is `0.649515`.** You updated `W2` before computing `dh`. Section 5 explains why the first step hides it.
- **`losses[1]` is `0.638737` in Example 1, and the loss drops too fast.** You dropped the `/ N`. The gradient of the sum is 4 times the gradient of the mean, which acts like `lr = 2`.
- **A broadcast warning or an `(N, N)` array somewhere.** `z` or `p` is `(N, 1)` while `y` is `(N,)`. Take `[:, 0]` after `h @ W2 + b2`.
- **The caller's weights changed after your function returned.** You trained the input arrays in place. The judge hands you fresh copies, so it won't flag this, but the statement forbids it and a real caller would lose its initial weights. Copy them.

## 13. Follow-ups an interviewer might ask

- *Why does `H = 1` fail on XOR?* One `tanh` unit is a monotone function of one linear projection of the input, so the output is still separated by a single line. You need at least two hidden units. The "one hidden unit" case plateaus at loss `0.5133`.
- *Why does Example 1 start with `dW2 = 0`?* The initial weights are symmetric, so the two hidden units cancel exactly. Symmetric initialization stalls learning; that's why weights are drawn at random (problem 37, weight-initialization).
- *How would you check this backward pass?* Run a numerical gradient check on the loss as a function of each parameter (problem 46). On these tiny shapes it costs a few hundred forward passes.
- *How would you add momentum or Adam?* Keep a velocity or moment array per parameter, shaped like it, and replace the `-= lr * grad` lines with the optimizer's update (problems 48 and 52).
