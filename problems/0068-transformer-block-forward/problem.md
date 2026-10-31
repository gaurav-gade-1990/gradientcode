Implement the forward pass of one **pre-LN decoder block**, the layout used by GPT-2 and most modern LLMs:

$$
\begin{aligned}
a &= x + \operatorname{MHA}\big(\operatorname{LN}_1(x)\big) \\
y &= a + \operatorname{MLP}\big(\operatorname{LN}_2(a)\big)
\end{aligned}
$$

`x` has shape `(B, T, d)`. Vectors are rows, and every weight is applied as `input @ W`. `params` is a dict holding:

| key | shape | used in |
|---|---|---|
| `ln1_g`, `ln1_b`, `ln2_g`, `ln2_b` | `(d,)` | LayerNorm scale and shift |
| `W_q`, `W_k`, `W_v`, `W_o` | `(d, d)` | attention (no attention biases) |
| `W1`, `b1` | `(d, d_ff)`, `(d_ff,)` | MLP up-projection |
| `W2`, `b2` | `(d_ff, d)`, `(d,)` | MLP down-projection |

**LayerNorm** normalizes over the last axis with the biased variance and $\epsilon = 10^{-5}$:

$$
\operatorname{LN}(z) = g \odot \frac{z - \mu}{\sqrt{\sigma^2 + \epsilon}} + b, \qquad \mu = \tfrac{1}{d}\textstyle\sum z_j, \quad \sigma^2 = \tfrac{1}{d}\textstyle\sum (z_j - \mu)^2
$$

**MHA** is causal multi-head self-attention. Let $h$ = `num_heads` and $d_{head} = d / h$. Compute $Q = u W_q$, $K = u W_k$, $V = u W_v$. Head $j$ uses columns `j*d_head : (j+1)*d_head`. Each head computes $\operatorname{softmax}(Q_j K_j^\top / \sqrt{d_{head}} + M) V_j$, where $M$ masks every key after the query's position. Concatenate the heads in order and multiply by $W_o$.

**MLP** is $\operatorname{GELU}(u W_1 + b_1) W_2 + b_2$ with the tanh approximation of GELU:

$$
\operatorname{GELU}(z) = \tfrac{1}{2} z \left(1 + \tanh\left(\sqrt{2/\pi}\,\left(z + 0.044715\, z^3\right)\right)\right)
$$

Return `y` with shape `(B, T, d)`. Use a numerically stable softmax.

**Constraints**

- `1 <= B <= 3`, `1 <= T <= 12`, `d <= 16`, `d_ff <= 64`
- `d` is divisible by `num_heads`
