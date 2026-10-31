## Approach

You generated `n` samples and `c` of them pass. pass@k asks: if a user drew `k` of those samples at random, how likely is at least one to pass? The chance that all `k` fail is the number of all-failing subsets over all subsets:

$$
\text{pass@}k = 1 - \frac{\binom{n-c}{k}}{\binom{n}{k}}
$$

Expanding the factorials gives a product that never builds a huge number:

$$
\frac{\binom{n-c}{k}}{\binom{n}{k}} = \prod_{i=n-c+1}^{n}\left(1 - \frac{k}{i}\right)
$$

```python
def _estimate(n, c, k):
    if n < k:
        return None
    if n - c < k:
        return 1.0
    keep = 1.0
    for i in range(n - c + 1, n + 1):
        keep *= 1.0 - k / i
    return 1.0 - keep
```

Score each k by averaging the non-skipped problems, then gate on the configured k.

## Common mistakes

- **The plug-in estimator** `1 - (1 - c/n)^k`. It assumes sampling with replacement and is biased low (for `n=5, c=2, k=2` it gives 0.64 instead of 0.7). The gap grows as k approaches n, exactly where pass@k curves matter.
- **Floating-point binomials.** `float(comb(2000, 1000))` overflows. SciPy's `comb` returns `inf`, and `inf / inf` is `nan`, which then quietly fails a `>=` gate.
- **Pooling samples.** One problem with 2,000 samples outweighs ten problems with 20. The benchmark number is a per-problem average.
- **Counting skipped problems as 0.** A problem that only got 5 samples has no pass@10 estimate. Treating it as a failure makes a release look worse and hides an eval-infra bug.

## Production notes

- Fix `n` per problem and report it next to the score. HumanEval papers usually sample `n=200` to estimate pass@1, pass@10 and pass@100 from the same pool.
- pass@1 at temperature 0 and pass@1 estimated from `n` samples at temperature 0.8 are different metrics. Record the sampling config with the score, and only compare like with like.
- Add a confidence interval (bootstrap over problems) before you gate on small differences between checkpoints. Pair this with the significance test in `ab-test-significance`, and with `prompt-regression-gate` for must-pass cases a regression may never break.
- Sandboxing matters more than the math. Run the unit tests in an isolated container with timeouts, because a generated `rm -rf` or an infinite loop is one of the samples.
