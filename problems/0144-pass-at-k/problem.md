Your team ships a code-generation model. Before each release the eval job samples `n` completions per benchmark problem, runs the unit tests, and the release gate decides from **pass@k** whether the new checkpoint ships.

Implement `pass_at_k(samples, ks, gate)`.

- `samples` maps a problem id (a string) to a list of test outcomes, one per sampled completion: `1` passed every unit test, `0` did not. Let `n` be the list length and `c` its sum.
- `ks` is a list of distinct positive integers.
- `gate` is `{"k": int, "min_score": float}`. `gate["k"]` is always in `ks`.

For one problem, use the unbiased estimator from Chen et al. (2021):

$$
\text{pass@}k = 1 - \frac{\binom{n-c}{k}}{\binom{n}{k}} = 1 - \prod_{i=n-c+1}^{n}\left(1 - \frac{k}{i}\right)
$$

with these rules:

| case | pass@k for the problem |
|---|---|
| `n < k` | `None`: not enough samples. The problem is **skipped** for this k. |
| `n - c < k` | `1.0`: every draw of k samples contains a pass. |
| otherwise | the formula above |

The score for a k is the **mean over the non-skipped problems** (a macro average, every problem weighted equally). If every problem is skipped, the score is `None`.

The checkpoint ships when the score for `gate["k"]` is not `None` and is `>= gate["min_score"]`.

Return a dict:

```
{
  "scores":      {"pass@1": float or None, ...},          # one key per k, formatted "pass@%d"
  "per_problem": {problem_id: {"pass@1": float or None, ...}, ...},
  "skipped":     {"pass@1": [problem ids, sorted], ...},   # problems with n < k
  "ship":        bool
}
```

**Constraints**

- `1 <= len(samples) <= 50`, and every list has `1 <= n <= 3000` entries
- `1 <= k <= 3000`
- Never compute `C(n, k)` as a float: it overflows past `1e308` once `n` is in the low thousands.
