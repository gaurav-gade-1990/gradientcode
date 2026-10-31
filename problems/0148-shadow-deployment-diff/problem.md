Your ticket-routing service is replacing its intent model. For a week the new model has run in **shadow**: it gets a copy of every request, and its answer is logged but never shown. Before you flip traffic, write the job that diffs shadow against primary and says whether the shadow is ready.

Implement `shadow_diff(records, policy)`.

- `records` is a list of `{"request_id", "segment", "primary", "shadow"}`, optionally with `"shadow_error"` (a string). `primary` and `shadow` are JSON values: strings, numbers, booleans, `None`, lists or dicts.
- `policy` is `{"abs_tol", "rel_tol", "min_agreement", "max_error_rate", "min_segment"}`.

**Classify each request** with the first rule that matches:

| class | rule |
|---|---|
| `"shadow_error"` | the record has a `"shadow_error"` key whose value is not `None` |
| `"exact"` | `json.dumps(primary, sort_keys=True) == json.dumps(shadow, sort_keys=True)` |
| `"normalized"` | both are `str` and `norm(primary) == norm(shadow)`, where `norm(s) = " ".join(s.lower().strip().rstrip(".!?").split())` |
| `"numeric"` | both are numbers (`int` or `float`, but **not** `bool`) and `abs(primary - shadow) <= abs_tol + rel_tol * abs(primary)` |
| `"mismatch"` | anything else |

**Summarize** the whole log and each segment. For a group, count every class, then compute `compared = total - shadow_error` and `agreement = (exact + normalized + numeric) / compared`, or `None` when `compared == 0`.

**Decide.** Collect blocking reasons in this order:

1. `"overall_agreement"` if the overall agreement is `None` or `< min_agreement`
2. `"shadow_errors"` if `shadow_error / total > max_error_rate` overall
3. `"segment:<name>"` for every segment (sorted by name) with `compared >= min_segment` and agreement `< min_agreement`. Smaller segments never block.

`ready` is true when there are no blocking reasons.

Return:

```
{
  "per_request": {request_id: class},
  "overall":     {"total", "exact", "normalized", "numeric", "mismatch", "shadow_error", "compared", "agreement"},
  "segments":    {segment: {same keys}},
  "mismatches":  [request ids classed "mismatch", in input order],
  "blocking":    [...],
  "ready":       bool
}
```

**Constraints**

- `1 <= len(records) <= 2000`, and request ids are unique
- `0 <= abs_tol`, `0 <= rel_tol`, `0 < min_agreement <= 1`, `0 <= max_error_rate <= 1`, `1 <= min_segment`
