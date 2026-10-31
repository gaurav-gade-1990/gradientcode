## Approach

Treat each expectation as two steps: pick the rows it **evaluates**, then apply a per-value predicate to those rows.

```python
if exp["check"] == "not_null":
    rows = all rows;  bad = rows where value is None or missing
else:
    rows = rows where the value is non-null       # nulls are skipped, not failed
    ok = predicate(exp)                           # type / range / regex / in_set / fk / unique
    bad = [i for i in rows if not ok(value_i)]
passed = evaluated == 0 or (evaluated - failed) / evaluated >= mostly
```

Separating nullness from validity is the core design rule. "Is this field present?" and "is this field well formed?" are different questions with different owners. A null `cost_usd` on a cache hit is fine, but a `cost_usd` of `"0.004"` is a bug.

`unique` is the only check that needs the whole column, so count values first (keyed by type and value, so `"7"` and `7` are different) and then fail every row whose value occurs more than once. Flagging every copy lets the dedupe job see both rows and choose which one to keep.

Two Python details matter: `bool` is a subclass of `int`, so test for `bool` first; and `re.match` anchors only at the start, so use `re.fullmatch`.

## Common mistakes

- **Nulls fail every check.** One optional column then fails type, range and regex together and blocks every load. Only `not_null` should see nulls.
- **`re.match` instead of `re.fullmatch`.** `"2026-10-30T14:02:11Z (retry)"` passes, and the warehouse cast fails an hour later.
- **`isinstance(True, int)`.** A boolean `prompt_tokens` passes the type and range checks, and billing charges for one token.
- **Flagging only the later duplicate.** The first copy looks clean, so the dedupe job keeps whichever copy it happens to see and retried requests get double-billed.
- **Dropping rows that failed a `mostly` expectation from the report.** The expectation passes, but those rows still need to be quarantined or inspected.

## Production notes

- Great Expectations, Soda, dbt tests and Deequ (on Spark) implement exactly these primitives. GE's `mostly`, its null-skipping semantics and its `partial_unexpected_list` samples are the model for this report.
- Run validation as a **gate** before the load (write-audit-publish): land the batch in a staging table, validate it, and only then swap it into the production table. A failed gate quarantines the batch instead of corrupting dashboards.
- Keep the samples small and log the ids, not the values, when rows may hold PII (problem 162).
- At scale, push the checks into SQL (`COUNT(*) FILTER (WHERE ...)`) so only the counts and a few sample ids leave the warehouse.
- Data-quality failures and drift are different incidents. Run this first, then drift detection (problems 135 and 136) on the rows that passed, so a broken pipeline doesn't page the ML on-call.
