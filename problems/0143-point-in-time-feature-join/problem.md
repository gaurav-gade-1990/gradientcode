Your risk team is building the training set for a chargeback model. Labels are chargeback events, and features come from the offline feature store. Last quarter's model looked great offline and fell over in production because the training join used feature values computed **after** each event. Write the point-in-time correct join.

Implement `point_in_time_join(labels, snapshots, feature_specs)`.

- `labels` is a list of `{"label_id", "entity_id", "event_ts", "label"}`.
- `snapshots` is a list of feature rows `{"snapshot_id", "entity_id", "feature", "value", "ts", "version", "created_at"}`. `ts` is the event time the value describes. `version` increases when a value for the same `ts` is recomputed. `created_at` is when the row was written to the store, which can be long after `ts` for a backfill.
- `feature_specs` maps each feature name to `{"lag", "ttl", "default"}`. All times are integer seconds.

For each label and each feature in `feature_specs`:

| step | rule |
|---|---|
| cutoff | `as_of = event_ts - lag`. The lag models pipeline delay: a value isn't usable the instant it is computed. |
| visibility | a snapshot for the same `entity_id` and `feature` is **visible** iff `ts <= as_of` **and** `created_at <= as_of` |
| choice | among the visible snapshots, take the greatest `ts`. On equal `ts`, take the greatest `version`. (`(entity_id, feature, ts, version)` is unique.) |
| freshness | if nothing is visible, the status is `"missing"`. If the chosen row has `as_of - ts > ttl`, the status is `"expired"`. Otherwise it is `"ok"`. Don't fall back to an older row. |
| value | the chosen row's `value` when `"ok"`, else the spec's `default` |
| source | the chosen row's `snapshot_id` when `"ok"`, else `None` |

Return:

```
{
  "rows": [
    {"label_id", "label",
     "features": {feature: value},
     "sources":  {feature: snapshot_id or None},
     "status":   {feature: "ok" | "missing" | "expired"}},
    ...                                   # one per label, in input order
  ],
  "stats": {feature: {"ok": int, "missing": int, "expired": int}}
}
```

**Constraints**

- `1 <= len(labels) <= 2000`, `0 <= len(snapshots) <= 5000`, `1 <= len(feature_specs) <= 10`
- `0 <= lag`, `0 <= ttl`, and `created_at >= ts` for every snapshot
- Snapshots for features not in `feature_specs` may appear. Ignore them.
