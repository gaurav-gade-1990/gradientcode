## 1. What the problem is really asking

A recurrent neural network reads a sequence one step at a time and carries a **hidden state** $h$ from step to step. At every step it mixes the new input with the old state, passes the result through `tanh`, and that becomes the new state. Before attention, this was how every language model, translator and speech recognizer handled sequences, and LSTMs and GRUs (problems 61 and 62) are refinements of exactly this loop.

Strip the story and this is a **fold over the time axis**: a loop where each iteration depends on the previous one's output, and each iteration is a pair of batched matrix multiplies. The batch dimension `B` is handled by the matrix product in one shot. The time dimension `T` can't be, because $h_t$ needs $h_{t-1}$.

The judge compares the full `(B, T, H)` array of states. Three things decide whether you match: which side `W_hh` multiplies on (the row-vector convention), whether you store the state after or before the update, and whether you actually feed each state into the next step.

## 2. Understand the inputs

| name | shape | what it is |
|---|---|---|
| `x` | `(B, T, d_in)` | `B` sequences, each `T` steps of `d_in` features |
| `h0` | `(B, H)` | the state before the first input, one row per sequence |
| `W_xh` | `(d_in, H)` | input-to-hidden weights |
| `W_hh` | `(H, H)` | hidden-to-hidden weights, the recurrence |
| `b` | `(H,)` | bias, shared across batch and time |
| return | `(B, T, H)` | `[:, t]` is the state right after reading `x[:, t]` |

Easy to miss:

- **Vectors are rows.** The update is `h @ W_hh`, not `W_hh @ h`. Papers written with column vectors show $W_{hh} h$, which in this layout is `h @ W_hh.T`. Follow the stated shapes, not the paper.
- **`h0` is not in the output.** You return `T` states, $h_1$ through $h_T$, not `T + 1`.
- **`x[:, t]` has shape `(B, d_in)`**, the input for step `t` across the whole batch. Indexing `x[t]` instead would pick a sequence, not a time step.

## 3. The math

The recurrence, for $t = 1, \dots, T$:

$$
a_t = x_t W_{xh} + h_{t-1} W_{hh} + b, \qquad h_t = \tanh(a_t),
$$

with shapes $x_t: (B, d_{in})$, $W_{xh}: (d_{in}, H)$, $h_{t-1}: (B, H)$, $W_{hh}: (H, H)$, and $a_t, h_t: (B, H)$. The bias $b$ of shape $(H,)$ broadcasts across the $B$ rows.

**Unrolling.** Substituting the recurrence into itself shows why the state is "memory":

$$
h_2 = \tanh\big(x_2 W_{xh} + \tanh(x_1 W_{xh} + h_0 W_{hh} + b)\,W_{hh} + b\big).
$$

Every state is a nested function of every earlier input and of $h_0$, through repeated multiplication by $W_{hh}$.

**Why `tanh`.** It keeps every state in $(-1, 1)$, so repeated multiplication by $W_{hh}$ can't make the forward values blow up, whatever the weights. That is the numerical-stability property of this forward pass: no overflow is possible, even in "saturating weights", where the weights are scaled by 3.

**What it does to gradients.** The forward pass is all this problem asks for, but the same structure explains why vanilla RNNs are hard to train. Differentiate one step:

$$
\frac{\partial h_t}{\partial h_{t-1}} = \operatorname{diag}(1 - h_t^2)\; W_{hh}^\top \quad (\text{per sequence, } H \times H).
$$

A gradient from step $T$ reaching step $k$ is a product of $T - k$ such matrices. If their norms are below 1 it shrinks exponentially (vanishing gradients); above 1 it grows exponentially (exploding gradients, which clipping in problem 55 contains). Saturation makes vanishing worse: in "saturating weights", 76% of the stored states have $|h| > 0.99$, so $1 - h^2$ is close to 0 and almost no gradient flows back through those units. LSTMs (problem 61) add an additive cell path to avoid this product.

## 4. Trace the examples by hand

**Example 1**: one sequence (`B = 1`), `T = 3`, `d_in = H = 1`. `x = [1, 0, -1]`, `h0 = 0`, `W_xh = 0.5`, `W_hh = 1`, `b = 0`.

