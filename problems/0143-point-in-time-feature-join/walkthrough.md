## 1. What the problem is really asking

A training row has to look exactly like what the production model would have seen at the moment it made the prediction. If the training join uses a feature value computed *after* the chargeback (a burst of transactions logged once the fraud was discovered, say), the model learns from the answer. Offline metrics look great, and production falls over. That's label leakage, and the fix is a **point-in-time correct join**, often called an as-of join.

Under the story, this is a **"latest row at or before a cutoff" lookup**, done once per (label, feature). Each lookup has two time filters, a tie-break rule and a freshness check:

- a row is usable only if it describes the past (`ts <= as_of`) **and** was already written to the store (`created_at <= as_of`);
- among usable rows, the newest `ts` wins, then the newest `version`;
- if the winner is too old (`as_of - ts > ttl`), it's expired and you use the default.

The judge compares the full output: every row's `features`, `sources` and `status`, plus the per-feature `stats` counts. `sources` is the most telling field. It names the exact snapshot you joined, so picking the wrong row shows up even when two rows happen to hold the same value.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `labels` | `{label_id, entity_id, event_ts, label}`, one per training example | one output row each, in input order |
| `snapshots` | feature rows with `ts`, `version` and `created_at` | group by `(entity_id, feature)` once |
| `ts` | the event time the value describes | first visibility filter, and the age for the TTL |
| `version` | recompute counter for the same `ts` | tie-break: higher wins |
| `created_at` | when the row landed in the store | second visibility filter; stops backfills leaking |
| `feature_specs` | `{feature: {lag, ttl, default}}` | per-feature cutoff, freshness limit and fallback value |

Three details are easy to miss:

- **The cutoff is per feature.** `as_of = event_ts - lag` uses that feature's `lag`, so one label has several cutoffs. In the "boundaries and ties" case, feature `f` has `lag=50` and `g` has `lag=0`.
- **TTL is measured from `as_of`, not from `event_ts`.** The online store checks staleness at lookup time, and the lookup happens at the cutoff.
- **Snapshots for features not in `feature_specs` are noise.** The edge case includes an `"unused"` feature row (`e7`); it must not appear in the output or the stats.

## 3. Trace Example 2 by hand

The label is `cb_102` on `acct_3` at `event_ts = T` (with `T = 1,000,000`, `D = 86,400`). Both features have `lag=0` and `ttl=2D`, so `as_of = T` for both.

**`credit_limit`.** Three rows share `ts = T - D`:

| snapshot | value | version | created_at | `created_at <= as_of`? |
|---|---|---|---|---|
| t1 | 5000 | 1 | T - D + 60 | yes |
| t2 | 7500 | 2 | T - D + 600 | yes |
| t3 | 2500 | 3 | T + 7D | **no**, a backfill written a week later |

t3 is the newest version, but at prediction time it didn't exist. Among t1 and t2, the higher version wins: **t2, value 7500**. Its age is `as_of - ts = D`, inside the 2-day TTL, so the status is `ok`.

**`zip_risk`.** The only row, t4, has `ts = T - 3D`. It's visible, but its age is `3D > 2D`, so the status is `expired`, the value is the default `0.5` and the source is `None`.

The output:

```python
{"features": {"credit_limit": 7500, "zip_risk": 0.5},
 "sources":  {"credit_limit": "t2", "zip_risk": None},
 "status":   {"credit_limit": "ok", "zip_risk": "expired"}}
```

**The hidden case that teaches the most, "boundaries and ties".** Feature `f` has `lag=50`, `ttl=100`. Entity `a` has e1 (`ts=100`), e2 (`ts=200`, written at 260) and e3 (`ts=300`). Entity `b` has e4 (`ts=500`, v1, written 500) and e5 (`ts=500`, v2, written 900).

| label | entity, event_ts | as_of for `f` | what happens | result |
|---|---|---|---|---|
| l1 | a, 350 | 300 | e3 has `ts == as_of`: visible | 3 from e3, ok |
| l2 | a, 310 | 260 | e3 is after; e2 was written at exactly 260: visible | 2 from e2, ok |
| l3 | a, 250 | 200 | e2 has `ts=200` but was written at 260: skip; e1 is 100 old, exactly the TTL | 1 from e1, ok |
| l4 | b, 600 | 550 | e5 (v2) was written at 900: skip; e4 (v1) is visible | 10 from e4, ok |
| l5 | b, 950 | 900 | e5 is visible now and wins the version tie, but it is 400 old | -1, expired |
| l8 | a, 149 | 99 | every row is after the cutoff | -1, missing |
| l9 | a, 251 | 201 | e2 not written yet; e1 is 101 old, one second over | -1, expired |

Every boundary in the table is inclusive: `ts <= as_of`, `created_at <= as_of`, and an age equal to `ttl` is still fresh. Feature `g` has `ttl=0`, so its only row (`e6`, `ts=0`) is `ok` only for l6, where `as_of = 0`.

## 4. Key idea: two clocks, both before the cutoff

