## Approach

The two-sample KS statistic is the largest vertical gap between two empirical CDFs. Both CDFs are step functions that only jump at sample values, so the maximum is reached at one of the values in **either** sample. Checking the union of values is enough, and it is required.

```python
rs, cs = sorted(ref), sorted(cur)
best, at = -1, None
for x in sorted(set(rs) | set(cs)):
    a = bisect.bisect_right(rs, x)            # reference values <= x
    b = bisect.bisect_right(cs, x)            # current values <= x
    num = abs(a * m - b * n)                  # integer, so ties are exact
    if num > best:
        best, at = num, x
D = best / (n * m)
```

Working with the integer numerator $|a m - b n|$ instead of `a/n - b/m` makes the location `at` well defined. Two floating-point gaps that are mathematically equal can differ in the last bit.

The p-value comes from the Kolmogorov distribution $Q(\lambda) = 2\sum_{j\ge1}(-1)^{j-1}e^{-2j^2\lambda^2}$ with the Stephens small-sample correction to $\lambda$. The series converges fast for $\lambda \ge 0.27$, and below that $Q$ is 1 to many digits, so the cutoff avoids summing a slowly converging alternating series.

Last, Bonferroni: with $k$ tests at level $\alpha$, the chance of at least one false alarm is up to $k\alpha$. Testing each at $\alpha / k$ keeps the family-wise error at $\alpha$. Here $k$ is the number of features that actually ran the test.

## Common mistakes

- **No correction.** Twenty features at 0.05 each give about a 64% chance of a false page every run. The on-call learns to ignore the detector.
- **Dividing by every column.** Dropped columns and sparse features never ran a test. Counting them makes the threshold stricter than it needs to be and hides real drift.
- **Treating nulls as zero.** An upstream outage that nulls a field looks like a huge spike at 0. That is a data-quality incident (problem 137), not distribution drift, and it should be reported separately.
- **Evaluating only at reference points.** A shift that sits between reference values is under-measured, because the gap peaks at a current value.
- **Strict vs non-strict CDF.** $F(x)$ counts values `<= x` (`bisect_right`). Mixing conventions across the two samples gives wrong gaps on tied integer features.

## Production notes

- Evidently, Alibi Detect and NannyML all run per-feature KS with a Bonferroni or FDR correction. Benjamini–Hochberg is the usual upgrade when you have hundreds of features and can tolerate a controlled fraction of false alarms.
- KS on large windows is *too* sensitive: with 100k rows a tiny, harmless shift gets $p \approx 0$. Mature teams alert on an effect size (D itself, or PSI, problem 135) **and** significance, not on p alone.
- KS assumes continuous data. On heavily tied integer features the asymptotic p-value is conservative; use a chi-squared test or PSI for low-cardinality features.
- Keep `missing` and `insufficient_data` as first-class statuses on the dashboard. A dropped column is often the real incident, and silently skipping it hides a broken pipeline.
- Pair with `embedding-drift` (141) for the unstructured inputs of an LLM app and `train-serve-skew` (150) to tell a pipeline bug from real-world drift.
