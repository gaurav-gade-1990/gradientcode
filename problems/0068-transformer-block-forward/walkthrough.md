## 1. What the problem is really asking

A decoder-only LLM is a stack of identical blocks. Each block reads the **residual stream** `x`, lets every token gather information from earlier tokens (attention), lets every token transform what it gathered on its own (the MLP), and writes both results back into the stream by addition. This problem is one such block, in the pre-LN layout of GPT-2 and most models since.

Strip the story and the problem is **four helpers wired with two residual adds**: LayerNorm, causal multi-head attention (problems 63 to 65), a tanh-approximate GELU, and a two-layer MLP. No single piece is hard. The difficulty is wiring: what gets normalized, what gets added to what, and which exact formula each helper uses. The judge compares the `(B, T, d)` output at `rtol = 1e-6`, so even the GELU variant matters.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `x` | `(B, T, d)` | the residual stream entering the block | normalized for each sublayer, never overwritten by a norm |
| `ln1_g`, `ln1_b` | `(d,)` | LayerNorm 1 scale and shift | before attention |
| `W_q`, `W_k`, `W_v`, `W_o` | `(d, d)` | attention weights, no biases | causal MHA |
| `ln2_g`, `ln2_b` | `(d,)` | LayerNorm 2 scale and shift | before the MLP |
| `W1`, `b1` | `(d, d_ff)`, `(d_ff,)` | MLP up-projection | then GELU |
| `W2`, `b2` | `(d_ff, d)`, `(d,)` | MLP down-projection | back to width `d` |
| `num_heads` | int | `h`, with `d_head = d / h` | splitting heads |

Easy to miss:

- **The residual adds the un-normalized input.** `a = x + MHA(LN1(x))`, not `LN1(x) + MHA(LN1(x))`.
- **The causal mask is built inside the block.** It isn't passed in. Every head, every batch element: query `t` sees keys `0..t`.
- **Two exact formulas are fixed.** LayerNorm uses the biased variance (divide by `d`) with `eps = 1e-5` inside the square root, and GELU is the tanh approximation, not the erf form.

## 3. The math

**LayerNorm**, per token over its $d$ features:

$$
\mu = \frac{1}{d}\sum_{j=1}^{d} z_j, \qquad \sigma^2 = \frac{1}{d}\sum_{j=1}^{d}(z_j - \mu)^2, \qquad \operatorname{LN}(z) = g \odot \frac{z - \mu}{\sqrt{\sigma^2 + \epsilon}} + b .
$$

After the division, each token's features have mean 0 and variance $\sigma^2/(\sigma^2 + \epsilon)$, just under 1. The $\epsilon$ guards the division when a token is nearly constant: with $\sigma^2 = 0$ you'd divide by $\sqrt{\epsilon} \approx 0.0032$ instead of by zero.

**Causal MHA** on $u = \operatorname{LN}_1(x)$: $Q = uW_q$, $K = uW_k$, $V = uW_v$, split into heads, and for each head

$$
O_j = \operatorname{softmax}\!\left(\frac{Q_j K_j^\top}{\sqrt{d_{head}}} + M\right) V_j, \qquad M_{st} = \begin{cases} 0 & t \le s \\ -\infty & t > s \end{cases},
$$

then concatenate and multiply by $W_o$.

**GELU** is $z\,\Phi(z)$ with $\Phi$ the standard normal CDF. The problem fixes its tanh approximation:

$$
\operatorname{GELU}(z) \approx \tfrac{1}{2} z \left(1 + \tanh\!\left(\sqrt{2/\pi}\,(z + 0.044715\, z^3)\right)\right).
$$

Over $z \in [-6, 6]$ the two forms differ by at most `4.7e-4` (at $z \approx 2.7$), far above the judge's `1e-6`.

**The block**:

$$
a = x + \operatorname{MHA}(\operatorname{LN}_1(x)), \qquad y = a + \big(\operatorname{GELU}(\operatorname{LN}_2(a) W_1 + b_1)\big) W_2 + b_2 .
$$

**Why pre-LN trains well: the gradient path.** Differentiate the first line with respect to $x$:

