Your support assistant logs `prompt_tokens` for every request. The feature-monitoring job compares today's window against a 30-day reference window and pages the ML on-call when the distribution moves. Write the Population Stability Index (PSI) report it runs per feature.

`psi_report(reference, current, n_bins=10, eps=1e-4)` takes two lists of numbers and returns a dict.

**Bins** come from the reference window only:

1. Compute the interior cut points `np.quantile(reference, [i / n_bins for i in range(1, n_bins)])` (NumPy's default linear interpolation).
2. Remove repeated cut points with `np.unique` (heavily tied features such as retry counts produce duplicates). Call the result `edges`, sorted ascending, with `len(edges) = B - 1` for `B` bins.
3. Bins are right-closed: bin 0 is $(-\infty, e_0]$, bin $j$ is $(e_{j-1}, e_j]$, and the last bin is $(e_{B-2}, \infty)$. A value exactly equal to an edge belongs to the lower bin. If `edges` is empty, there is one bin.

**Proportions and PSI.** For each bin, `r_j = max(ref_count_j / len(reference), eps)` and `c_j = max(cur_count_j / len(current), eps)`. Do not renormalize after flooring.

$$
\text{contrib}_j = (c_j - r_j)\,\ln\frac{c_j}{r_j}, \qquad \text{PSI} = \sum_j \text{contrib}_j
$$

**Severity** uses the industry bands:

| PSI | severity |
|---|---|
| `psi < 0.1` | `"stable"` |
| `0.1 <= psi < 0.25` | `"moderate"` |
| `psi >= 0.25` | `"major"` |

Return

```
{"edges": [...], "ref_pct": [r_0, ...], "cur_pct": [c_0, ...], "contrib": [...],
 "psi": float, "severity": str, "top_bin": int}
```

where all lists are plain Python floats in bin order and `top_bin` is the index of the largest `contrib` (the lowest index on ties). The job reuses `reference` for other features, so do not modify the input lists.

**Constraints**

- `2 <= n_bins <= 20`
- `1 <= len(reference), len(current) <= 5000`
- `0 < eps < 0.01`
- Values are finite numbers (ints or floats).