Every snapshot carries two times. `ts` answers "what moment does this value describe?" `created_at` answers "when could anyone read it?" A normal pipeline writes rows a few minutes after `ts`. A backfill recomputes last month's `ts` values today, with today's code. If you filter on `ts` alone, that backfill leaks into last month's labels, and it's the newest version, so it wins the tie-break too. That's exactly what happens to t3 in Example 2: ignore `created_at` and you join 2500 instead of 7500.

Since `created_at >= ts` always holds, the `created_at` filter is the stricter of the two for any single row. But you still need `ts <= as_of`, because ordering by `ts` is what makes "latest" mean the latest describing the past.

## 5. Key idea: sort once, bisect, walk back

Scanning all 5,000 snapshots for each of 2,000 labels and 10 features is 100 million checks. Instead, group snapshots by `(entity_id, feature)` and sort each group by `(ts, version)`. Then for one lookup:

1. `bisect_right` on the `ts` keys finds the last row with `ts <= as_of`.
2. Walk backwards from there and return the first row with `created_at <= as_of`.

Walking back through `(ts, version)` order visits the greatest `ts` first and, within that `ts`, the greatest version first. The first visible row you meet is exactly the one the choice rule wants. You never need to fall back past it for the TTL: anything older is staler still.

## 6. Plan before you code

```
groups = {(entity, feature): rows sorted by (ts, version)}, only for features in specs
stats = zero counts per feature
for each label, in order:
    for each feature, spec:
        as_of = event_ts - lag
        snap = last row with ts <= as_of, walking back past rows with created_at > as_of
        status = missing if no snap, expired if as_of - snap.ts > ttl, else ok
        value, source = (snap.value, snap.id) if ok else (default, None)
        stats[feature][status] += 1
```

| chosen row | status | value | source |
|---|---|---|---|
| none visible | `missing` | `default` | `None` |
| `as_of - ts > ttl` | `expired` | `default` | `None` |
| otherwise | `ok` | row's `value` | row's `snapshot_id` |

## 7. Build it one piece at a time

**Step 1: the index.** Drop unknown features while grouping, then sort each group:

```python
def _index(snapshots, features):
    groups = {}
    for s in snapshots:
        if s["feature"] in features:
            groups.setdefault((s["entity_id"], s["feature"]), []).append(s)
    for rows in groups.values():
        rows.sort(key=lambda s: (s["ts"], s["version"]))
    return groups
```

The `version` in the sort key is what makes the walk-back pick the correction. Sort by `(ts, -version)` and Example 2 returns t1's 5000.

**Step 2: the lookup.** `bisect_right` puts rows with `ts == as_of` on the left side, so they count as visible. `bisect_left` would drop l1's e3 in the edge case:

```python
def _choose(rows, as_of):
    if not rows:
        return None
    keys = [s["ts"] for s in rows]
    i = bisect.bisect_right(keys, as_of) - 1
    while i >= 0:
        if rows[i]["created_at"] <= as_of:
            return rows[i]
        i -= 1
    return None
```

**Step 3: the cutoff and status, per feature.** Compute `as_of` inside the feature loop, from that feature's `lag`, and use it for the TTL too:

```python
as_of = lab["event_ts"] - spec["lag"]
snap = _choose(groups.get((lab["entity_id"], f), []), as_of)
if snap is None:
    status = "missing"
elif as_of - snap["ts"] > spec["ttl"]:
    status = "expired"
else:
    status = "ok"
```

`groups.get(..., [])` handles an entity with no rows at all (Example 3's `acct_new`, and l7's entity `c`).

**Step 4: fill the row and the counts.** Only an `ok` row contributes its value and source:

```python
ok = status == "ok"
row["features"][f] = snap["value"] if ok else spec["default"]
row["sources"][f] = snap["snapshot_id"] if ok else None
row["status"][f] = status
stats[f][status] += 1
```

## 8. Full solution

