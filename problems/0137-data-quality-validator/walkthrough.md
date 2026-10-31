## 1. What the problem is really asking

Before a batch of gateway log rows lands in the warehouse, you run a list of rules against it and block the load if a rule fails. This is the "expectations" model from Great Expectations: each rule names a column, a check and an optional tolerance (`mostly`), and the report says how many rows each rule looked at, how many failed, and which ones.

Under the story, every expectation is the same two-step shape:

1. **Pick the rows it evaluates.** `not_null` looks at every row. Every other check looks only at rows where the value is present.
2. **Apply a per-value predicate** to those rows (is it an int, is it in range, does it match the pattern...). The one exception, `unique`, needs the whole column first.

Then it's arithmetic: `failed / evaluated`, a `mostly` comparison, the first few failing ids, and the union of failing row indices.

The judge compares the whole return value: `success`, every field of every result in input order (`evaluated`, `failed`, `fail_rate`, `passed`, `sample`), and the sorted `failed_rows`. Most wrong answers come from getting `evaluated` wrong (counting nulls) or from Python's type quirks.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `records` | list of dicts, one per request | read with `r.get(col)` so a missing key reads as `None` |
| `expectations` | list of `{"column", "check", ...params, "mostly"?}` | one result per expectation, in order |
| `refs` | `{"tenants": [...]}` or `None` | the key set for `foreign_key` |
| `id_column` | which field identifies a row, default `"request_id"` | what goes into `sample` |
| `sample_size` | how many failing ids to show, default `3` | `bad[:sample_size]` |

Three details are easy to miss:

- **A null is a missing key *or* a `None` value.** `r.get(col) is None` covers both. A null is not a failure for any check except `not_null`, and it doesn't count as evaluated either. In Example 2, `cost_usd` is null on the cache hit, so its `type` check evaluates **2** rows, not 3.
- **`bool` is a subclass of `int` in Python.** `isinstance(True, int)` is `True`. The statement says `int` and `float` both exclude booleans, and `range` treats a boolean as "not a number".
- **`failed_rows` includes rows that failed an expectation that still passed.** A `mostly` tolerance lets the batch through, but the bad rows still need quarantine. In Example 2, `cost_usd` not_null passes at 2/3 ≥ 0.5, and row 0 is still in `failed_rows`.

## 3. Trace Example 1 by hand

Four rows:

| row | request_id | tenant_id | prompt_tokens |
|---|---|---|---|
| 0 | req_00a1f3c2 | acme-health | 812 |
| 1 | req_00a1f3c3 | globex-bank | None |
| 2 | req_00a1f3c2 | hooli | 95 |
| 3 | req_00a1f3c5 | initech | 0 |

**`request_id` unique.** No nulls, so 4 rows are evaluated. Count the values first: `req_00a1f3c2` appears twice. Both row 0 and row 2 fail. Result: `evaluated 4, failed 2, fail_rate 0.5, passed False, sample ['req_00a1f3c2', 'req_00a1f3c2']`. The sample lists the same id twice because it lists one id per failing row.

**`tenant_id` foreign_key** against `refs["tenants"]`. `hooli` is not a known tenant, so row 2 fails: `evaluated 4, failed 1, fail_rate 0.25`, sample `['req_00a1f3c2']`.

**`prompt_tokens` range, min 1.** Row 1 is null and is skipped, so **3** rows are evaluated. Row 3 has `0 < 1` and fails: `evaluated 3, failed 1, fail_rate 0.333333`, sample `['req_00a1f3c5']`.

No expectation has a `mostly`, so each needs a perfect score and all three fail: `success False`. The rows that failed anything are `{0, 2} ∪ {2} ∪ {3}`, so `failed_rows = [0, 2, 3]`.

**The busiest hidden case, "dirty batch with incidents".** Eleven rows of a 150-row batch are broken on purpose, and the report shows every rule doing its job:

| expectation | evaluated | failed | passed | why |
|---|---|---|---|---|
| request_id not_null | 150 | 1 | False | row 77 is `None`, so its sample is `[None]` |
| request_id unique | 149 | 2 | False | rows 4 and 90 share an id; row 77 is skipped |
| request_id regex | 149 | 0 | True | |
| prompt_tokens type int | 150 | 2 | False | row 17 is `True`, row 52 is `"512"` |
| prompt_tokens range | 150 | 2 | False | the same two rows: neither is a number |
| cost_usd type float | 102 | 1 | False | only the 102 non-cached rows are evaluated; row 88 is `"0.004"` |
| created_at regex | 150 | 1 | False | row 11 has `" (retry)"` after a valid timestamp |
| status in_set, mostly 0.95 | 149 | 1 | **True** | row 60 has no status (skipped); row 61 is `"cancelled"`, and 148/149 ≥ 0.95 |