| `t` | `x_t W_xh` | `h_{t-1} W_hh` | `a_t` | `h_t = tanh(a_t)` |
|---|---|---|---|---|
| 0 | `0.5` | `0` | `0.5` | `0.4621` |
| 1 | `0` | `0.4621` | `0.4621` | `0.4318` |
| 2 | `-0.5` | `0.4318` | `-0.0682` | `-0.0681` |

Step 1 has no input at all, yet the state is still `0.4318`: that's memory. The output is `[[[0.4621], [0.4318], [-0.0681]]]`, shape `(1, 3, 1)`. With `1 × 1` weights, transposing `W_hh` makes no difference, which is why the second example exists.

**Example 2**: `B = 1`, `T = 2`, `d_in = H = 2`. `x = [[1, 0], [0, 1]]`, `h0 = [0.1, -0.2]`, `W_xh = I`, `W_hh = [[0, 1], [-0.5, 0]]`, `b = [0, 0.1]`.

| `t` | `x_t W_xh` | `h_{t-1} W_hh` | `a_t` | `h_t` |
|---|---|---|---|---|
| 0 | `[1, 0]` | `[0.1, 0.1]` | `[1.1, 0.2]` | `[0.8005, 0.1974]` |
| 1 | `[0, 1]` | `[-0.0987, 0.8005]` | `[-0.0987, 1.9005]` | `[-0.0984, 0.9563]` |

Work out `h0 @ W_hh` once by hand: row `[0.1, -0.2]` times the matrix gives `[0.1·0 + (-0.2)(-0.5), 0.1·1 + (-0.2)·0] = [0.1, 0.1]`. With the transposed matrix you'd get `[-0.2, 0.05]` and a first state of `[0.664, 0.05]`. `W_hh` isn't symmetric, so the convention matters.

## 5. Key idea: loop over time, vectorize over batch

There's no way around a Python loop over `T`: step `t` needs the result of step `t - 1`. But inside each step, the whole batch is one matrix product: `(B, d_in) @ (d_in, H)` and `(B, H) @ (H, H)`. Each row of `h` is one sequence, and they never interact, because matrix multiplication treats rows independently.

You can also pull the input projection out of the loop, since it doesn't depend on $h$:

```python
xw = x @ W_xh + b              # (B, T, d_in) @ (d_in, H) -> (B, T, H), all steps at once
for t in range(T):
    h = np.tanh(xw[:, t] + h @ W_hh)
```

`x @ W_xh` on a 3-D array multiplies the last axis by the matrix and keeps `(B, T)` as batch axes. That turns `T` small matrix products into one large one, which is what cuDNN does for real RNNs. Only the `h @ W_hh` part is truly sequential.

## 6. Plan before you code

```
B, T = x.shape[0], x.shape[1]
h = h0                                   # (B, H)
states = empty (B, T, H)
for t in 0 .. T-1:
    h = tanh(x[:, t] @ W_xh + h @ W_hh + b)    # (B, H)
    states[:, t] = h                           # store AFTER the update
return states
```

## 7. Build it one piece at a time

**Step 1: shapes and the output buffer.** Preallocating `(B, T, H)` avoids stacking a list at the end and makes the shape explicit.

```python
B, T, _ = x.shape                        # e.g. (4, 10, 3)
h = h0                                   # (B, H)
states = np.empty((B, T, h0.shape[1]))   # (B, T, H)
```

**Step 2: one step.** Each term is `(B, H)`, and `b` broadcasts from `(H,)` over the `B` rows.

```python
xt = x[:, t]                             # (B, d_in)
h = np.tanh(xt @ W_xh + h @ W_hh + b)    # (B, d_in)@(d_in, H) + (B, H)@(H, H) + (H,) -> (B, H)
```

Rebinding `h` with `=` creates a new array each step, so writing it into `states` stores a snapshot. Nothing later overwrites it.

**Step 3: store after updating.** `states[:, t] = h` writes a `(B, H)` slice into the `(B, T, H)` buffer. Put it **after** the update, so slot `t` holds the state that has read `x[:, t]`. Storing before the update would give `h0` in slot 0 and drop the last state.

## 8. Full solution

