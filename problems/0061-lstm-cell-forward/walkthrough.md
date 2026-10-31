## 1. What the problem is really asking

An LSTM step is a vanilla RNN step (problem 60) with **three valves and a separate memory lane**. The model keeps two vectors per sequence: the cell state $c$, which carries long-term memory, and the hidden state $h$, which is what the rest of the network reads. Each step decides how much of the old memory to keep (forget gate), how much new content to write (input gate and candidate), and how much of the memory to expose (output gate).

Strip the story and the problem is **one matrix product, a slice into four blocks, and five elementwise lines**. All four gates are linear in the same two inputs, `x` and `h_prev`, so one stacked product of width $4H$ computes all of them at once. The only real decisions are which columns belong to which gate and how to write a sigmoid that survives `±1000`.

The judge compares both returned arrays, `h` and `c`, at `rtol = 1e-6`.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `x` | `(B, d_in)` | the input at this time step, one row per sequence | `x @ W` |
| `h_prev` | `(B, H)` | last step's hidden state | `h_prev @ U`; also gives you `H` |
| `c_prev` | `(B, H)` | last step's cell state | multiplied by the forget gate |
| `W` | `(d_in, 4H)` | input weights for all four gates side by side | one product |
| `U` | `(H, 4H)` | recurrent weights, same column layout | one product |
| `b` | `(4H,)` | bias, same column layout | broadcast over the batch |

Easy to miss:

- **The column layout is i, f, g, o, in contiguous blocks.** Columns `0:H` are the input gate, `H:2H` the forget gate, `2H:3H` the candidate, `3H:4H` the output gate. Keras and some papers use other orders; the problem fixes PyTorch's.
- **Only `g` uses tanh.** The three gates are sigmoids, because they are fractions in $(0, 1)$. The candidate is content, which can be negative.
- **`H` is not passed in.** Read it from `h_prev.shape[1]`.

## 3. The math

Name the stacked pre-activation $z \in \mathbb{R}^{B \times 4H}$:

$$
z = x W + h_{t-1} U + \mathbf{1} b^\top .
$$

Shapes: $(B, d_{in})(d_{in}, 4H)$ is $(B, 4H)$, $(B, H)(H, 4H)$ is $(B, 4H)$, and $b$ is added to every row. Split $z$ into $z_i, z_f, z_g, z_o$, each $(B, H)$, then

$$
i = \sigma(z_i), \quad f = \sigma(z_f), \quad g = \tanh(z_g), \quad o = \sigma(z_o),
$$

$$
c_t = f \odot c_{t-1} + i \odot g, \qquad h_t = o \odot \tanh(c_t),
$$

where $\odot$ is the elementwise product and $\sigma(a) = 1/(1+e^{-a})$.

**Why the cell state remembers.** Take the derivative of $c_t$ with respect to $c_{t-1}$, holding the gates fixed (the direct path). The update is elementwise, so the Jacobian is diagonal:

$$
\frac{\partial c_t}{\partial c_{t-1}} = \operatorname{diag}(f).
$$

Over $T$ steps the gradient along this path is $\prod_{t} \operatorname{diag}(f_t)$. If the forget gate sits near 1, that product stays near 1 and the gradient survives. Compare a vanilla RNN, $h_t = \tanh(x W + h_{t-1} U + b)$, where

$$
\frac{\partial h_t}{\partial h_{t-1}} = \operatorname{diag}\!\big(1 - h_t^2\big)\, U^\top ,
$$

a product of a squashing factor $\le 1$ and a matrix on every step. That product shrinks or blows up geometrically. The additive cell update is the whole reason LSTMs exist.

**A sigmoid that cannot overflow.** $e^{-a}$ overflows float64 once $-a > 709$, so at $a = -1000$ the textbook form computes `1 / (1 + inf)`. That happens to give the right `0.0`, but with an overflow warning. The form $e^{a}/(1+e^{a})$ is worse: at $a = 1000$ it is `inf / inf = nan`. Fix it by never exponentiating a positive number. Let $e = e^{-|a|} \in (0, 1]$. For $a \ge 0$, $e = e^{-a}$ and $\sigma(a) = 1/(1+e)$. For $a < 0$, $e = e^{a}$ and multiplying the textbook form by $e^{a}/e^{a}$ gives

$$
\sigma(a) = \frac{1}{1 + e^{-a}} = \frac{e^{a}}{e^{a} + 1} = \frac{e}{1 + e}.
$$

Both branches only ever see $e \le 1$. `np.tanh` is already stable at any input, so it needs no trick.

## 4. Trace Example 2 by hand

`x = [[1, -1]]` is `(1, 2)`, `H = 2`, `U` is all zeros, so $z = xW + b$, shape `(1, 8)`. Row 0 of `W` minus row 1, plus `b`:

