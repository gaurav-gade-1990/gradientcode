Implement causal multi-head self-attention with a **KV cache**, the way an LLM decodes: the keys and values of past tokens are stored, and each new token only computes its own projections.

Write a class `CachedSelfAttention`:

- `__init__(self, W_q, W_k, W_v, W_o, num_heads)` stores the weights and starts with an empty cache. Each weight has shape `(d, d)` and is applied as `x @ W`.
- `prefill(self, x)` takes `x` of shape `(n, d)`, the next `n` tokens of the sequence. It appends their keys and values to the cache and returns the attention output for those `n` tokens, shape `(n, d)`.
- `step(self, x_t)` takes one token of shape `(d,)`, appends it, and returns its output of shape `(d,)`.

The judge may call `prefill` and `step` in any order and any number of times, and it may use several instances at once. Each instance holds its own sequence.

**What "correct" means.** Let $x_0, x_1, \dots$ be every token an instance has received, in order. The output for token $t$ must equal the output of ordinary causal multi-head attention over the full sequence at row $t$:

$$
o_t = \operatorname{concat}_{j}\left(\sum_{s \le t} \operatorname{softmax}_s\left(\frac{q_{t,j} \cdot k_{s,j}}{\sqrt{d_{head}}}\right) v_{s,j}\right) W_o
$$

where $q_t = x_t W_q$, $k_s = x_s W_k$ and $v_s = x_s W_v$. Head $j$ uses the contiguous columns `j*d_head : (j+1)*d_head`, and $d_{head} = d / \text{num\_heads}$. Token $t$ attends to itself and every earlier token, including tokens from earlier calls. Within one `prefill` call, a token must not see the tokens after it.

Don't recompute projections of cached tokens. Use a numerically stable softmax.

**Constraints**

- `d <= 16`, `d` divisible by `num_heads`
- At most 40 tokens per instance, and at most 3 instances per test
- `prefill` is called with `n >= 1`