$$
\frac{\partial a}{\partial x} = I + \frac{\partial\, \operatorname{MHA}(\operatorname{LN}_1(x))}{\partial x} .
$$

The identity term means the gradient from $a$ reaches $x$ unchanged, plus whatever the sublayer adds. Chain $L$ blocks and the product of Jacobians always contains the term $I \cdot I \cdots I$, a clean path from the loss to the first layer. In post-LN, $a = \operatorname{LN}(x + f(x))$, every block's Jacobian is multiplied by LayerNorm's Jacobian, which rescales by $1/\sigma$ and projects out the mean, so there is no pure identity path. That's why post-LN stacks need learning-rate warmup and pre-LN stacks mostly don't.

**Stability.** The softmax uses the row-max shift. "large activations" has `x` scaled by 10 and weights by 1.5, with outputs up to about `41` in magnitude. LayerNorm keeps the sublayer inputs at unit scale whatever the stream's magnitude, which is the other reason pre-LN is stable.

## 4. Trace Example 1 by hand

`x = [[[1, -1], [3, 1]]]` is `(1, 2, 2)`, one head, identity attention weights, `W1 = I`, `W2 = 0.5 I`, all LayerNorm scales 1 and shifts 0, all biases 0.

| step | token 0 | token 1 | note |
|---|---|---|---|
| `x` | `[1, -1]` | `[3, 1]` | |
| mean, variance | `0`, `1` | `2`, `1` | biased variance, divide by `d = 2` |
| `u = LN1(x)` | `[1, -1]` | `[1, -1]` | `0.999995` really, from `eps` |
| scores `u u^T / sqrt(2)` | `[1.4142, masked]` | `[1.4142, 1.4142]` | `(1, 1, 2, 2)` |
| attention out | `[1, -1]` | `[1, -1]` | every value row is `[1, -1]` |
| `a = x + attn` | `[2, -2]` | `[4, 0]` | residual from **`x`**, not `u` |
| `LN2(a)` | `[1, -1]` | `[1, -1]` | |
| `GELU(LN2(a) @ W1)` | `[0.8412, -0.1588]` | `[0.8412, -0.1588]` | `(1, 2, 2)`; `W1 = I` |
| `m = ... @ W2` | `[0.4206, -0.0794]` | `[0.4206, -0.0794]` | `W2 = 0.5 I` |
| `y = a + m` | `[2.4206, -2.0794]` | `[4.4206, -0.0794]` | expected output |

Both tokens normalize to the same vector, so they're identical after LayerNorm: the stream's scale and offset survive only through the residual. That's what this example tests. Adding the residual from `u` instead gives `y[0, 0] = 1.4206`. Post-LN gives about `1.0`, because the output passes through a final normalization. The example can't test the mask, though: every value row is the same, so attending to the future changes nothing. Example 2 and the larger cases catch that.

## 5. Key idea: the stream is never normalized

Think of `x` as a shared bus. Each sublayer takes a normalized *copy* of the bus, computes something, and adds the result back. The bus itself keeps its raw scale from block to block. Every wrong wiring breaks this in one way or another:

| wiring | `a` | what breaks |
|---|---|---|
| pre-LN (correct) | `x + MHA(LN(x))` | nothing |
| post-LN | `LN(x + MHA(x))` | the stream is renormalized every block |
| residual from normed | `LN(x) + MHA(LN(x))` | the stream's scale is thrown away |

## 6. Plan before you code

```
layer_norm(z, g, b): mean and biased variance over the last axis, eps inside the sqrt
gelu(z): the tanh formula
causal_mha(u, ...): split (B, T, d) -> (B, h, T, dh), scores, tril mask, stable softmax, merge, @ W_o
block:
    a = x + causal_mha(layer_norm(x, ln1))
    m = gelu(layer_norm(a, ln2) @ W1 + b1) @ W2 + b2
    return a + m
```

## 7. Build it one piece at a time

**Step 1: LayerNorm.** `keepdims=True` makes the mean and variance `(B, T, 1)`, so they broadcast across the feature axis. `g` and `b` are `(d,)` and broadcast across `(B, T)`.

