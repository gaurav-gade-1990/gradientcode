## Approach

Skew shows up in two ways, and you need both checks.

- **Row-level mismatch** answers "for the same user, did online and offline compute the same number?" It catches unit bugs (cents vs dollars), off-by-one windows and timezone shifts that leave the distribution almost unchanged.
- **Distribution distance** answers "do the two populations look alike?" It catches a serving pipeline that is consistently wrong for users who never appear in training.

The bookkeeping order matters:

```python
latest = {}
for row in serve_rows:                       # dedupe: newest ts, later row on ties
    cur = latest.get(row["entity_id"])
    if cur is None or row["ts"] >= cur["ts"]:
        latest[row["entity_id"]] = row
joined = [(r, latest[r["entity_id"]]) for r in train_rows if r["entity_id"] in latest]
```

Then, per feature, settle the type before comparing (`bool` is not numeric), treat missing as its own state, and compute the standardized mean difference or the total variation distance over all rows.

## Common mistakes

- **Joining by position.** Logs are never in the same order. Zipping them compares unrelated users and reports massive skew, or, if the logs happen to line up in a test, none at all.
- **`fillna(0)`.** The most common real skew is a feature the online path forgot to send. Filling with 0 makes "missing" look like "a user with zero orders" and hides it.
- **Keeping a stale serving row.** Serving logs every request. The row that matters is the most recent one before the label.
- **Sample vs population std.** Pick one and say which. Here the spec fixes it so the gate is reproducible.
- **`isinstance(True, int)`.** A flag logged as `"true"` in serving and `True` in training is a real skew (string vs bool). Treating bools as numbers hides it.

## Production notes

- Google's *Rules of ML* (rule 29) recommends logging the features you serve and training on those logs. That removes this class of bug at the source. Feast, Tecton and Vertex AI Feature Store each offer a single feature definition for both paths.
- TFX Data Validation computes this exact skew report (L-infinity distance for categoricals, Jensen-Shannon divergence for numerics) and fails the pipeline on thresholds. Evidently and WhyLabs do the same as hosted dashboards.
- Run this as a deploy gate on a fresh sample of shadow-logged traffic (see `shadow-deployment-diff`), and continuously afterwards as a drift monitor (`population-stability-index`, `ks-drift-detector`).
- Pairs with `point-in-time-feature-join`. Most "skew" found in production is really leakage in the training join, where offline features saw the future.
