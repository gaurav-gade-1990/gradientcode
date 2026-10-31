Implement the standard LLM sampling pipeline: **temperature**, then **top-k**, then **top-p** (nucleus) filtering, then sampling with a given uniform number.

`logits` is a float array of shape `(V,)`. Apply these steps in order:

1. **Temperature.** $p = \operatorname{softmax}(\text{logits} / T)$. Use a numerically stable softmax.
2. **Top-k.** If `top_k > 0`, keep the `top_k` most probable tokens, set every other probability to `0`, and renormalize to sum to `1`. `top_k = 0` disables this step. If `top_k >= V`, nothing is removed.
3. **Top-p.** Rank the remaining tokens by probability, then keep the smallest prefix of that ranking whose cumulative probability is `>= top_p`. The token that crosses the threshold is kept, and so is the top token. Zero the rest and renormalize. `top_p = 1.0` keeps every token with nonzero probability.
4. **Sample.** Take the cumulative sum of the final probabilities in **index order** $0, 1, \dots, V-1$. Return the smallest index $i$ whose cumulative sum is strictly greater than `u`.

**Ties.** Whenever tokens are ranked, a higher probability comes first, and equal probabilities are ordered by the lower index first.

Return a tuple `(token, probs)`, where `token` is a Python `int` and `probs` is the final filtered distribution, a float array of shape `(V,)` that sums to `1`.

**Constraints**

- `1 <= V <= 1000`
- `0 < temperature <= 10`. Logits can be as large as `±1e4`.
- `0 <= top_k`, and `0 < top_p <= 1`
- `0 <= u < 1`
- Apart from exact zeros, no cumulative sum lands within `1e-9` of `top_p` or `u`, so floating-point rounding never decides a test