`failed_rows = [4, 11, 17, 23, 31, 40, 52, 61, 77, 88, 90]`, and row 61 is in it even though its expectation passed.

## 4. Key idea: nullness and validity are different questions

"Is this field present?" and "is this field well formed?" have different owners. A null `cost_usd` on a cache hit is normal. A `cost_usd` of `"0.004"` is a bug. If every check also failed nulls, one optional column would fail `type`, `range` and `regex` at once and block every load. So the rule is: `not_null` owns nulls, and every other check sees only present values. This also changes `evaluated`, which is the denominator of `fail_rate` and of the `mostly` test.

## 5. Key idea: unique needs the whole column, keyed by type

Every other check is a function of one value. `unique` depends on all of them, so you count first and then judge each row:

```python
counts = Counter((type(v).__name__, _freeze(v)) for v in values)
ok = lambda v: counts[(type(v).__name__, _freeze(v))] == 1
```

Two reasons for this shape:

- **Every copy fails, including the first.** If you flagged only the second occurrence, the first copy would look clean, and a dedupe job would keep whichever copy it saw first. In Example 1 that drops row 0 from `failed_rows`.
- **The key includes the type.** In Python, `1 == True`, `0 == False` and `1 == 1.0`, and they hash the same. The statement says duplicates must be "of the same type". In "bools are not ints", the values `0, 1, True, 2, False, 3.0` are all unique once the type is in the key. Without it, `0`/`False` and `1`/`True` collide and 4 rows fail.

`_freeze` turns lists and dicts into tuples so that they can be hashed. Values are JSON, so a column can hold a list.

## 6. Plan before you code

```
failed_rows = set()
for each expectation:
    if check is not_null:
        rows = every index;  bad = indices whose value is null
    else:
        rows = indices whose value is not null
        ok = predicate built for this check (unique counts the column first)
        bad = [i in rows if not ok(value_i)]
    evaluated, failed = len(rows), len(bad)
    passed = evaluated == 0 or (evaluated - failed) / evaluated >= mostly
    failed_rows |= bad
    record column, check, counts, fail_rate, passed, ids of bad[:sample_size]
success = all passed; failed_rows sorted
```

The per-check predicates, for a non-null `v`:

| check | `v` passes when |
|---|---|
| `type` int | `isinstance(v, int) and not isinstance(v, bool)` |
| `type` float | an int or float that is not a bool |
| `type` str / bool | `isinstance(v, str)` / `isinstance(v, bool)` |
| `range` | it's a number, and `min <= v <= max` for whichever bounds are given |
| `regex` | it's a `str` and `re.fullmatch(pattern, v)` matches |
| `in_set` / `foreign_key` | `v in values` / `v in refs[ref]` |
| `unique` | its `(type, value)` occurs exactly once among evaluated rows |

## 7. Build it one piece at a time

**Step 1: the type helpers.** Test for `bool` before `int`:

```python
def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)
```

Without the `bool` exclusion, a client that sends `"prompt_tokens": true` passes both `type int` and `range min 1`, because `True == 1`, and billing charges for one token.

**Step 2: one predicate factory.** Build the predicate once per expectation, not once per row. That's where you compile the regex and count the column for `unique`:

```python
if check == "regex":
    pat = re.compile(exp["pattern"])
    return lambda v: isinstance(v, str) and pat.fullmatch(v) is not None
```

`re.match` only anchors at the start, so `"2026-10-30T14:02:11Z (retry)"` would match a timestamp pattern. `fullmatch` requires the whole string. The `isinstance(v, str)` guard matters too: `re` raises `TypeError` on a number.

For `range`, missing bounds are `None` and are simply skipped: `(lo is None or v >= lo) and (hi is None or v <= hi)`.

**Step 3: choose the rows.** This is the line that sets `evaluated`:

```python
rows = [i for i, r in enumerate(records) if r.get(col) is not None]
```

Keep the row indices, not just the values. You need them for `failed_rows` and for the sample ids.

**Step 4: the report.** `fail_rate` must not divide by zero, and an expectation that evaluated nothing passes (the "empty batch" and "column missing everywhere" cases). `sample` reads `id_column` with `.get`, so a row without an id contributes `None`, as row 77 does in the dirty batch.

## 8. Full solution