```python
# NumPy for the batched matrix products and tanh
import numpy as np


# run a tanh (Elman) RNN over a batch of sequences and return every hidden state
def rnn_forward(x, h0, W_xh, W_hh, b):
    B, T, _ = x.shape                     # batch size and number of time steps; d_in isn't needed
    h = h0                                # (B, H) state before the first input
    states = np.empty((B, T, h0.shape[1]))  # (B, T, H) output buffer, one slot per step
    for t in range(T):                    # time must be sequential: step t needs h from step t-1
        h = np.tanh(x[:, t] @ W_xh + h @ W_hh + b)  # (B, H); rows are vectors, so h @ W_hh, not W_hh @ h
        states[:, t] = h                  # store AFTER the update: slot t has read x[:, t]
    return states                         # h_1 .. h_T, excluding h0
```

## 9. How the test cases map to the code

| test case | expected (first values) | what it checks |
|---|---|---|
| Example 1 | `[0.4621, 0.4318, -0.0681]` | the recurrence carries memory through a zero input |
| Example 2 | `[[0.8005, 0.1974], [-0.0984, 0.9563]]` | a non-symmetric `W_hh`: `h @ W_hh`, not transposed |
| single step | `states[0, 0, 0] = -0.8548` | `T = 1`: output is `h_1`, not `h0` |
| batch of sequences | `states[0, 1, 0] = -0.4340` | `B = 4`, `T = 10`: rows stay independent |
| nonzero h0 matters | `states[0, 0, 0] = 0.9543` | `h0` feeds the first step |
| long sequence | shape `(2, 40, 6)` | 40 steps: no drift, state stays bounded |
| saturating weights | `states[0, 1, 0] = -0.999965` | weights × 3: tanh saturates but never overflows |
| wide hidden | `states[0, 0, 0] = -0.7460` | `d_in = 8`, `H = 16`: non-square `W_xh` |

## 10. Complexity

Each step costs $O(B \cdot d_{in} \cdot H)$ for the input projection and $O(B \cdot H^2)$ for the recurrence, so the whole sequence is $O(T \cdot B \cdot H\,(d_{in} + H))$ time. Memory is $O(B \cdot T \cdot H)$ for the returned states; the loop itself only needs the current `h`.

The cost that matters in production is not the FLOPs but the **sequential depth**: `T` dependent steps that can't run in parallel. A GPU can multiply a `(B, H) × (H, H)` matrix very fast, but it has to wait for step `t - 1` before starting step `t`. That's the main reason transformers replaced RNNs: attention (problem 63) processes all `T` positions at once during training. The RNN's advantage is at inference time: constant memory per step, independent of how long the sequence has been, which is why state-space models revisit the idea.

## 11. If you got Wrong Answer

- **Example 1 passes but Example 2 gives `[0.664, 0.05]` for the first state.** You used `h @ W_hh.T` (or `W_hh @ h`). With `1 × 1` weights the transpose is invisible, so only Example 2 and the larger cases catch it.
- **`states[:, 0]` equals `h0` (`0` in Example 1, `[0.1, -0.2]` in Example 2).** You stored the state before updating it. Every case fails, starting at index 0.
- **"single step" passes, but `states[:, 1]` is wrong everywhere else (Example 1 gives `0` at step 1).** You used `h0` at every step instead of the running `h`, so there's no recurrence. A one-step sequence can't tell the difference.
- **Output shape is `(B, T + 1, H)`.** You included `h0`. Drop it.

## 12. Follow-ups an interviewer might ask

- *How would you write the backward pass?* Backpropagation through time: walk `t` from `T - 1` down to 0, with $\bar a_t = \bar h_t \odot (1 - h_t^2)$, $\bar W_{hh} \mathrel{+}= h_{t-1}^\top \bar a_t$, $\bar W_{xh} \mathrel{+}= x_t^\top \bar a_t$, and $\bar h_{t-1} = \bar a_t W_{hh}^\top$ plus that step's own loss gradient. Each weight is shared across time, so its gradient sums over steps, the same `+=` rule as problems 56 and 59.
- *Why do vanilla RNNs struggle with long-range dependencies?* The gradient through `k` steps is a product of `k` Jacobians $\operatorname{diag}(1 - h^2) W_{hh}^\top$, which vanishes or explodes exponentially. LSTMs and GRUs (problems 61 and 62) add gates and an additive path.
- *What does `h0` usually hold?* Zeros for a fresh sequence, or the last state of the previous chunk when you process a long stream in pieces (truncated BPTT).
- *How would you handle sequences of different lengths in one batch?* Pad them to length `T` and keep a mask; for padded steps, keep the old state, for example `h = np.where(mask[:, t, None], h_new, h)`.
