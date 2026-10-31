## Approach

A training row must contain exactly what the online model would have seen at prediction time. That means three cutoffs on every candidate snapshot:

1. **Event time**: `ts <= event_ts - lag`. The value describes the past, minus the pipeline delay.
2. **Write time**: `created_at <= as_of`. The value was actually in the store by then. This is what stops backfills and late corrections from leaking.
3. **Freshness**: `as_of - ts <= ttl`. The online store would have evicted anything older.

Group snapshots by `(entity, feature)` and sort by `(ts, version)`. For each label, bisect to the last row with `ts <= as_of`, then walk backwards past rows that were written too late:

```python
i = bisect.bisect_right([s["ts"] for s in rows], as_of) - 1
while i >= 0:
    if rows[i]["created_at"] <= as_of:
        return rows[i]
    i -= 1
```

Walking backwards in `(ts, version)` order gives the greatest visible `ts`, and within it the greatest visible version. That's exactly the choice rule. Then apply the TTL to the chosen row only.

## Common mistakes

- **Joining the latest snapshot.** This is the classic leakage bug, and the one this problem opens with. Offline metrics look great because the features already encode the outcome (a chargeback triggers a burst of `txn_count` updates).
- **Forgetting the lag.** Online, a value computed at 12:00 is in the store at 12:15. Offline, it looks usable at 12:00. The model learns from a signal it will never have in time.
- **Ignoring `created_at`.** Backfills recompute history with today's code and data. Without the write-time check, a row with `ts` last month and `created_at` today leaks into last month's labels.
- **The wrong version on ties.** Corrections exist for a reason. Keep the newest version that was visible at `as_of`.
- **TTL from the event time.** The online store measures staleness at lookup time, which is the cutoff. Using `event_ts` expires values that were fresh when they were served.

## Production notes

- Feast's `get_historical_features`, Tecton, Databricks Feature Store and Hopsworks all implement this "as-of join" with a TTL, and Feast uses `created_timestamp` to break ties. In Spark or DuckDB it's an `ASOF JOIN`, or a window function over `(entity, feature)` ordered by `ts`.
- At scale you don't loop over labels. You sort both sides by `(entity, time)` and merge, which is what `pandas.merge_asof(direction="backward")` does. The bisect here is the per-group version of that.
- Log the `sources` column. When a model misbehaves, being able to say "row 42 used snapshot s91 written at 03:12" turns a week of debugging into a query.
- Pairs with `train-serve-skew`. A point-in-time join removes leakage from training, and the skew check confirms that serving computes the same values.
