## 1. What the problem is really asking

A GRU is the LSTM's leaner cousin (problem 61). It has no separate cell state: the hidden state $h$ is the memory. Two gates control it. The **update gate** $z$ decides, unit by unit, whether to keep the old state or replace it with a fresh candidate. The **reset gate** $r$ decides how much of the old state the candidate is allowed to look at.

Strip the story and the problem is **a time loop with two matrix products per step, a three-way slice, and an interpolation**. Two things make it more than a copy of the LSTM: you run the whole sequence and collect every state, and the reset gate is applied in PyTorch's specific place, *after* the hidden product and *including* its bias. That placement is what most wrong answers get wrong.

The judge compares the full `(B, T, H)` array of states at `rtol = 1e-6`.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `x` | `(B, T, d_in)` | a batch of sequences | slice `x[:, t]`, shape `(B, d_in)`, per step |
| `h0` | `(B, H)` | the starting state | the first `h_{t-1}`; not part of the output |
| `W_ih` | `(d_in, 3H)` | input weights for r, z, n side by side | `x[:, t] @ W_ih` |
| `W_hh` | `(H, 3H)` | hidden weights, same layout | `h @ W_hh` |
| `b_ih`, `b_hh` | `(3H,)` each | two separate biases | added to their own projection |

Easy to miss:

- **The order is r, z, n**, in contiguous blocks of width `H`. Reset first, update second.
- **There are two biases, and they are not interchangeable.** For r and z they just add, so only their sum matters. For n, `b_hn` is multiplied by `r` and `b_in` is not.
- **The output excludes `h0`.** `states[:, t]` is the state *after* reading `x[:, t]`, so the output has `T` time slices, not `T + 1`.

## 3. The math

Per step, the two projections are

$$
g^x = x_t W_{ih} + b_{ih}, \qquad g^h = h_{t-1} W_{hh} + b_{hh}, \qquad g^x, g^h \in \mathbb{R}^{B \times 3H}.
$$

Write $g_r, g_z, g_n$ for the three `(B, H)` blocks. Then

$$
r = \sigma(g^x_r + g^h_r), \qquad z = \sigma(g^x_z + g^h_z),
$$

$$
n = \tanh\!\big(g^x_n + r \odot (h_{t-1} W_{hn} + b_{hn})\big), \qquad h_t = (1 - z) \odot n + z \odot h_{t-1}.
$$

**The update is an interpolation.** Rewrite the last line as $h_t = h_{t-1} + (1 - z) \odot (n - h_{t-1})$. Each unit moves a fraction $1 - z$ of the way from its old value toward the candidate. At $z = 1$ it copies itself unchanged; at $z = 0$ it is fully replaced. Since $n \in (-1, 1)$, a state that starts inside $(-1, 1)$ stays there.

**Why it remembers.** Differentiate $h_t$ with respect to $h_{t-1}$. The product rule gives the direct term plus terms through the gates:

$$
\frac{\partial h_t}{\partial h_{t-1}} = \operatorname{diag}(z) \;+\; \operatorname{diag}(1 - z)\,\frac{\partial n}{\partial h_{t-1}} \;+\; \operatorname{diag}(h_{t-1} - n)\,\frac{\partial z}{\partial h_{t-1}} .
$$

When the update gate saturates near 1, the first term is close to the identity and the other two are small, because $1 - z \approx 0$ and $\partial z / \partial h = \operatorname{diag}(z(1-z))\,W_{hz}^\top \approx 0$. The gradient then passes through the step almost unchanged, which is the same trick as the LSTM's forget gate.

**Where the reset gate goes.** The original GRU (Cho et al., 2014) computes $n = \tanh(g^x_n + (r \odot h_{t-1}) W_{hn} + b_{hn})$, resetting the state *before* the product. PyTorch and cuDNN use $r \odot (h_{t-1} W_{hn} + b_{hn})$ instead, so that $h_{t-1} W_{hh}$ for all three gates is one product computed before $r$ is known. The two give different numbers, and the problem asks for PyTorch's.

**Stability.** The constraints keep pre-activations within `±50`, so the plain $1/(1 + e^{-a})$ is safe here: $e^{50} \approx 5 \times 10^{21}$, far below float64's limit. If you might see `±1000`, use the two-branch sigmoid from problem 61.

## 4. Trace Example 2 by hand

`x` is `(2, 1, 2)`: two sequences, one step each. `H = 2`, `b_ih = 0`, `b_hh = [0, 0, 0, 0, 0.5, 0.5]`.

