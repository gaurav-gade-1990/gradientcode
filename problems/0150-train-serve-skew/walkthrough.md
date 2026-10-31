## 1. What the problem is really asking

A model that scores 0.94 AUC offline and 0.71 in production usually isn't a bad model. It's being fed different numbers online. Maybe the serving pipeline logs order value in cents, computes account age in a different timezone, or forgets to send a feature at all. You're writing the check that catches that before deploy, by comparing a training snapshot with logged serving features for the same users.

Under the story, this is **a dedup, a join on a key, and three statistics per feature**:

| statistic | what it catches |
|---|---|
| `mismatch_rate` | the same user gets different values offline and online (a unit bug, an off-by-one) |
| `distance` | the two distributions differ overall, even if you can't join users |
| missing-rate delta | one side stops sending the feature |

Each one can mark a feature as `skewed`, and any skewed feature blocks the deploy. The judge compares every field of every feature, plus the join counts, the ordered offender list and the decision. Most of the difficulty is in definitions: what "missing" means, what "numeric" means, and which rows each statistic uses.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `train_rows` | `{entity_id, features}`, ids unique | one side of the join; all rows feed the distance |
| `serve_rows` | `{entity_id, ts, features}`, an entity may repeat | dedupe to the latest row per entity first |
| `features` | the feature names to check | one report entry each, in this order |
| `abs_tol` | numeric tolerance for a joined pair | `abs(t - s) > abs_tol` is a mismatch |
| `max_mismatch_rate`, `max_distance`, `max_missing_delta` | the three skew thresholds | strict `>` each |
| `top_k` | how many offenders to list | truncate after sorting |

Three details are easy to miss:

- **Missing means an absent key or `None`.** It doesn't mean 0. `row["features"].get(f) is None` covers both.
- **Different statistics use different rows.** `mismatch_rate` uses joined entities only. `distance` and the missing rates use *every* training row and *every* deduplicated serving row.
- **`bool` is a subclass of `int`.** `isinstance(True, int)` is `True`, so a naive check calls a boolean flag numeric.

## 3. Trace Example 1 by hand

Training has u1 to u4. Serving has the same four users, one row each, but in a different order (u3, u1, u2, u4). That's why you join on `entity_id` and never by position: zipping the lists would compare u1's training row with u3's serving row.

| entity | train aov | serve aov | aov match? | train country | serve country | country match? |
|---|---|---|---|---|---|---|
| u1 | 52.10 | 5210.0 | no, logged in cents | US | US | yes |
| u2 | 18.00 | 18.004 | yes, diff 0.004 ≤ 0.01 | CA | `None` | no, one side missing |
| u3 | 75.50 | 75.50 | yes | US | US | yes |
| u4 | 30.00 | 30.00 | yes | GB | GB | yes |

**aov** (numeric): `mismatch_rate = 1/4 = 0.25 > 0.05`. For the distance, the training mean is 43.9 and its population std is 21.964858. The serving mean is 1333.376, pulled up by the cents bug. Distance $= \lvert 1333.376 - 43.9\rvert / 21.964858 = 58.70632$, far above 0.25. Skewed.

**country** (categorical): `mismatch_rate = 0.25`. The distance ignores missing values, so serving has three values. Training frequencies are US 0.5, CA 0.25, GB 0.25; serving frequencies are US 2/3, GB 1/3. Total variation distance:

$$
\tfrac12\left(\lvert 0.5 - 0.667\rvert + \lvert 0.25 - 0\rvert + \lvert 0.25 - 0.333\rvert\right) = \tfrac12(0.1667 + 0.25 + 0.0833) = 0.25
$$

The serving missing rate is `1/4 = 0.25` against 0 in training. Skewed.

Both features are in `top_offenders`, sorted by mismatch rate (tied at 0.25) then by name: `["aov", "country"]`. The decision is `block`.

**Example 2 shows the dedup.** u1 has rows at `ts` 50 and 90; the later one (3) wins and matches training. u2 has two rows at `ts` 90, values 2 then 5. On a tie the later row in the list wins, so 5, which matches. u9 exists only in serving, u3 only in training, so `joined = 2`, `train_only = 1`, `serve_only = 1`. The training values `[3, 5, 4]` have population std $\sqrt{2/3} = 0.8165$, and the deduplicated serving values `[3, 5, 4]` have the same mean, so the distance is 0. Nothing is skewed.

