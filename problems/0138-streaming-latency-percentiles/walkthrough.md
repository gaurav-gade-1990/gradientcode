## 1. What the problem is really asking

You want a fleet-wide p99 latency, but you can't ship every sample to one place, and you can't average the replicas' p99s. The fix is to make each replica keep a **histogram** whose buckets are spaced logarithmically, so every bucket is a fixed *percentage* wide. Histograms with the same buckets merge by adding counts, so the collector gets exactly the histogram it would have built from all the samples.

Under the story, the class is a **dict from bucket index to count**, plus a separate counter for exact zeros:

- `record` computes one index with a logarithm and increments a count;
- `merge` adds another histogram's counts into this one;
- `quantile` walks the buckets in order with a running sum until it passes a target rank;
- a memory cap folds the lowest buckets together when there are too many.

The judge's driver (`driver.py`) calls your methods and records everything observable: how many records were accepted or rejected (each `ValueError` counts as a rejection), every quantile value or `"ValueError"`, whether `merge` left the source unchanged (`source_unchanged`), and the `buckets()` table at each snapshot and at the end. So the bucket indices themselves are graded, not just the percentiles.

## 2. Understand the inputs before writing anything

| piece | what it is | how you use it |
|---|---|---|
| `alpha` | relative error bound, e.g. `0.01` | `gamma = (1 + alpha) / (1 - alpha)` |
| `max_buckets` | memory cap on non-empty buckets | fold the lowest while over it |
| `record(value_ms, count=1)` | add `count` copies of one latency | validate, then zero bucket or `ceil(log v / log gamma)` |
| `merge(other)` | add another histogram's counts | same `alpha` required; never alias `other`'s dict |
| `quantile(q)` | `rank = q * (n - 1)` | first bucket whose cumulative count is `> rank` |
| `count()`, `buckets()` | totals and the sorted `[index, count]` table | the zero bucket counts in `count()` but is not listed in `buckets()` |

Details that are easy to miss:

- **Validate before you mutate.** A negative latency or a bad `count` raises `ValueError` and records nothing. "Bad count" includes `0`, `2.5` and `True`. `True` is an `int` in Python, so exclude `bool` explicitly.
- **`0` is not negative.** An exact zero is a cache hit and goes to the zero bucket. Negative values are clock skew and are rejected, not clamped to zero.
- **Indices can be negative.** Values below 1 ms have a negative log. In "cap applied after merge" the data starts at about 0.5 ms, and replica `r1`'s final bucket table starts at index `-12`. A dict handles that without any offset bookkeeping.
- **Folding happens after every `record` and every `merge`**, and it only touches the non-zero buckets.

## 3. Trace Example 1 by hand

`alpha = 0.1`, so `gamma = 1.1 / 0.9 = 1.2222` and `ln gamma = 0.200671`. Record `[100, 120, 250, 900, 1800]`:

| value | ln v / ln γ | index = ceil | representative 2γⁱ/(γ+1) |
|---|---|---|---|
| 100 | 22.949 | 23 | 90.928 |
| 120 | 23.857 | 24 | 111.134 |
| 250 | 27.515 | 28 | 247.998 |
| 900 | 33.898 | 34 | 826.701 |
| 1800 | 37.352 | 38 | 1844.8 |

The snapshot is `[[23, 1], [24, 1], [28, 1], [34, 1], [38, 1]]`. Each representative is within 10% of its value, which is the whole promise of the sketch: 247.998 for 250, 1844.8 for 1800.

**p50:** `n = 5`, `rank = 0.5 · 4 = 2`. The running count is 1 after bucket 23, 2 after bucket 24 (not `> 2`), and 3 after bucket 28. The answer is bucket 28's representative, `247.998`.

**p100:** `rank = 1.0 · 4 = 4`. Only the last bucket takes the count past 4, so the answer is `1844.8`. That's why the rank is `q · (n − 1)` with a strict `>`: p0 is the smallest bucket and p100 the largest.

**Example 2** adds merging. `alpha = 0.05`, `gamma = 1.105263`. `replica-a` records `[0, 180, 210, 240]`: the `0` goes to the zero bucket, the rest to buckets 52, 54 and 55. `replica-b` records `[190, 2600, -15]`: buckets 53 and 79, and `-15` raises, so the trace shows `accepted 2, rejected 1`. Merging both into `fleet` gives 6 observations and buckets `[[52, 1], [53, 1], [54, 1], [55, 1], [79, 1]]`, with both sources unchanged.

| q | rank = q · 5 | where the running count first exceeds it | value |
|---|---|---|---|
| 0.0 | 0 | zero bucket (count 1) | `0.0` |
| 0.5 | 2.5 | bucket 53 (count 3) | `191.164` |
| 0.99 | 4.95 | bucket 55 (count 5) | `233.527` |