| quantity | shape | sequence 0 (`h0 = [0, 0]`) | sequence 1 (`h0 = [1, -1]`) |
|---|---|---|---|
| `gi` | `(2, 6)` | `[1, 0, -1, 0, 0.5, 0]` | `[0, 1, 0, -1, 0, 0.5]` |
| `gh` | `(2, 6)` | `[0, 0, 0, 0, 0.5, 0.5]` | `[0.2, -0.2, 0, 0, 1.5, -0.5]` |
| `r` | `(2, 2)` | `[0.7311, 0.5]` | `[0.5498, 0.69]` |
| `z` | `(2, 2)` | `[0.2689, 0.5]` | `[0.5, 0.2689]` |
| `n` | `(2, 2)` | `[0.6991, 0.2449]` | `[0.6776, 0.1538]` |
| `h` | `(2, 2)` | `[0.5111, 0.1225]` | `[0.8388, -0.1565]` |

Look at sequence 0, unit 0. The state is all zeros, yet `gh_n = 0.5`, because the product is zero but the bias `b_hn` is not. The candidate is `tanh(0.5 + 0.7311 * 0.5) = 0.6991`. If you add `b_hn` outside the reset gate, you get `tanh(0.5 + 0.5)` and the final `h` becomes `0.5568` instead of `0.5111`. That's why this example sets a nonzero `b_hh`: it's the only way to tell the placements apart.

Then `h = (1 - 0.2689) * 0.6991 + 0.2689 * 0 = 0.5111`.

**Example 1** checks the time loop. `H = 1`, every gate pre-activation is 0, so `r = z = 0.5`.

| step | `x_t` | `gh_n = h_prev` | `n = tanh(x_t + 0.5 gh_n)` | `h` |
|---|---|---|---|---|
| 0 | `1` | `0.5` | `0.8483` | `0.6741` |
| 1 | `2` | `0.6741` | `0.9815` | `0.8278` |

Step 1 uses step 0's output as its `h_prev`. The output `[[[0.6741], [0.8278]]]` has shape `(1, 2, 1)` and doesn't contain `h0 = 0.5`. Example 1 can't catch gate-order, interpolation or bias bugs, though: with `r = z = 0.5` and zero biases, all three mistakes give the same numbers.

## 5. Key idea: keep the hidden projection whole

Compute `gh = h @ W_hh + b_hh` once, as a full `(B, 3H)` block, and multiply its n-block by `r` afterwards. Don't slice `W_hh` and add `b_hh[2H:]` separately. Keeping it whole is shorter, matches PyTorch exactly, and makes the bias land inside the reset product without you having to think about it. It's also why cuDNN chose this formulation: one fused product per step for all three gates.

## 6. Plan before you code

```
H = h0.shape[1]; h = h0
states = empty (B, T, H)
for t in 0..T-1:
    gi = x[:, t] @ W_ih + b_ih       # (B, 3H)
    gh = h @ W_hh + b_hh             # (B, 3H)
    r = sigmoid(gi_r + gh_r)         # (B, H)
    z = sigmoid(gi_z + gh_z)         # (B, H)
    n = tanh(gi_n + r * gh_n)        # (B, H), bias inside
    h = (1 - z) * n + z * h          # (B, H)
    states[:, t] = h
return states
```

| block | columns | role |
|---|---|---|
| r | `0:H` | reset: scales the hidden contribution to n |
| z | `H:2H` | update: weight on the old state |
| n | `2H:3H` | candidate |

## 7. Build it one piece at a time

**Step 1: allocate the output and start the state.**

```python
B, T, _ = x.shape
H = h0.shape[1]
h = h0                          # (B, H)
states = np.empty((B, T, H))    # filled one time slice per step
```

**Step 2: the two projections.** `x[:, t]` drops the time axis, giving `(B, d_in)`. Each bias of shape `(3H,)` broadcasts across the batch rows.

```python
gi = x[:, t] @ W_ih + b_ih      # (B, d_in)@(d_in, 3H) -> (B, 3H)
gh = h @ W_hh + b_hh            # (B, H)@(H, 3H)       -> (B, 3H)
```

**Step 3: the gates and the candidate.**

```python
r = sigmoid(gi[:, :H] + gh[:, :H])                 # (B, H)
z = sigmoid(gi[:, H:2 * H] + gh[:, H:2 * H])       # (B, H)
n = np.tanh(gi[:, 2 * H:] + r * gh[:, 2 * H:])     # (B, H); gh's n-block already holds b_hn
```

**Step 4: interpolate and record.** Rebinding `h` with `=` makes a new array, so `states[:, t]` holds a copy of this step's values and later steps can't change it.

```python
h = (1 - z) * n + z * h         # z = 1 keeps the old state
states[:, t] = h                # (B, H) into slice t of (B, T, H)
```

## 8. Full solution