```python
import bisect  # binary search over each group's sorted ts keys


def _index(snapshots, features):  # build the lookup table once instead of scanning per label
    groups = {}  # (entity_id, feature) -> list of snapshot rows
    for s in snapshots:  # one pass over the store
        if s["feature"] in features:  # rows for features nobody asked for are ignored
            groups.setdefault((s["entity_id"], s["feature"]), []).append(s)  # bucket by entity and feature
    for rows in groups.values():  # order each bucket for the walk-back
        rows.sort(key=lambda s: (s["ts"], s["version"]))  # within a ts, the newest version comes last
    return groups  # ready for per-label lookups


def _choose(rows, as_of):  # the newest row that existed and described the past at as_of
    if not rows:  # this entity has no rows for this feature
        return None  # caller turns this into "missing"
    keys = [s["ts"] for s in rows]  # sorted ts values, the bisect key
    i = bisect.bisect_right(keys, as_of) - 1  # last row with ts <= as_of (ts == as_of counts)
    while i >= 0:  # walk back through (ts, version) order, newest first
        if rows[i]["created_at"] <= as_of:  # it was already in the store at the cutoff
            return rows[i]  # first visible row is the greatest ts, then greatest version
        i -= 1  # written too late (a backfill or a slow write): try the next older row
    return None  # every candidate was written after the cutoff


def point_in_time_join(labels, snapshots, feature_specs):  # build the leakage-free training set
    groups = _index(snapshots, feature_specs)  # group and sort once
    stats = {f: {"ok": 0, "missing": 0, "expired": 0} for f in feature_specs}  # every feature reports all three counts
    out = []  # one output row per label, in input order
    for lab in labels:  # each training example
        # start the row with the label's identity and empty per-feature maps
        row = {"label_id": lab["label_id"], "label": lab["label"], "features": {}, "sources": {}, "status": {}}
        for f, spec in feature_specs.items():  # each feature has its own lag, ttl and default
            as_of = lab["event_ts"] - spec["lag"]  # the moment this feature was really available online
            snap = _choose(groups.get((lab["entity_id"], f), []), as_of)  # unknown entities get an empty list
            if snap is None:  # nothing was visible at the cutoff
                status = "missing"  # use the default
            elif as_of - snap["ts"] > spec["ttl"]:  # age measured at the cutoff, where the online lookup happens
                status = "expired"  # too stale; an older row would be staler, so no fallback
            else:  # visible and fresh enough
                status = "ok"  # the value is usable
            ok = status == "ok"  # only an ok row contributes its value and id
            row["features"][f] = snap["value"] if ok else spec["default"]  # the training value
            row["sources"][f] = snap["snapshot_id"] if ok else None  # lineage: which row was joined
            row["status"][f] = status  # why the value is what it is
            stats[f][status] += 1  # per-feature coverage for the dashboard
        out.append(row)  # keep label order
    return {"rows": out, "stats": stats}  # the training rows plus coverage counts
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | 2 from s1, ok | the lag: s2 at T-10min is after the T-15min cutoff, s3 is in the future |
| Example 2 | 7500 from t2; zip_risk expired, 0.5 | `created_at` blocks the backfill t3; version breaks the tie; TTL expiry |
| Example 3 | 0, missing | an entity with no rows at all |
| boundaries and ties | f stats ok 4, missing 3, expired 2; g stats ok 1, missing 3, expired 5 | every inclusive boundary, write-time skips, the version tie, `ttl=0`, an ignored feature |
| chargeback training set | 120 labels over 668 snapshots | everything at once, shuffled input, about 9% recomputed versions and delayed backfills |
| no snapshots at all | every feature missing | empty `groups` |
| lag pushes cutoff before every row | 0, missing | `as_of = 50` is before every `ts` |

The bulk case's stats show why TTLs matter: `txn_count_24h` (2-hour TTL, a new row every 3 hours) comes out ok 36, missing 37, expired 47.

## 10. Complexity

Let `N` be snapshots, `M` labels, `F` features and `g` the size of the largest group. Building the index is O(N log N). Each lookup is O(log g) for the bisect plus the walk-back, which is short unless many recent rows were written late. This solution rebuilds the `keys` list on every call, which is O(g); caching the keys per group makes the whole join O(N log N + M·F·log g). At 2,000 labels that's instant.

At warehouse scale you don't loop over labels at all. You sort both sides by `(entity, time)` and merge them in one pass. That's `pandas.merge_asof(direction="backward")`, an `ASOF JOIN` in DuckDB or Snowflake, or a window function in Spark. Feast's `get_historical_features` and Tecton do the same thing with a TTL.

## 11. If you got Wrong Answer

- **Example 1 returns 14 from s3, or 9 from s2.** 14 means you joined the latest row with no cutoff at all. 9 means you cut off at `event_ts` and forgot the `lag`.
- **Example 2 returns 2500 from t3.** You ignore `created_at`, so the backfill leaks. In the edge case the same bug gives l4 the value 11 from e5.
- **Example 2 returns 5000 from t1.** Your tie-break keeps the lowest version.
- **"boundaries and ties" marks l2 and l3 expired.** You measure age from `event_ts` instead of `as_of`.
- **"boundaries and ties" differs only on one boundary row.** Check every comparison is inclusive: `ts <= as_of` (use `bisect_right`), `created_at <= as_of`, and expire only when the age is strictly greater than `ttl`. Each of those three slips fails this case.
- **An `"unused"` key appears in `stats`.** Build the counts from `feature_specs`, not from the snapshots.

## 12. Follow-ups an interviewer might ask

- *Why does this matter if the model's offline AUC is great?* Because offline AUC is exactly what leakage inflates. The fix shows up as a *lower* offline score that finally matches production. Problem 150 (train-serve-skew) checks the other half: that serving computes the same values the training set holds.
- *How would you choose the lag?* Measure it. Take the distribution of `created_at - ts` for each feature pipeline and use a high percentile, like p99. A lag set from the median leaks on the slow days.
- *Why not fall back to an older row when the latest one is expired?* It's older, so it's even more expired. Online, the store would have evicted it too, and the model would have seen the default.
- *How do you debug a bad training row?* With the `sources` column. "Row 42 used snapshot s91, written at 03:12" turns a week of investigation into a single query. Store it alongside the training set and the model version in the registry (problem 151, model-registry-stages).
- *What about features with no TTL, like account tier?* Give them a long TTL rather than none, so a dead pipeline shows up as a rising `expired` count instead of silently serving last year's value.