**Why averaging p99s is wrong, in this problem's own data.** In "three replicas, one with a tail", the replicas' p99s are 685.5, 699.4 and 6838.0 ms. Their average is 2740.9 ms. The merged histogram's p99 is `2951.94` ms. The quiet replicas pull the average down, while the real fleet tail is set by how many slow requests there are in total.

## 4. Key idea: log buckets give a relative error bound

Bucket `i` covers `(γ^(i−1), γ^i]`. Its representative `2γ^i / (γ + 1)` sits where the relative error to both ends is equal. At the top end the error is `1 − 2/(γ+1) = (γ−1)/(γ+1) = α`, and at the bottom end it's the same. So whatever value you recorded, the reported value is within `α` of it, whether that value is 2 ms or 20 seconds. Linear buckets can't do that: 10 ms buckets are useless at 2 ms and wasteful at 20 s.

The bucket count stays small. At `alpha = 0.01`, covering 1 ms to 600,000 ms takes `ln(600000) / ln(γ) ≈ 665` buckets.

Use `ceil`, exactly as the statement writes it. `floor` puts every value one bucket low. In Example 1 that turns p50 into `202.907` and p100 into `1509.38`, about `2α` optimistic, which is the direction that hides a regression.

## 5. Key idea: merging is adding, and must not share state

The histogram of a union of samples is the sum of their histograms, bucket by bucket. That's the property that makes the sketch useful, and it only works if `merge` **adds**:

```python
for i, c in other._counts.items():
    self._counts[i] = self._counts.get(i, 0) + c
self._zero += other._zero
```

Two traps:

- **Overwriting** (`self._counts[i] = c`, or `dict.update`). In Example 2, `fleet` then has `count 5` instead of 6, because `_zero` was overwritten by replica-b's 0, and p0 becomes `172.958` instead of `0.0`.
- **Aliasing.** "The collector is empty, so just take the replica's dict" makes both objects share one dict. In "collector merges then replica keeps recording", the pod records a second scrape of 150 values and the collector's snapshot shows `count 300` instead of 150. The copy-by-adding loop above never shares the dict.

Merging histograms with different `alpha` would add counts for buckets of different widths, which is meaningless, so it raises.

## 6. Key idea: fold the low end, keep the tail

When the cap is exceeded, merge the **lowest** bucket into the next-lowest. Low percentiles lose accuracy, but p99 is still exact to `α`, and p99 is what the SLO pages on. In "bucket cap folds the low end" (`max_buckets = 40`), after 300 values p1 and p50 both read `5546.65` (everything below was folded together), while p99 is `102882` ms.

Folding the other way is the dangerous mistake: with the high buckets folded down, the same p99 reads `6.68625` ms, and after all 600 values every quantile from p50 up reads `3.6692` ms. The 100-second tail vanishes, and the dashboard stays green through an outage.

## 7. Plan before you code

```
__init__: alpha, max_buckets, gamma, log(gamma), counts = {}, zero = 0
record(v, count):
    count must be an int (not bool) >= 1, else ValueError
    v < 0 -> ValueError
    v == 0 -> zero += count, done
    counts[ceil(log v / log gamma)] += count; collapse()
merge(other):
    alpha must match, else ValueError
    add every count of other into self; zero += other.zero; collapse()
quantile(q):
    q outside [0, 1] -> ValueError; empty -> None
    rank = q * (n - 1); cum = zero; if cum > rank -> 0.0
    for i ascending: cum += counts[i]; if cum > rank -> representative(i)
collapse(): while len(counts) > max_buckets: fold lowest into next-lowest
```

| input to `record` | result |
|---|---|
| `count` is `0`, `2.5` or `True` | `ValueError`, nothing recorded |
| `value_ms < 0` | `ValueError`, nothing recorded |
| `value_ms == 0` | zero bucket |
| `value_ms > 0` | bucket `ceil(ln v / ln γ)`, then fold if over the cap |

## 8. Build it one piece at a time

**Step 1: constructor and the two bucket formulas.** Cache `log(gamma)`: it's used on every record.

```python
def _index(self, v):
    return math.ceil(math.log(v) / self._log_gamma)

def _value(self, i):
    return 2 * self.gamma ** i / (self.gamma + 1)
```

Compute the index exactly as the statement writes it. An algebraically equivalent form such as `math.log(v, gamma)` passes the current tests, but on a value that sits right at a bucket edge it can round to the neighbouring bucket, and the bucket table is graded.

**Step 2: `record`, validating first.** Check `count` and the sign of `value_ms` before touching any state, so a rejected call leaves the histogram exactly as it was:

```python
if isinstance(count, bool) or not isinstance(count, int) or count < 1:
    raise ValueError("count must be a positive int")
if value_ms < 0:
    raise ValueError("negative latency")
```