```python
# arrays in, arrays out
import numpy as np


# plain logistic; safe here because the constraints keep pre-activations within +-50
def sigmoid(a):
    return 1.0 / (1.0 + np.exp(-a))  # exp(50) is ~5e21, nowhere near float64 overflow


# run PyTorch's GRU over every time step and return all T states (not h0)
def gru_forward(x, h0, W_ih, W_hh, b_ih, b_hh):
    B, T, _ = x.shape  # x is (B, T, d_in); d_in is implied by W_ih
    H = h0.shape[1]  # hidden size comes from the initial state
    h = h0  # (B, H) the state each step reads; starts at h0
    states = np.empty((B, T, H))  # one (B, H) slice per step, filled in order
    # the recurrence is sequential: step t needs step t-1's output
    for t in range(T):
        gi = x[:, t] @ W_ih + b_ih  # (B, 3H) input projection for r, z, n at once
        gh = h @ W_hh + b_hh  # (B, 3H) hidden projection kept whole, so b_hn sits inside it
        r = sigmoid(gi[:, :H] + gh[:, :H])  # (B, H) reset gate: block 0
        z = sigmoid(gi[:, H:2 * H] + gh[:, H:2 * H])  # (B, H) update gate: block 1
        n = np.tanh(gi[:, 2 * H:] + r * gh[:, 2 * H:])  # (B, H) candidate; r scales W_hn h + b_hn together
        h = (1 - z) * n + z * h  # (B, H) interpolate: z = 1 copies the old state, z = 0 takes n
        states[:, t] = h  # the state after reading x[:, t]
    return states  # (B, T, H)
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `[[[0.6741], [0.8278]]]` | the time loop: step 1 reads step 0's state, `h0` excluded |
| Example 2 | `h[0, 0] = [0.5111, 0.1225]` | gate order and the bias `b_hn` inside the reset product, even when `h = 0` |
| random batch | `(4, 8, 5)`, first element `-0.2494` | batching over 8 steps with random biases |
| large hidden bias | `(3, 5, 4)`, first element `0.5046` | `b_hn = [2, -2, 1.5, -1]`, which makes the bias placement visible |
| single unit long | `(2, 40, 1)`, first element `0.2002` | `T = 40`, the longest sequence |
| wide | `(2, 6, 16)`, first element `-0.274` | `d_in = 8`, `H = 16` slicing |
| strong gates | `(3, 10, 3)`, first element `0.8895` | weight scale 1.5 and bias scale 1, gates near saturation |

## 10. Complexity

Each step does two products, $O(B \cdot 3H \cdot (d_{in} + H))$, so the whole run is $O(T \cdot B \cdot 3H\,(d_{in} + H))$ time. Memory is $O(BTH)$ for the output and $O(BH)$ working state. A GRU has three gate blocks to the LSTM's four, so it is about 25% cheaper per step for the same width. The loop over $T$ is inherently sequential. In production you hoist the input projection out of the loop as one `(B·T, d_in) @ (d_in, 3H)` product and leave only `h @ W_hh` inside.

## 11. If you got Wrong Answer

Example 1 passes for all three classic bugs below, so look at Example 2.

- **Example 2's first value is `0.5568` instead of `0.5111`.** The bias `b_hn` is outside the reset gate: `r * (h @ W_hn) + b_hn`. The original Cho et al. form, `(r * h) @ W_hn + b_hn`, gives the same `0.5568` here because `h = 0`, and it fails every other case too. Keep `gh` whole and multiply its n-block by `r`.
- **Example 2 gives `0.1509`.** You read the gates as z, r, n. The order is r, z, n.
- **Example 2 gives `0.188`.** You wrote `h = z * n + (1 - z) * h`. That's a valid convention elsewhere, but PyTorch's `z` weights the *old* state.
- **Shape `(B, T + 1, H)`, or every state shifted by one step.** You stored `h0`, or stored `h` before updating it.

## 12. Follow-ups an interviewer might ask

- *GRU or LSTM?* A GRU has about 25% fewer parameters and often matches an LSTM on moderate-length sequences. An LSTM's separate cell state and output gate give it more control on long dependencies (problem 61).
- *How do you handle sequences of different lengths in one batch?* Pass a mask of shape `(B, T)` and, for padded steps, keep the old state: `h = np.where(mask[:, t, None], h_new, h)`. The `None` adds a trailing axis so the `(B,)` mask broadcasts over `H`.
- *How would you make it bidirectional?* Run a second GRU on `x[:, ::-1]`, reverse its outputs back, and concatenate along the last axis to get `(B, T, 2H)`.
- *How do you get the gradient through 40 steps?* Backpropagation through time: run the steps in reverse and accumulate into `W_ih`, `W_hh` and the biases, using the Jacobian from section 3. Clip the global gradient norm (problem 55) to tame the occasional explosion.