```python
import re  # fullmatch for the regex check
from collections import Counter  # counts values for the unique check


# A number for range/float purposes: int or float, but never a bool.
def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)  # True is an int in Python


# Does a non-null value have the requested type?
def _type_ok(v, t):
    if t == "bool":  # booleans only
        return isinstance(v, bool)  # the bool check needs no exclusion
    if t == "int":  # integers, excluding booleans
        return isinstance(v, int) and not isinstance(v, bool)  # rule out True/False explicitly
    if t == "float":  # any real number, excluding booleans
        return _is_number(v)  # an int like 1 counts as a float
    if t == "str":  # strings only
        return isinstance(v, str)  # "512" is a str, 512 is not
    raise ValueError("unknown type %r" % t)  # a typo in the expectation should be loud


# Build the per-value predicate for one expectation; `values` is the evaluated column.
def _row_checker(exp, refs, values):
    check = exp["check"]  # which rule this expectation applies
    if check == "type":  # type check
        return lambda v: _type_ok(v, exp["type"])  # fixed type, tested per value
    if check == "range":  # inclusive numeric bounds
        lo, hi = exp.get("min"), exp.get("max")  # either bound may be absent
        # must be a real number, then honour whichever bounds exist
        return lambda v: _is_number(v) and (lo is None or v >= lo) and (hi is None or v <= hi)
    if check == "regex":  # pattern over the whole string
        pat = re.compile(exp["pattern"])  # compile once, not once per row
        return lambda v: isinstance(v, str) and pat.fullmatch(v) is not None  # whole value must match
    if check == "in_set":  # allowed-values list
        allowed = exp["values"]  # the enum for this column
        return lambda v: v in allowed  # membership is the whole rule
    if check == "foreign_key":  # value must exist in a reference table
        keys = (refs or {})[exp["ref"]]  # the referenced table's keys
        return lambda v: v in keys  # unknown key means an orphan row
    if check == "unique":  # needs the whole column, so count first
        counts = Counter((type(v).__name__, _freeze(v)) for v in values)  # key by type so 1 and True differ
        return lambda v: counts[(type(v).__name__, _freeze(v))] == 1  # every copy of a duplicate fails
    raise ValueError("unknown check %r" % check)  # unsupported check name


# Make lists and dicts hashable so unique can count them.
def _freeze(v):
    if isinstance(v, list):  # lists become tuples
        return tuple(_freeze(x) for x in v)  # recursively, for nested values
    if isinstance(v, dict):  # dicts become sorted key/value tuples
        return tuple(sorted((k, _freeze(x)) for k, x in v.items()))  # key order doesn't matter
    return v  # scalars are already hashable


# Run every expectation over the batch and report.
def validate(records, expectations, refs=None, id_column="request_id", sample_size=3):
    results, failed_rows = [], set()  # one result per expectation; any row that failed anything
    for exp in expectations:  # input order is report order
        col = exp["column"]  # the field this rule looks at
        if exp["check"] == "not_null":  # the only check that sees nulls
            rows = list(range(len(records)))  # every row is evaluated
            bad = [i for i in rows if records[i].get(col) is None]  # missing key or None
        else:  # every other check skips nulls
            rows = [i for i, r in enumerate(records) if r.get(col) is not None]  # present values only
            ok = _row_checker(exp, refs, [records[i][col] for i in rows])  # predicate for this rule
            bad = [i for i in rows if not ok(records[i][col])]  # rows whose value breaks the rule
        evaluated, failed = len(rows), len(bad)  # the two counts the report is built on
        # nothing to evaluate passes; otherwise the pass fraction must reach `mostly`
        passed = evaluated == 0 or (evaluated - failed) / evaluated >= exp.get("mostly", 1.0)
        failed_rows.update(bad)  # bad rows are listed even when `mostly` lets the rule pass
        results.append({  # one report row for this expectation
            "column": col,
            "check": exp["check"],
            "evaluated": evaluated,
            "failed": failed,
            "fail_rate": failed / evaluated if evaluated else 0.0,
            "passed": passed,
            "sample": [records[i].get(id_column) for i in bad[:sample_size]],
        })
    # the batch loads only if every rule passed; rows reported in ascending order
    return {"success": all(r["passed"] for r in results), "results": results, "failed_rows": sorted(failed_rows)}
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `failed_rows [0, 2, 3]`; unique fails both copies; range evaluates 3 | every duplicate fails; nulls are skipped by `range` |
| Example 2 | regex and `cached` type fail row 1; `cost_usd` type evaluates 2 and passes; not_null passes under `mostly 0.5`; `failed_rows [0, 1]` | `fullmatch`, string `"false"` is not a bool, int `1` is a float, `mostly`-passing rows still listed |
| clean hourly batch | `success True`, `cost_usd` type evaluates 83 of 120 | no false positives; cached rows with null cost are skipped |
| dirty batch with incidents, dirty batch, sample of 5 | 11 failed rows; status passes at 148/149 | every check on one batch, `None` id in a sample |
| mostly holds at 2 of 60 | status fails 2, `passed True`, `success True`, `failed_rows [3, 9]` | 58/60 ≥ 0.95 |
| mostly breaks at 4 of 60 | status fails 4, `passed False` | 56/60 < 0.95 |
| empty batch | every result `evaluated 0, passed True`, `success True` | no division by zero |
| column missing everywhere | regex evaluates 0 and passes; not_null fails 4 of 4 with sample `['t-0', 't-1', 't-2']` | only `not_null` sees absent keys; custom `id_column`; sample capped at 3 |
| bools are not ints | type fails `r2, r4, r5`; range fails `r2, r4`; unique fails none | `bool` excluded from int and number; `3.0` is not an int; type in the unique key |
| unique by type and value | fails `r1, r3`; the two nulls are skipped | `"7"` and `7` differ; nulls are not duplicates |

## 10. Complexity

Each expectation is one pass over the records, plus building its predicate. `unique` builds a `Counter` in O(n) (more for large nested values, which `_freeze` walks). With `E` expectations and `n` rows the total is O(E · n), and memory is O(n) for the row index lists and the counter. At 20 expectations over 2,000 rows that is trivial.

In production you don't pull the rows out of the warehouse to do this. Each check becomes a SQL aggregate (`COUNT(*) FILTER (WHERE ...)`, `GROUP BY value HAVING COUNT(*) > 1` for unique), and only the counts and a few sample ids leave the database. Run it as a gate in a write-audit-publish flow: land the batch in staging, validate, then swap it into production.

## 11. If you got Wrong Answer

- **`evaluated` equals the batch size on every check, and the clean batch fails.** Your checks count nulls as failures. `cost_usd` type then evaluates all 120 rows and fails the 37 cache hits. Only `not_null` evaluates every row.
- **Example 1 has `failed_rows [2, 3]` and unique fails only 1 row.** You flag the second occurrence of a duplicate and let the first pass. Count the column first, then fail every row whose value occurs more than once.
- **"bools are not ints" reports only `r5` failing the type check, or the dirty batch's `prompt_tokens` checks fail only row 52.** `True` slipped through `isinstance(v, int)`. Exclude `bool` explicitly.
- **The dirty batch's `created_at` regex shows `failed 0`.** You used `re.match`, which ignores trailing junk like `" (retry)"`. Use `re.fullmatch`.
- **"bools are not ints" has the unique check failing 4 rows.** Your unique key is the value alone, so `0`/`False` and `1`/`True` collide. Put `type(v).__name__` in the key.
- **Example 2's `failed_rows` is missing row 0.** You only add a rule's bad rows when the rule fails. Rows that failed a `mostly`-passing rule still go in.
- **Runtime Error: `TypeError: expected string or bytes-like object`.** You ran the regex on a non-string. The current tests never put a number in a regex column, so this passes the judge, but the statement says a non-string fails the check, and a real batch will contain one. Check `isinstance(v, str)` first.

## 12. Follow-ups an interviewer might ask

- *The batch has 50 million rows. How do you run this?* Push each check into SQL or Spark (Deequ, dbt tests, Soda). Each expectation becomes an aggregate, so only counts and a few ids come back. `unique` becomes a `GROUP BY ... HAVING COUNT(*) > 1`.
- *What do you do with the failed rows when the batch passes under `mostly`?* Quarantine them: write them to a side table with the expectation that caught them, load the rest, and alert the owning team if the quarantine grows. That's why `failed_rows` includes them.
- *How would you choose `mostly` for `status`?* From history. Look at the fail rate over the past weeks and set the tolerance just above its normal range, so a new error code (`rate_limited` in "mostly breaks at 4 of 60") trips the rule while normal noise doesn't.
- *How does this relate to drift detection?* Run data quality first, then drift (problems 135, population-stability-index, and 136, ks-drift-detector) on the rows that passed. Otherwise a null burst from a broken pipeline shows up as "drift" and pages the ML on-call instead of the data owner.
- *Should the sample show values?* Only ids. Log rows can hold PII (prompts, user ids), so show the identifier and let someone with access look up the row (problem 162 covers PII handling).