| block | columns | `z` | activation | value |
|---|---|---|---|---|
| input `i` | 0–1 | `[0.2, 0.2]` | sigmoid | `[0.5498, 0.5498]` |
| forget `f` | 2–3 | `[1.2, 1.4]` | sigmoid | `[0.7685, 0.8022]` |
| candidate `g` | 4–5 | `[0.7, 0.4]` | tanh | `[0.6044, 0.3799]` |
| output `o` | 6–7 | `[-0.3, -0.3]` | sigmoid | `[0.4256, 0.4256]` |

Then, all `(1, 2)`:

| quantity | unit 0 | unit 1 |
|---|---|---|
| `f * c_prev` | `0.2306` | `0` |
| `i * g` | `0.3323` | `0.2089` |
| `c` | `0.5629` | `0.2089` |
| `tanh(c)` | `0.5101` | `0.2059` |
| `h = o * tanh(c)` | `0.2171` | `0.0876` |

That matches the expected `([[0.2171, 0.0876]], [[0.5629, 0.2089]])`. Unit 1 starts with `c_prev = 0`, so its whole cell state is the new write `i * g`.

**The hidden case "saturated gates"** is the one to understand. The bias is `±1000` in a fixed pattern, so every gate is exactly 0 or 1 regardless of the inputs (`H = 4`):

| unit | i | f | g | o | `c` | `h` |
|---|---|---|---|---|---|---|
| 0 | 1 | 0 | 1 | 0 | `1` (overwritten) | `0` (hidden) |
| 1 | 0 | 1 | -1 | 1 | `c_prev` = `0.8178` | `tanh(0.8178)` = `0.6738` |
| 2 | 1 | 1 | 1 | 1 | `c_prev + 1` = `0.5923` | `0.5316` |
| 3 | 1 | 0 | 1 | 0 | `1` | `0` |

These are the LSTM's three moves in their purest form: overwrite, keep, and accumulate. A sigmoid that returns `nan` at `1000` poisons the whole row.

## 5. Key idea: one product, then slice

You could keep eight weight matrices, one $W$ and one $U$ per gate. Stacking them side by side into a single `(d_in, 4H)` matrix is mathematically identical, because column block $k$ of $xW$ is $x$ times column block $k$ of $W$. One large matmul is much faster on real hardware than four small ones, which is why every framework stores the weights this way. The cost is that you have to know the layout, and the layout here is **contiguous blocks**: gate $k$ owns columns $kH$ to $(k+1)H$. A reshape to `(B, H, 4)` assumes the gates are interleaved column by column, which is a different layout.

## 6. Plan before you code

```
H = h_prev.shape[1]
z = x @ W + h_prev @ U + b          # (B, 4H)
i, f, o = sigmoid of blocks 0, 1, 3 # each (B, H)
g       = tanh of block 2           # (B, H)
c = f * c_prev + i * g              # (B, H)
h = o * tanh(c)                     # (B, H)
return h, c
```

| block | columns | nonlinearity |
|---|---|---|
| i | `0:H` | sigmoid |
| f | `H:2H` | sigmoid |
| g | `2H:3H` | tanh |
| o | `3H:4H` | sigmoid |

## 7. Build it one piece at a time

**Step 1: the stable sigmoid.** Both branches are computed for every element, and `np.where` picks one. Since `e <= 1` everywhere, neither branch can overflow.

```python
def sigmoid(a):
    e = np.exp(-np.abs(a))                                      # same shape as a, values in (0, 1]
    return np.where(a >= 0, 1.0 / (1.0 + e), e / (1.0 + e))
```

**Step 2: the stacked pre-activation.**

```python
H = h_prev.shape[1]
z = x @ W + h_prev @ U + b       # (B, d_in)@(d_in, 4H) + (B, H)@(H, 4H) + (4H,) -> (B, 4H)
```

Broadcasting aligns trailing axes, so `b` of shape `(4H,)` is treated as `(1, 4H)` and added to every row. No reshape is needed.

**Step 3: slice and activate.**

```python
i = sigmoid(z[:, 0:H])           # (B, H)
f = sigmoid(z[:, H:2 * H])       # (B, H)
g = np.tanh(z[:, 2 * H:3 * H])   # (B, H)  the only tanh
o = sigmoid(z[:, 3 * H:4 * H])   # (B, H)
```

**Step 4: the two state updates.** Everything is `(B, H)` against `(B, H)`, so no broadcasting happens here.

```python
c = f * c_prev + i * g           # keep part of the old memory, write part of the new
h = o * np.tanh(c)               # squash, then gate what is exposed
```

## 8. Full solution