In "validation errors", `count=0`, `count=2.5` and `count=True` are each rejected, and the following `count=25` is the only one recorded, giving `[[301, 25]]`.

**Step 3: `quantile`.** Start the running count at the zero bucket, then walk the indices in sorted order:

```python
rank = q * (n - 1)
cum = self._zero
if cum > rank:
    return 0.0
for i in sorted(self._counts):
    cum += self._counts[i]
    if cum > rank:
        return self._value(i)
```

"weighted records" shows the strict `>` at work: with 970 + 25 + 5 = 1000 observations, p97 has rank `969.03`. The first bucket's count of 970 exceeds it, so p97 is `808.389`. p97.5 (rank `974.025`) moves to the 4120 ms bucket, `4125.97`.

**Step 4: the cap.** Sort the indices, take the two smallest, move the count:

```python
while len(self._counts) > self.max_buckets:
    lo, nxt = sorted(self._counts)[:2]
    self._counts[nxt] += self._counts.pop(lo)
```

Call it at the end of both `record` and `merge`. A merge can push the bucket count over the cap just as easily as a record. "cap applied after merge" fails if you only fold in `record`.

## 9. Full solution

```python
import math  # log and ceil for the bucket index


# DDSketch-style log-bucket histogram with a bounded relative error.
class LatencyHistogram:
    # Set up the bucket geometry and empty counters.
    def __init__(self, alpha=0.01, max_buckets=2048):
        self.alpha = alpha  # relative error bound; merge compares it
        self.max_buckets = max_buckets  # memory cap on non-empty buckets
        self.gamma = (1 + alpha) / (1 - alpha)  # ratio between consecutive bucket edges
        self._log_gamma = math.log(self.gamma)  # cached, used on every record
        self._counts = {}  # bucket index -> count; sparse, and indices can be negative
        self._zero = 0  # exact-zero observations (cache hits) live outside the log buckets

    # Which bucket a positive value belongs to.
    def _index(self, v):
        return math.ceil(math.log(v) / self._log_gamma)  # bucket i covers (gamma^(i-1), gamma^i]

    # The value reported for bucket i.
    def _value(self, i):
        return 2 * self.gamma ** i / (self.gamma + 1)  # equal relative error to both bucket edges

    # Enforce the memory cap by folding the low end upward.
    def _collapse(self):
        while len(self._counts) > self.max_buckets:  # too many non-empty buckets
            lo, nxt = sorted(self._counts)[:2]  # the two lowest indices
            self._counts[nxt] += self._counts.pop(lo)  # lose low-end detail, keep the tail exact

    # Add `count` observations of one latency.
    def record(self, value_ms, count=1):
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:  # True, 2.5 and 0 are all bad
            raise ValueError("count must be a positive int")  # reject before changing anything
        if value_ms < 0:  # clock skew, not a cache hit
            raise ValueError("negative latency")  # reject rather than clamp to zero
        if value_ms == 0:  # an exact zero has no logarithm
            self._zero += count  # count it in the zero bucket
            return  # zeros never take part in folding
        i = self._index(value_ms)  # log-spaced bucket for this value
        self._counts[i] = self._counts.get(i, 0) + count  # add, creating the bucket if new
        self._collapse()  # a new bucket may push us over the cap

    # Add another histogram's counts into this one.
    def merge(self, other):
        if other.alpha != self.alpha:  # different bucket widths can't be added
            raise ValueError("cannot merge histograms with different alpha")  # refuse the merge
        for i, c in other._counts.items():  # read other's buckets without sharing its dict
            self._counts[i] = self._counts.get(i, 0) + c  # counts add; never overwrite
        self._zero += other._zero  # zeros add too
        self._collapse()  # the union may exceed the cap

    # The representative value at quantile q.
    def quantile(self, q):
        if not 0 <= q <= 1:  # outside the valid range
            raise ValueError("q must be in [0, 1]")  # bad query
        n = self.count()  # total observations including zeros
        if n == 0:  # nothing recorded yet
            return None  # no quantile exists
        rank = q * (n - 1)  # p0 is the minimum, p100 the maximum
        cum = self._zero  # zeros are the smallest values, so they come first
        if cum > rank:  # the target falls among the zeros
            return 0.0  # the zero bucket's representative
        for i in sorted(self._counts):  # walk buckets from smallest to largest value
            cum += self._counts[i]  # running count up to and including bucket i
            if cum > rank:  # first bucket that passes the target rank
                return self._value(i)  # report its representative
        return self._value(max(self._counts))  # floating-point safety net: the top bucket

    # Total number of observations.
    def count(self):
        return self._zero + sum(self._counts.values())  # zeros plus every bucket

    # The non-empty buckets, sorted, without the zero bucket.
    def buckets(self):
        return [[i, self._counts[i]] for i in sorted(self._counts)]  # [index, count] pairs
```

