## 1. What the problem is really asking

For each benchmark problem you sampled `n` completions and `c` of them passed the unit tests. pass@k answers a user-facing question: *if someone generates `k` completions, what's the chance at least one works?* You estimate that from the `n` you already have, then average across problems and gate the release on one k.

Under the story, this is **a counting formula plus careful aggregation**. The counting part is "draw `k` of your `n` samples without replacement; what's the chance all of them are failures?" The aggregation part is three rules that are easy to get subtly wrong: average per problem (not pooled), leave out problems that can't be estimated (not counted as 0), and return `None` when nothing is left.

The judge compares the whole dict: `scores` per k, `per_problem` values, the sorted `skipped` lists and the `ship` boolean, with `rtol=1e-9`. So the estimator must be the exact unbiased one, not an approximation.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `samples` | `{problem_id: [1, 0, 0, 1, ...]}` | per problem, `n = len(list)` and `c = sum(list)` |
| `ks` | distinct positive ints, in any order | one `"pass@%d"` key per k, in the order given |
| `gate` | `{"k": int, "min_score": float}` | ship iff `scores["pass@k"]` is not `None` and `>= min_score` |

Three details are easy to miss:

- **`ks` is not sorted.** The "k equals n" case passes `[3, 1, 2]`. Dicts keep insertion order, so iterate `ks` as given and the keys come out in that order.
- **`n` differs per problem.** In "mixed sample counts", problems have 200, 40, 5 and 8 samples. A problem with 5 samples has a pass@5 but no pass@10.
- **`n` goes up to 3000.** `math.comb(2000, 1000)` has 601 digits. Converting it to a float raises `OverflowError`.

## 3. The math

You have `n` samples, `c` passing and `n - c` failing. Draw `k` of them without replacement. Every subset of size `k` is equally likely, so:

$$
P(\text{all } k \text{ fail}) = \frac{\#\text{subsets of size } k \text{ from the } n-c \text{ failures}}{\#\text{subsets of size } k \text{ from all } n} = \frac{\binom{n-c}{k}}{\binom{n}{k}}
$$

and pass@k is one minus that. If `n - c < k`, there aren't enough failures to fill a draw, so every draw contains a pass and pass@k is exactly `1.0`.

To avoid huge numbers, expand the factorials:

$$
\frac{\binom{n-c}{k}}{\binom{n}{k}} = \frac{(n-c)!}{k!\,(n-c-k)!}\cdot\frac{k!\,(n-k)!}{n!} = \frac{(n-k)!/(n-c-k)!}{n!/(n-c)!}
$$

Both fractions are products of exactly `c` consecutive integers. The top is $\prod_{i=n-c+1}^{n}(i-k)$ and the bottom is $\prod_{i=n-c+1}^{n} i$. Pair them up term by term:

$$
\frac{\binom{n-c}{k}}{\binom{n}{k}} = \prod_{i=n-c+1}^{n}\frac{i-k}{i} = \prod_{i=n-c+1}^{n}\left(1-\frac{k}{i}\right)
$$

Every factor is between 0 and 1, so the running product never overflows. When `c = 0` the product is empty, equal to 1, and pass@k is 0, which is right: nothing ever passes.

Why not just use $1 - (1 - c/n)^k$? That's the probability for drawing **with** replacement. It's biased low. For `n=5, c=2, k=2` it gives `0.64`; the unbiased value is `0.7`.

## 4. Trace Example 1 by hand

`two-sum` is `[1, 0, 0, 1, 0]`, so `n=5, c=2`. `lru-cache` is all zeros, so `n=5, c=0`. `ks = [1, 2]`.

| problem | k | `n - c < k`? | product over i = 4, 5 | pass@k |
|---|---|---|---|---|
| two-sum | 1 | 3 < 1, no | (1 - 1/4)(1 - 1/5) = 0.75 · 0.8 = 0.6 | 0.4 |
| two-sum | 2 | 3 < 2, no | (1 - 2/4)(1 - 2/5) = 0.5 · 0.6 = 0.3 | 0.7 |
| lru-cache | 1 | no | empty product = 1 | 0 |
| lru-cache | 2 | no | empty product = 1 | 0 |

Scores: `pass@1 = (0.4 + 0) / 2 = 0.2` and `pass@2 = (0.7 + 0) / 2 = 0.35`. The gate is `k=1, min_score=0.15`, and `0.2 >= 0.15`, so `ship` is `True`. Notice pass@1 is just `c/n`: the product has one factor for k=1 that telescopes to `(n-c)/n`.

**Example 2 shows the skip rule.** `rate-limiter` has `n=3`, so for `k=4` it's `None` and goes into `skipped["pass@4"]`. `parse-csv` has `n=4, c=3`, and `n - c = 1 < 4`, so its pass@4 is `1.0`. The pass@4 score averages only the one remaining problem: `1.0`, which clears `0.9`.

## 5. Key idea: macro average, and skip rather than zero

The benchmark number is "the average problem's pass@k". Two tempting alternatives answer different questions:

- **Pooling.** Add every problem's samples into one big `n` and `c`. In "macro vs pooled", `repo/fix-imports` has 200 samples (180 passing) and the other two have 10 each (1 and 0 passing). Pooled pass@1 is `181/220 = 0.822727`, which would ship against `0.6`. The macro average is `(0.9 + 0.1 + 0) / 3 = 0.333333`, which doesn't. One easy problem with lots of samples shouldn't hide two failures.
- **Counting a skip as 0.** A problem with fewer than k samples has no estimate. In "all pass", `x` has 50 passing samples and `y` has 7. Treat `y`'s missing pass@10 as 0 and the score is `0.5`, so a model that passed every single test doesn't ship. Leave it out and the score is `1.0`.

## 6. Plan before you code

```
estimate(n, c, k):
    n < k      -> None
    n - c < k  -> 1.0
    else       -> 1 - prod(1 - k/i for i in n-c+1 .. n)

for each k in ks (given order):
    for each problem: value = estimate(...); store in per_problem
        None -> add to skipped list, else -> add to vals
    sort skipped list; score = mean(vals) or None
ship = gate score is not None and >= min_score
```

| per-problem situation | value | in the mean? | in `skipped`? |
|---|---|---|---|
| `n < k` | `None` | no | yes |
| `n - c < k` | `1.0` | yes | no |
| otherwise | the product formula | yes | no |

## 7. Build it one piece at a time

**Step 1: the estimator.** The order of the two early returns matters. Check `n < k` first; otherwise a problem with 3 samples and `c=3` would return `1.0` for `k=4` instead of being skipped.

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

The loop has `c` iterations, at most 3000. The `n - c < k` check also guarantees every factor is positive: `i >= n - c + 1 > k`.

**Step 2: per-problem values for every k.** Create every problem's inner dict up front so each k can fill its own key:

```python
per_problem = {pid: {} for pid in samples}
for k in ks:
    key = "pass@%d" % k
    vals = []
    skipped[key] = []
    for pid, outcomes in samples.items():
        v = _estimate(len(outcomes), sum(outcomes), k)
        per_problem[pid][key] = v
```

**Step 3: split skipped from scored, then average.** `skipped` must be sorted; `samples` iterates in insertion order, which may not be sorted:

```python
        if v is None:
            skipped[key].append(pid)
        else:
            vals.append(v)
    skipped[key].sort()
    scores[key] = sum(vals) / len(vals) if vals else None
```

**Step 4: the gate.** Check `None` before comparing; in Python 3, `None >= 0.5` raises a `TypeError`:

```python
score = scores["pass@%d" % gate["k"]]
ship = score is not None and score >= gate["min_score"]
```

## 8. Full solution

```python
def _estimate(n, c, k):  # unbiased pass@k for one problem with n samples, c passing
    if n < k:  # can't draw k distinct samples from fewer than k
        return None  # no estimate: the caller marks this problem skipped
    if n - c < k:  # too few failures to fill a draw of k
        return 1.0  # so every draw contains a pass
    keep = 1.0  # running value of C(n-c, k) / C(n, k), the all-fail probability
    for i in range(n - c + 1, n + 1):  # c factors, one per passing sample
        keep *= 1.0 - k / i  # each factor is in (0, 1), so this never overflows
    return 1.0 - keep  # chance at least one of the k passes


def pass_at_k(samples, ks, gate):  # benchmark scores per k plus the release decision
    scores, skipped = {}, {}  # headline score and skipped ids, both keyed "pass@k"
    per_problem = {pid: {} for pid in samples}  # each problem's values, filled one k at a time
    for k in ks:  # in the given order, so output keys follow ks
        key = "pass@%d" % k  # the key format the judge expects
        vals = []  # estimates that take part in the mean
        skipped[key] = []  # problems with fewer than k samples
        for pid, outcomes in samples.items():  # every problem gets a value for every k
            v = _estimate(len(outcomes), sum(outcomes), k)  # n is the list length, c the number of 1s
            per_problem[pid][key] = v  # None is reported, not hidden
            if v is None:  # no estimate for this k
                skipped[key].append(pid)  # list it so eval-infra gaps are visible
            else:  # a real estimate
                vals.append(v)  # macro average: every problem weighs the same
        skipped[key].sort()  # the spec wants the skipped ids sorted
        scores[key] = sum(vals) / len(vals) if vals else None  # skips are left out, not counted as 0
    score = scores["pass@%d" % gate["k"]]  # the one k the release gate looks at
    return {  # everything the judge compares
        "scores": scores,  # headline number per k
        "per_problem": per_problem,  # drill-down per problem
        "skipped": skipped,  # problems that couldn't be estimated
        "ship": score is not None and score >= gate["min_score"],  # no estimate means no ship
    }
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | pass@1 0.2, pass@2 0.35, ship | the product formula; the unbiased 0.7, not 0.64 |
| Example 2 | pass@4 1.0 from one problem, ship | the `n < k` skip and the `n - c < k` shortcut |
| Example 3 | pass@8 `None`, no ship | every problem skipped: score `None`, gate fails |
| large n, k sweep | pass@10 0.45086, ship at 0.4 | `n = 2000` and k up to 1000: no float binomials |
| mixed sample counts | pass@10 0.47361, skips `mbpp/3` and `mbpp/5` | per-k skip lists differ; the mean excludes them |
| macro vs pooled | pass@1 0.333333, no ship | macro average; pooling would give 0.822727 and ship |
| k equals n | pass@3 0.666667, ship at 0.66 | `n == k` is estimated, not skipped; `ks` order kept |
| single sample per problem | pass@1 0.333333, pass@2 `None` | `n = 1`; every problem skipped at k=2 |
| all pass | pass@10 1.0, ship at exactly 1.0 | the skipped `y` stays out; `>=` at the boundary |

## 10. Complexity

For each k and each problem, the work is O(n) to sum the outcomes plus O(c) for the product. With `P` problems and `K` values of k, that's O(K · Σn), a few hundred thousand multiplications at the largest sizes here. Memory is O(P·K) for the output.

In production the expensive part is generating and sandboxing the `n` completions, not this arithmetic. That's why you sample once (HumanEval papers typically use `n=200`) and estimate pass@1, pass@10 and pass@100 all from the same pool. The unbiased estimator is what makes that reuse valid.

## 11. If you got Wrong Answer

- **Example 1's pass@2 for two-sum is 0.64.** You used `1 - (1 - c/n)**k`, the with-replacement formula.
- **Runtime Error, `OverflowError: int too large to convert to float`, on "large n, k sweep".** You computed `float(math.comb(n - c, k)) / float(math.comb(n, k))`. Use the product.
- **"macro vs pooled" gives 0.822727 and ships.** You pooled all samples into one `n` and `c`.
- **"all pass" gives 0.5 and doesn't ship, or "mixed sample counts" gives pass@10 0.31574.** You counted skipped problems as 0.
- **Example 3 crashes with `ZeroDivisionError` or `TypeError`.** You divided by an empty list, or compared `None >= min_score`.
- **A problem with `n == k` is skipped.** The skip condition is `n < k`, strictly.

## 12. Follow-ups an interviewer might ask

- *pass@1 at temperature 0 versus pass@1 from 200 samples at temperature 0.8: same number?* No. They're different metrics. Record the sampling config with every score and compare only like with like.
- *Checkpoint B beats A by 0.01 on pass@1. Ship?* Not without a confidence interval. Bootstrap over problems, or run a paired test like problem 146 (ab-test-significance). Fifty problems give a wide interval.
- *What if a release must never break specific problems?* Average scores can hide a regression on a must-pass case. Gate on those separately, as problem 149 (prompt-regression-gate) does.
- *Could you compute the ratio exactly instead?* Yes. Python integers are unbounded, and `math.comb(n - c, k) / math.comb(n, k)` with int true division is correctly rounded, but it builds 600-digit numbers. The product is simpler and just as accurate here.
- *What does the eval harness need besides the math?* A sandbox. Generated code runs with timeouts in an isolated container, because one of the samples will be an infinite loop or a destructive shell command.