```python
# arrays in, arrays out
import numpy as np


# a logistic sigmoid that never exponentiates a positive number, so +-1000 is safe
def sigmoid(a):
    e = np.exp(-np.abs(a))  # e^{-|a|} is in (0, 1] for every element: no overflow possible
    # a >= 0: 1/(1+e^{-a}); a < 0: e^{a}/(1+e^{a}), the same value rewritten to keep e <= 1
    return np.where(a >= 0, 1.0 / (1.0 + e), e / (1.0 + e))


# one LSTM step for a batch; gates stacked in PyTorch's i, f, g, o order
def lstm_cell(x, h_prev, c_prev, W, U, b):
    H = h_prev.shape[1]  # hidden size isn't passed in; read it from the state
    z = x @ W + h_prev @ U + b  # (B, 4H): all four gates in one product; b broadcasts over rows
    i = sigmoid(z[:, 0:H])  # (B, H) input gate: how much new content to write
    f = sigmoid(z[:, H:2 * H])  # (B, H) forget gate: how much old memory to keep
    g = np.tanh(z[:, 2 * H:3 * H])  # (B, H) candidate content; tanh because it can be negative
    o = sigmoid(z[:, 3 * H:4 * H])  # (B, H) output gate: how much memory to expose
    c = f * c_prev + i * g  # (B, H) additive update, the path long-range gradients travel
    h = o * np.tanh(c)  # (B, H) squash the memory into (-1, 1), then gate it
    return h, c  # the judge checks both states
```

## 9. How the test cases map to the code

| test case | expected (first elements) | what it checks |
|---|---|---|
| Example 1 | `h = 0.2793`, `c = 0.6308` | `H = 1`, every gate at `sigmoid(0) = 0.5`, `g = tanh(1)` |
| Example 2 | `h = [0.2171, 0.0876]`, `c = [0.5629, 0.2089]` | the block layout with `H = 2`, so contiguous versus interleaved matters |
| random batch | `(4, 6)`, `h[0, 0] = -0.124` | batching and a nonzero `U` |
| single unit | `(3, 1)`, `h[0, 0] = 0.3213` | `H = 1` with random weights |
| wide | `(2, 16)`, `h[0, 0] = 0.0237` | `d_in = 8`, `H = 16`: indexing at a larger width |
| strong weights | `(5, 3)`, `h[0, 0] = 0.017` | weight scale 2, so gates near saturation |
| saturated gates | `h = [0, 0.6738, 0.5316, 0]` | pre-activations of `±1000`: the stable sigmoid |

## 10. Complexity

The two products cost $O(B \cdot 4H \cdot (d_{in} + H))$ time; everything after is $O(BH)$. Memory is $O(BH)$ for the gates on top of the $O(4H(d_{in} + H))$ weights. An LSTM layer has four times the parameters of a vanilla RNN of the same width. The bigger production cost is that time steps are sequential: step $t$ needs $h_{t-1}$, so you can't parallelize over the sequence the way attention does (problem 63). That is a large part of why transformers replaced LSTMs for long sequences.

## 11. If you got Wrong Answer

- **Every case fails, Example 1 gives `h = 0.179` instead of `0.2793`.** You used the order i, f, o, g (common in some write-ups), so the tanh is applied to the output-gate block. Use i, f, g, o.
- **Example 1 and "single unit" pass, Example 2 gives `0.444` instead of `0.2171`.** You split the gates as interleaved columns, for example with `z.reshape(B, H, 4)`. With `H = 1` the two layouts coincide, which is why only the multi-unit cases catch it.
- **`h` is a little too large everywhere (Example 1 `0.3154` instead of `0.2793`), but `c` is right.** You returned `o * c`. The output is `o * tanh(c)`.
- **Only "saturated gates" fails, with `nan`.** Your sigmoid is `np.exp(a) / (1 + np.exp(a))`, which is `inf / inf` at `a = 1000`. Use the two-branch form from section 3.

## 12. Follow-ups an interviewer might ask

- *Why initialize the forget-gate bias to 1?* It starts $f = \sigma(1) \approx 0.73$ rather than 0.5, so the cell keeps more memory early in training and the $\prod f_t$ gradient path from section 3 doesn't vanish before the network learns to use it.
- *How does a GRU differ?* It merges the cell and hidden states and uses two gates instead of three, with $h_t = (1 - z) \odot n + z \odot h_{t-1}$ (problem 62).
- *What is the backward pass?* Reverse the five elementwise lines: $\partial L/\partial c_{t-1} = \partial L/\partial c_t \odot f$, and each gate's gradient goes through its activation's derivative, $\sigma(1-\sigma)$ or $1 - \tanh^2$, back into the stacked $z$, then $\partial L/\partial W = x^\top\, \partial L/\partial z$.
- *How would you run a whole sequence?* Loop $t = 1..T$, feeding each step's `(h, c)` into the next. Precompute $xW$ for all $T$ steps in one `(T·B, d_in) @ (d_in, 4H)` product, since it doesn't depend on $h$; only the $hU$ part has to be sequential.