## 10. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | buckets 23, 24, 28, 34, 38; p50 `247.998`, p100 `1844.8` | `ceil` index, representative, `q · (n − 1)` rank |
| Example 2 | `-15` rejected; fleet count 6; p0 `0.0`, p50 `191.164`, p99 `233.527` | zero bucket, merge adds, sources unchanged |
| three replicas, one with a tail | fleet p99 `2951.94`; us-east-1c alone `6837.96` | merging three replicas, a tail from one of them |
| bucket cap folds the low end | after 300 values p1 = p50 = `5546.65`, p99 `102882` | fold the lowest bucket, keep the tail |
| cap applied after merge | agg holds 25 buckets after each merge, p99 `94971.1` | `_collapse()` in `merge`, not only in `record` |
| cache hits and clock skew | `accepted 101, rejected 2`; p0 through p30 are `0.0`, p50 `33.4505` | negatives rejected; 31 zeros counted separately |
| collector merges then replica keeps recording | collector stays at `count 150` after the pod records 150 more | merge copies counts, never aliases the dict |
| validation errors | counts `0`, `2.5`, `True` rejected; alpha mismatch is `ValueError`; q `-0.01` and `1.01` raise; empty quantile is `None` | every validation rule |
| weighted records | p97 `808.389`, p97.5 `4125.97`, p99.6 `29883.8` | `count` weights, and the strict `>` at bucket boundaries |
| single bucket cap | snapshot `[[311, 3]]`; p0 and p30 `0.0`, p100 `497.779` | cap of 1 folds everything into the top bucket; zeros stay out of folding |

## 11. Complexity

`record` is O(1) for the log and the dict update. `_collapse` sorts the indices, O(B log B) for `B` buckets, but only does work when the cap is exceeded, and a single record adds at most one bucket. `merge` is O(B_other) plus a collapse. `quantile` sorts the indices and walks them, O(B log B). Memory is O(B) with `B ≤ max_buckets`, regardless of how many observations you record. In practice `B` is a few hundred at `alpha = 0.01`.

That fixed size is the point at scale. A replica ships a few hundred integers per scrape interval instead of every sample, and the backend can re-aggregate any set of pods over any time range by adding counts. A production version would keep the indices sorted (or in a contiguous array with an offset) to avoid sorting on every query.

## 12. If you got Wrong Answer

- **Every bucket index in the snapshot is one lower than expected, and p50 in Example 1 is `202.907`.** You used `math.floor`. Use `ceil`.
- **Example 2's fleet has `count 5` and p0 is `172.958`.** Your merge overwrote counts instead of adding them. The zero bucket was overwritten by replica-b's 0.
- **"collector merges then replica keeps recording" shows the collector at `count 300`.** You assigned `self._counts = other._counts` when the collector was empty, so the two objects share one dict.
- **"cache hits and clock skew" shows `accepted 103, rejected 0`.** You clamped negatives to zero. They must raise.
- **The capped cases report a tiny p99, like `6.68625` ms.** You folded the highest buckets instead of the lowest.
- **"cap applied after merge" has more than 25 buckets in a snapshot.** You only call `_collapse` from `record`.
- **"validation errors" accepts `count=True`.** `bool` is an `int` subclass. Reject it explicitly.
- **"weighted records" gives p97 = `4125.97`.** You used `rank = q * n`. Use `q * (n - 1)`.

## 13. Follow-ups an interviewer might ask

- *Why not t-digest?* t-digest is very accurate at the extremes, but merging two digests is not exact: the result depends on merge order. Log-bucket sketches merge exactly, which matters when a backend re-aggregates thousands of pods.
- *How does this relate to OpenTelemetry and Prometheus?* OpenTelemetry's exponential histogram uses the same layout with `γ = 2^(2^−scale)`, and Prometheus native histograms do too. Changing `scale` by one doubles or halves the bucket width, so histograms of different resolution can still be merged by down-scaling one of them.
- *How would you turn these counts into SLO alerts?* Count the requests above the latency target (the buckets above it) as "bad events" per window, and alert on the burn rate of the error budget. Problem 139 (slo-burn-rate-alerts) builds that.
- *Where else does a merged p99 show up?* A load balancer comparing replicas (problem 132, load-balancer-p2c) and an anomaly detector on latency (problem 140, ewma-anomaly-detection) both consume per-replica latency summaries, and both should use mergeable ones.
- *What would you change for LLM traffic?* Latency is multi-modal: cache hits, short completions and long generations. Keep separate histograms for time to first token and total latency, per model, so a slow model doesn't hide inside a fleet-wide p99.