```python
def layer_norm(z, g, b, eps=1e-5):
    mu = z.mean(axis=-1, keepdims=True)                     # (B, T, 1)
    var = ((z - mu) ** 2).mean(axis=-1, keepdims=True)      # (B, T, 1), biased: divides by d
    return g * (z - mu) / np.sqrt(var + eps) + b            # (B, T, d)
```

`z.var(axis=-1, keepdims=True)` is also biased by default. Passing `ddof=1` makes it unbiased, which is the bug.

**Step 2: GELU.**

```python
def gelu(z):
    return 0.5 * z * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (z + 0.044715 * z ** 3)))
```

**Step 3: causal MHA**, as in problem 65, with the mask built from `T`.

```python
def causal_mha(u, W_q, W_k, W_v, W_o, num_heads):
    B, T, d = u.shape
    dh = d // num_heads
    def split(a):                                           # (B, T, d) -> (B, h, T, dh)
        return a.reshape(B, T, num_heads, dh).transpose(0, 2, 1, 3)
    q, k, v = split(u @ W_q), split(u @ W_k), split(u @ W_v)
    s = q @ k.transpose(0, 1, 3, 2) / np.sqrt(dh)           # (B, h, T, T)
    s = np.where(np.tril(np.ones((T, T), dtype=bool)), s, -np.inf)
    s = s - s.max(axis=-1, keepdims=True)
    w = np.exp(s)
    w = w / w.sum(axis=-1, keepdims=True)
    return (w @ v).transpose(0, 2, 1, 3).reshape(B, T, d) @ W_o   # (B, T, d)
```

**Step 4: wire the block.**

```python
a = x + causal_mha(layer_norm(x, p["ln1_g"], p["ln1_b"]), p["W_q"], p["W_k"], p["W_v"], p["W_o"], num_heads)
m = gelu(layer_norm(a, p["ln2_g"], p["ln2_b"]) @ p["W1"] + p["b1"]) @ p["W2"] + p["b2"]   # (B, T, d_ff) -> (B, T, d)
return a + m
```

## 8. Full solution