## 4. Key idea: missing is not zero

The most common real skew is a feature the online path forgot to send. If you fill missing values with 0, that bug looks like "a user with zero orders" and blends into the distribution. Keeping missing as its own state gives you two signals:

- in the join, "exactly one side missing" is a mismatch, and "both missing" is a match (both pipelines agree there's nothing);
- across all rows, the missing rates are compared directly.

In "dropped country, float noise", 15% of serving rows lose `country`. The serving missing rate is 0.153846 against 0 in training, and the mismatch rate is 0.181818. Meanwhile `avg_order_value_30d` has tiny float noise (standard deviation 0.002) that stays inside `abs_tol = 0.01`, so it's correctly *not* flagged.

## 5. Key idea: what makes a feature numeric

The kind decides how you compare, so it has to be decided once per feature, from every non-missing value on both sides:

```python
def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)
```

If any value is a string or a bool, the feature is categorical. That matters in "bool flag logged as string": training has `True` and `False`, serving has `"true"` and `"false"`. As categorical values they never compare equal, so the mismatch rate is 1.0 and the distance is 0.888889. That's the real skew: a client branching on `if is_premium:` treats the string `"false"` as true.

A feature with no non-missing values at all (`absent_feature` in "no overlap") is categorical with `distance = None`, since there's nothing to compare.

## 6. Plan before you code

```
latest = per entity, the serving row with the greatest ts (later row wins ties)
joined = [(train, latest[id]) for train rows whose id is in latest]
for each feature:
    t_vals, s_vals = non-missing values over all train rows / all latest rows
    kind = numeric if values exist and all are real numbers, else categorical
    mismatch over joined pairs: both missing ok; one missing bad; numeric tol; categorical !=
    distance: numeric z-shift with population std, or categorical TVD; None if a side is empty
    missing rates over all rows on each side
    skewed = any threshold exceeded, None never triggers
offenders = mismatch > 0, sorted (-rate, name), first top_k
```

| numeric distance case | result |
|---|---|
| either side has no values | `None` |
| $\sigma_t > 0$ | $\lvert\mu_s - \mu_t\rvert / \sigma_t$ |
| $\sigma_t = 0$, means equal | `0.0` |
| $\sigma_t = 0$, means differ | `inf` |

## 7. Build it one piece at a time

**Step 1: dedupe serving.** `>=` (not `>`) makes the later row win a tie, because it replaces the stored row:

```python
latest = {}
for row in serve_rows:
    cur = latest.get(row["entity_id"])
    if cur is None or row["ts"] >= cur["ts"]:
        latest[row["entity_id"]] = row
```

**Step 2: join on the key.** Iterate the training rows and look up the serving row by id:

```python
joined = [(r, latest[r["entity_id"]]) for r in train_rows if r["entity_id"] in latest]
```

**Step 3: the mismatch count.** Handle the missing states before touching the values, since a missing value can't be subtracted:

```python
for t, s in joined:
    mt, ms = _missing(t, f), _missing(s, f)
    if mt and ms:
        continue
    if mt != ms:
        bad += 1
    elif kind == "numeric":
        bad += abs(t["features"][f] - s["features"][f]) > policy["abs_tol"]
    else:
        bad += t["features"][f] != s["features"][f]
```

Adding a bool to an int works in Python (`True` is 1), which keeps the counting short.

**Step 4: the distance.** Population std divides by `len(t_vals)`, not `len - 1`. The sample std would give 50.84116 instead of 58.70632 in Example 1. In "constant training feature", `api_version` is always 2 in training ($\sigma_t = 0$) and one serving row is 3, so the means differ and the distance is `inf`: a feature that never varied in training now varies online.

**Step 5: offenders and decision.** `report[f]["mismatch_rate"]` is truthy only for a positive number, so `None` and `0.0` both drop out of the offender filter.

## 8. Full solution

```python
import math  # sqrt for the population standard deviation


def _missing(row, f):  # absent key or explicit None both mean missing
    return row["features"].get(f) is None  # never treat missing as 0


def _is_num(v):  # a real number; bool subclasses int and must be excluded
    return isinstance(v, (int, float)) and not isinstance(v, bool)  # True/False are flags, not numbers


def _distance(kind, t_vals, s_vals):  # distribution shift between all train and all serve values
    if not t_vals or not s_vals:  # a side with no values can't be compared
        return None  # unknown, and None never marks a feature skewed
    if kind == "numeric":  # mean shift in units of training spread
        mu_t, mu_s = sum(t_vals) / len(t_vals), sum(s_vals) / len(s_vals)  # the two means
        sd = math.sqrt(sum((x - mu_t) ** 2 for x in t_vals) / len(t_vals))  # population std: divide by n
        if sd == 0:  # training never varied
            return 0.0 if mu_s == mu_t else float("inf")  # any shift from a constant is infinitely surprising
        return abs(mu_s - mu_t) / sd  # standardized mean difference
    pt, ps = {}, {}  # value counts for each side
    for v in t_vals:  # count training values
        pt[v] = pt.get(v, 0) + 1  # frequency of this category in training
    for v in s_vals:  # count serving values
        ps[v] = ps.get(v, 0) + 1  # frequency of this category in serving
    keys = set(pt) | set(ps)  # every category seen on either side
    # total variation distance: half the L1 gap between the two frequency distributions
    return 0.5 * sum(abs(pt.get(k, 0) / len(t_vals) - ps.get(k, 0) / len(s_vals)) for k in keys)


def train_serve_skew(train_rows, serve_rows, features, policy):  # the pre-deploy skew report
    latest = {}  # entity -> its most recent serving row
    for row in serve_rows:  # list order matters for ties
        cur = latest.get(row["entity_id"])  # the row kept so far, if any
        if cur is None or row["ts"] >= cur["ts"]:  # newer, or equally new but later in the list
            latest[row["entity_id"]] = row  # keep this one
    serve = list(latest.values())  # deduplicated serving rows
    train_ids = {r["entity_id"] for r in train_rows}  # for the train_only / serve_only counts
    joined = [(r, latest[r["entity_id"]]) for r in train_rows if r["entity_id"] in latest]  # join on the key, never by position

    report = {}  # feature -> its statistics
    for f in features:  # in the requested order
        t_vals = [r["features"][f] for r in train_rows if not _missing(r, f)]  # every non-missing training value
        s_vals = [r["features"][f] for r in serve if not _missing(r, f)]  # every non-missing serving value
        values = t_vals + s_vals  # the kind is decided from both sides together
        kind = "numeric" if values and all(_is_num(v) for v in values) else "categorical"  # any string or bool -> categorical

        bad = 0  # joined pairs that disagree
        for t, s in joined:  # same user, offline vs online
            mt, ms = _missing(t, f), _missing(s, f)  # missing on each side
            if mt and ms:  # both pipelines agree there's no value
                continue  # a match
            if mt != ms:  # one side dropped the feature
                bad += 1  # a mismatch
            elif kind == "numeric":  # both present, compare with tolerance
                bad += abs(t["features"][f] - s["features"][f]) > policy["abs_tol"]  # float noise is fine, unit bugs are not
            else:  # both present, categorical
                bad += t["features"][f] != s["features"][f]  # any difference counts
        mismatch = bad / len(joined) if joined else None  # undefined with no overlap
        dist = _distance(kind, t_vals, s_vals)  # population-level shift
        tm = sum(_missing(r, f) for r in train_rows) / len(train_rows)  # training missing rate, all rows
        sm = sum(_missing(r, f) for r in serve) / len(serve)  # serving missing rate, deduplicated rows
        skewed = ((mismatch is not None and mismatch > policy["max_mismatch_rate"])  # per-user disagreement
                  or (dist is not None and dist > policy["max_distance"])  # distribution shift
                  or abs(sm - tm) > policy["max_missing_delta"])  # one side stopped sending it
        report[f] = {"kind": kind, "mismatch_rate": mismatch, "distance": dist,  # this feature's row in the report
                     "train_missing_rate": tm, "serve_missing_rate": sm, "skewed": bool(skewed)}

    # features with a positive mismatch rate, worst first, ties by name
    offenders = sorted((f for f in features if report[f]["mismatch_rate"]), key=lambda f: (-report[f]["mismatch_rate"], f))
    skewed = sorted(f for f in features if report[f]["skewed"])  # names sorted alphabetically
    return {  # the gate's full report
        "joined": len(joined),  # users on both sides
        "train_only": len(train_ids - set(latest)),  # users with no serving log
        "serve_only": len(set(latest) - train_ids),  # users with no training row
        "features": report,  # per-feature detail
        "top_offenders": offenders[:policy["top_k"]],  # the few worth looking at first
        "skewed": skewed,  # everything that blocks
        "decision": "block" if skewed else "pass",  # any skewed feature blocks the deploy
    }
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | block on `aov` and `country` | join by key; cents bug; a dropped value; tolerance |
| Example 2 | pass; joined 2, train_only 1, serve_only 1 | latest `ts` wins; a tie goes to the later row |
| clean pipeline | pass; every mismatch rate 0 | no false positives; `is_premium` is categorical |
| cents and timezone bugs | block on `account_age_days` (0.3) and `avg_order_value_30d` (0.472727) | a +1 day bug and a ×100 bug |
| dropped country, float noise | block on `country` only | missing is a mismatch; noise inside `abs_tol` is fine |
| bool flag logged as string | block on `is_premium`, mismatch 1.0 | bool vs string is categorical skew |
| constant training feature | block on `api_version`, distance `inf` | the $\sigma_t = 0$ branch |
| no overlap | `x` skewed by missing delta 1.0; mismatch `None` | `joined = 0`; a feature absent everywhere |

## 10. Complexity

Dedup and join are O(T + S) with dicts. Per feature, each statistic is one pass over the rows, so the total is O(F · (T + S)) for `F` features. At 3,000 rows and 30 features that's about 180,000 dictionary reads.

At warehouse scale you'd push this into SQL or Spark: a window function picks the latest serving row, a join on `entity_id` computes mismatches, and grouped aggregates give the means, stds and category counts. TFX Data Validation, Evidently and WhyLabs compute this same kind of report and fail the pipeline on thresholds.

## 11. If you got Wrong Answer

- **Example 1's `aov` mismatch rate is 0.75 and country's is 0.5, and "clean pipeline" flags every feature.** You joined by position. Join on `entity_id`.
- **Example 1's serving missing rate for `country` is 0, and "no overlap" reports `x` with distance `inf`.** You filled missing values with 0.
- **Example 2 shows mismatch 1.0 and blocks.** You kept the first serving row per entity instead of the latest.
- **`is_premium` comes out as `numeric`.** Your number check accepts `bool`.
- **Example 1's `aov` distance is 50.84116 instead of 58.70632.** You used the sample std (`n - 1`). The spec says population std.
- **A crash on `None - float`.** You subtracted values before handling the missing cases.

## 12. Follow-ups an interviewer might ask

- *How do you remove this class of bug instead of detecting it?* Log the features you actually serve, and train on those logs (Google's *Rules of ML*, rule 29). Or use one feature definition for both paths, which is what Feast, Tecton and Vertex AI Feature Store offer.
- *Skew passes, but production AUC is still low. What next?* Check the training join for leakage. Offline features that saw the future look like skew from the other side. Problem 143 (point-in-time-feature-join) builds the leakage-free join.
- *Should this run once at deploy or continuously?* Both. At deploy, run it on a fresh sample of shadow-logged traffic (problem 148, shadow-deployment-diff). Afterwards, run drift monitors such as PSI or a KS test on serving data alone.
- *Why total variation distance for categoricals?* It's bounded in `[0, 1]`, easy to read ("this share of the probability mass moved"), and works with categories that appear on only one side. TFX uses the L-infinity distance, which is the single largest per-category gap.
- *What would you put in the alert?* The top offenders, a few joined example pairs with both values side by side, and the missing-rate delta. "u1: 52.10 offline, 5210.0 online" diagnoses a cents bug in seconds.
