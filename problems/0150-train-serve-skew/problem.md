Your fraud model scored 0.94 AUC offline and 0.71 in production. The usual suspect is **train/serve skew**: the online feature pipeline computes something different from the offline one. You're adding a pre-deploy check that compares a training snapshot against logged serving features for the same users.

Implement `train_serve_skew(train_rows, serve_rows, features, policy)`.

- `train_rows` is a list of `{"entity_id", "features": {name: value}}`. Entity ids are unique.
- `serve_rows` is a list of `{"entity_id", "ts", "features"}`. An entity can be logged more than once.
- `features` is the list of feature names to check.
- `policy` is `{"abs_tol", "max_mismatch_rate", "max_distance", "max_missing_delta", "top_k"}`.

A value is **missing** when its key is absent or its value is `None`.

**1. Deduplicate serving.** Per entity keep the row with the greatest `ts`. On equal `ts`, keep the one that comes later in the list.

**2. Join** on `entity_id`. `joined` is the number of entities on both sides, `train_only` the entities only in training, and `serve_only` the entities only in (deduplicated) serving.

**3. Per feature:**

| field | definition |
|---|---|
| `kind` | `"numeric"` if there is at least one non-missing value and every non-missing value on both sides (all rows, joined or not) is an `int` or `float` and **not** a `bool`, else `"categorical"` |
| `mismatch_rate` | over joined entities: both missing is a match; exactly one missing is a mismatch; numeric values mismatch when `abs(train - serve) > abs_tol`; categorical values mismatch when `train != serve`. Divide by `joined`, or `None` if `joined == 0`. |
| `distance` | over all training rows vs all deduplicated serving rows, ignoring missing values. Numeric: $\lvert\mu_s - \mu_t\rvert / \sigma_t$ with $\sigma_t$ the **population** std of the training values. If $\sigma_t = 0$, the distance is `0.0` when the means are equal, else `float("inf")`. Categorical: total variation distance $\tfrac12 \sum_v \lvert P_t(v) - P_s(v)\rvert$ between the value frequencies. If either side has no non-missing values, `None`. |
| `train_missing_rate`, `serve_missing_rate` | the fraction of rows on that side where the feature is missing |
| `skewed` | `mismatch_rate > max_mismatch_rate`, or `distance > max_distance`, or `abs(serve_missing_rate - train_missing_rate) > max_missing_delta` (a `None` never triggers) |

**4. Report.** `top_offenders` lists the features with `mismatch_rate > 0`, sorted by mismatch rate descending and then by name, truncated to `top_k`. `skewed` lists the skewed feature names sorted. `decision` is `"block"` if any feature is skewed, else `"pass"`.

Return:

```
{
  "joined": int, "train_only": int, "serve_only": int,
  "features": {name: {"kind", "mismatch_rate", "distance", "train_missing_rate", "serve_missing_rate", "skewed"}},
  "top_offenders": [...], "skewed": [...], "decision": "pass" | "block"
}
```

**Constraints**

- `1 <= len(train_rows), len(serve_rows) <= 3000`, `1 <= len(features) <= 30`
- Feature values are numbers, strings, booleans or `None`
- `0 <= abs_tol`, and every other threshold is in `[0, 1]` except `max_distance >= 0`