```python
# arrays in, arrays out
import numpy as np


# per-token LayerNorm over the last axis: biased variance, eps inside the square root
def layer_norm(z, g, b, eps=1e-5):
    mu = z.mean(axis=-1, keepdims=True)  # (B, T, 1) so it broadcasts over features
    var = ((z - mu) ** 2).mean(axis=-1, keepdims=True)  # (B, T, 1); mean() divides by d, the biased form
    return g * (z - mu) / np.sqrt(var + eps) + b  # (B, T, d); eps keeps a constant token from dividing by 0


# the tanh approximation of GELU that GPT-2 uses (the erf form differs by up to ~5e-4)
def gelu(z):
    return 0.5 * z * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (z + 0.044715 * z ** 3)))  # elementwise


# causal multi-head self-attention, no biases; the mask is built here from T
def causal_mha(u, W_q, W_k, W_v, W_o, num_heads):
    B, T, d = u.shape  # shapes for the split and merge reshapes
    dh = d // num_heads  # per-head width, also the softmax scale

    # (B, T, d) -> (B, h, T, dh): relabel contiguous column slices as heads, then move heads forward
    def split(a):
        return a.reshape(B, T, num_heads, dh).transpose(0, 2, 1, 3)  # reshape before transpose keeps tokens intact

    q, k, v = split(u @ W_q), split(u @ W_k), split(u @ W_v)  # project once for all heads, then split
    s = q @ k.transpose(0, 1, 3, 2) / np.sqrt(dh)  # (B, h, T, T) scaled scores
    s = np.where(np.tril(np.ones((T, T), dtype=bool)), s, -np.inf)  # (T, T) causal mask broadcasts over B and h
    s = s - s.max(axis=-1, keepdims=True)  # stable softmax: row max becomes 0
    w = np.exp(s)  # future keys are exp(-inf) = 0
    w = w / w.sum(axis=-1, keepdims=True)  # each row is a distribution over keys 0..t
    return (w @ v).transpose(0, 2, 1, 3).reshape(B, T, d) @ W_o  # merge heads in order, then project


# one pre-LN decoder block: each sublayer reads a normalized copy and adds into the raw stream
def transformer_block(x, params, num_heads):
    p = params  # short name for the weight dict
    # attention sublayer: the residual adds to x itself, not to LN1(x)
    a = x + causal_mha(layer_norm(x, p["ln1_g"], p["ln1_b"]), p["W_q"], p["W_k"], p["W_v"], p["W_o"], num_heads)
    # MLP sublayer on a normalized copy of a: (B, T, d) -> (B, T, d_ff) -> (B, T, d)
    m = gelu(layer_norm(a, p["ln2_g"], p["ln2_b"]) @ p["W1"] + p["b1"]) @ p["W2"] + p["b2"]
    return a + m  # second residual add; no final norm inside the block
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `[[[2.4206, -2.0794], [4.4206, -0.0794]]]` | the residual comes from raw `x`; GELU and biased variance |
| Example 2 | row 0 `[0.6954, 1.4948, -1.0831, 0.4069]` | two heads, random LayerNorm parameters, the causal mask |
| single token | `(2, 1, 8)`, first element `0.7075` | `T = 1`, so the mask is irrelevant |
| four heads | `(2, 6, 8)`, first element `0.7233` | head split with `d_head = 2` |
| identity layernorm | first element `2.5437` | `g = 1`, `b = 0`, and `x` shifted by 2 and scaled by 3 |
| large activations | first element `19.5144` | inputs scaled by 10, weights by 1.5 |
| wider | `(2, 10, 16)`, first element `4.2965` | everything at the largest size |

## 10. Complexity

Projections cost $O(BT \cdot 4d^2)$, the MLP $O(BT \cdot 2 d\, d_{ff})$, and attention $O(BT^2 d)$. With the usual $d_{ff} = 4d$, the MLP is two-thirds of the per-token weight FLOPs, and the MLP weights are two-thirds of the block's parameters. Memory is $O(BhT^2)$ for the scores plus $O(BT d_{ff})$ for the MLP hidden layer. At long context the $T^2$ attention term dominates; at short context with large $d$, the matmuls do.

## 11. If you got Wrong Answer

All the classic bugs fail Example 1 except the missing mask, so start there.

- **Example 1 gives `1.4206` instead of `2.4206`.** You added the residual to the normalized input. Use `x + MHA(LN1(x))`.
- **Example 1 gives about `1.0`.** You built post-LN: `LN(x + MHA(x))`.
- **Example 1 gives `1.9759`.** Your LayerNorm uses the unbiased variance (`ddof=1`). With `d = 2` dividing by `d - 1 = 1` doubles the variance and shrinks every normalized value by $1/\sqrt 2$.
- **Example 1 gives `2.42067` instead of `2.42059`.** You used the exact erf GELU. Close, but `rtol = 1e-6` catches it in every case.
- **Example 1 passes, Example 2 gives `0.8312` instead of `0.6954`.** You forgot the causal mask. Example 1 can't detect it because both tokens normalize to the same vector, and "single token" can't because `T = 1`.

## 12. Follow-ups an interviewer might ask

- *What changes in LLaMA-style blocks?* LayerNorm becomes RMSNorm (problem 74), the MLP becomes SwiGLU (problem 75), positions come from RoPE applied to $Q$ and $K$ (problem 67), and attention may share K/V heads (problem 76).
- *Where does the final LayerNorm go?* After the last block, before the unembedding. Without it the logits would see the raw stream, whose scale grows with depth.
- *How would you cache this block for generation?* Store each layer's $K$ and $V$ for past tokens and compute $Q$, $K$, $V$ only for the new token (problem 69).
- *What's the backward pass of LayerNorm?* With $\hat z = (z - \mu)/\sigma$, $\partial L/\partial z = \frac{1}{\sigma}\big(\delta - \operatorname{mean}(\delta) - \hat z\,\operatorname{mean}(\delta \odot \hat z)\big)$ where $\delta = g \odot \partial L/\partial y$. The two mean terms come from $\mu$ and $\sigma$ depending on every input.
